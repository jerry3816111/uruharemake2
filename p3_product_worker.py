#!/usr/bin/env python3
"""Isolated P3 product-worker seam with real generation disabled by default.

The module top level intentionally imports only the standard-library P3
contract.  Heavy product and tokenizer imports happen only after the caller has
created a case-owned ephemeral workspace and installed the isolation
environment.  P3-B1 exercises import and transport guards with contract fakes;
it does not instantiate the brain or contact Ollama.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from typing import Any, Callable, Iterable, Mapping
from unittest import mock

from p3_product_comparison import (
    P3ContractError,
    canonical_sha256,
    load_design,
    load_tokenizer_binding_probe,
    make_request,
    mark_transport_failure,
    new_budget,
    record_usage,
    reserve_call,
    write_new_json,
)


WORKSPACE_SCHEMA = "uruha_p3_ephemeral_workspace_v1"
CASE_OWNER_SCHEMA = "uruha_p3_case_owner_v1"
DRY_RUN_SCHEMA = "uruha_p3_product_worker_dry_run_v1"
ADAPTER_SCHEMA = "uruha_p3_product_transport_adapter_contract_v1"
TOKEN_PROBE_RELEASE_SCHEMA = "uruha_p3_tokenizer_binding_probe_execution_release_v1"
SAFE_SLOT_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
REPO_ROOT = Path(__file__).resolve().parent
PRODUCTION_DB_PATH = (REPO_ROOT / "uruha_memory_mac_db").resolve()


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise P3ContractError("invalid_worker_state", str(path)) from exc
    if not isinstance(value, dict):
        raise P3ContractError("invalid_worker_state", str(path))
    return value


def _signed_record(payload: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    result["record_sha256"] = canonical_sha256(result)
    return result


def _verify_signed_record(record: Mapping[str, Any], code: str) -> None:
    expected = record.get("record_sha256")
    unsigned = dict(record)
    unsigned.pop("record_sha256", None)
    if not isinstance(expected, str) or expected != canonical_sha256(unsigned):
        raise P3ContractError(code)


def initialise_ephemeral_workspace(root: str | Path) -> Path:
    """Create or verify a sentinel-owned root outside the repository."""

    raw = Path(root)
    if raw.is_symlink():
        raise P3ContractError("worker_root_symlink_forbidden")
    resolved = raw.resolve()
    if _is_relative_to(resolved, REPO_ROOT) or _is_relative_to(REPO_ROOT, resolved):
        raise P3ContractError("worker_root_overlaps_repository", str(resolved))
    sentinel = resolved / ".p3_ephemeral_workspace.json"
    if resolved.exists():
        if not resolved.is_dir() or not sentinel.is_file():
            raise P3ContractError("existing_worker_root_without_sentinel", str(resolved))
        record = _read_json(sentinel)
        _verify_signed_record(record, "worker_sentinel_digest_mismatch")
        if record.get("schema") != WORKSPACE_SCHEMA:
            raise P3ContractError("worker_sentinel_schema_mismatch")
        return resolved
    resolved.mkdir(parents=True, exist_ok=False)
    write_new_json(
        sentinel,
        _signed_record(
            {
                "schema": WORKSPACE_SCHEMA,
                "purpose": "P3 isolated product worker; never production state",
                "repo_sha256": canonical_sha256(str(REPO_ROOT)),
            }
        ),
    )
    return resolved


def claim_case_workspace(
    root: str | Path,
    case_id: str,
    *,
    state_slot: str | None = None,
) -> dict[str, Any]:
    """Claim a persistent case slot; same-case restart is allowed, reuse is not."""

    if not isinstance(case_id, str) or not case_id:
        raise P3ContractError("invalid_case_id")
    workspace_root = initialise_ephemeral_workspace(root)
    case_hash = hashlib.sha256(case_id.encode("utf-8")).hexdigest()
    slot = state_slot or case_hash[:24]
    if not isinstance(slot, str) or SAFE_SLOT_RE.fullmatch(slot) is None:
        raise P3ContractError("invalid_case_state_slot")
    case_root = workspace_root / "cases" / slot
    if case_root.is_symlink():
        raise P3ContractError("case_state_symlink_forbidden")
    owner_path = case_root / ".p3_case_owner.json"
    restart = owner_path.is_file()
    if restart:
        owner = _read_json(owner_path)
        _verify_signed_record(owner, "case_owner_digest_mismatch")
        if owner.get("schema") != CASE_OWNER_SCHEMA:
            raise P3ContractError("case_owner_schema_mismatch")
        if owner.get("case_sha256") != case_hash:
            raise P3ContractError("cross_case_state_reuse")
    else:
        if case_root.exists() and any(case_root.iterdir()):
            raise P3ContractError("unowned_case_state_not_empty")
        case_root.mkdir(parents=True, exist_ok=True)
        write_new_json(
            owner_path,
            _signed_record(
                {
                    "schema": CASE_OWNER_SCHEMA,
                    "case_sha256": case_hash,
                    "slot": slot,
                }
            ),
        )
    paths = {
        "case_root": case_root,
        "memory": case_root / "memory",
        "adaptive": case_root / "adaptive.json",
        "web_logs": case_root / "web_logs",
    }
    for key in ("memory", "web_logs"):
        paths[key].mkdir(parents=True, exist_ok=True)
    for path in paths.values():
        resolved_path = path.resolve()
        if not _is_relative_to(resolved_path, workspace_root):
            raise P3ContractError("case_path_escaped_worker_root", str(resolved_path))
        if resolved_path == PRODUCTION_DB_PATH:
            raise P3ContractError("production_database_path_forbidden")
    return {
        "case_sha256": case_hash,
        "state_slot": slot,
        "restart": restart,
        "paths": paths,
    }


def prepare_isolated_environment(
    case_workspace: Mapping[str, Any], design: Mapping[str, Any]
) -> dict[str, str]:
    paths = case_workspace["paths"]
    model = str(design["model"]["generation_model"])
    env = {
        "URUHA_SKIP_AUTO_VENV": "1",
        "URUHA_MEMORY_DB_PATH": str(paths["memory"]),
        "URUHA_ADAPTIVE_PERSON_MODEL_PATH": str(paths["adaptive"]),
        "URUHA_WEB_LOG_JSONL_PATH": str(paths["web_logs"] / "turns.jsonl"),
        "URUHA_WEB_LOG_TXT_PATH": str(paths["web_logs"] / "turns.txt"),
        "URUHA_WEB_PREWARM_BRAIN": "0",
        "URUHA_IDLE_VISIBLE_PROACTIVE_ENABLED": "false",
        "URUHA_RIGHT_BRAIN_MODEL_BLEND_ENABLED": "false",
        "URUHA_M31_SEMANTIC_VERIFIER_MODEL": model,
        "GRADIO_ANALYTICS_ENABLED": "false",
        "ANONYMIZED_TELEMETRY": "False",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "TOKENIZERS_PARALLELISM": "false",
    }
    os.environ.update(env)
    return env


@contextmanager
def network_forbidden() -> Iterable[list[dict[str, str]]]:
    """Fail if product import or tokenizer inspection attempts any connection."""

    attempts: list[dict[str, str]] = []

    def blocked_connect(socket_self: Any, address: Any, *args: Any, **kwargs: Any) -> Any:
        attempts.append(
            {"api": "socket.connect", "target_sha256": canonical_sha256(str(address))}
        )
        raise P3ContractError("network_attempt_during_product_dry_run")

    def blocked_create_connection(address: Any, *args: Any, **kwargs: Any) -> Any:
        attempts.append(
            {
                "api": "socket.create_connection",
                "target_sha256": canonical_sha256(str(address)),
            }
        )
        raise P3ContractError("network_attempt_during_product_dry_run")

    def blocked_urlopen(*args: Any, **kwargs: Any) -> Any:
        attempts.append({"api": "urlopen", "target_sha256": canonical_sha256(str(args[:1] or kwargs))})
        raise P3ContractError("network_attempt_during_product_dry_run")

    with mock.patch.object(socket.socket, "connect", blocked_connect), mock.patch.object(
        socket, "create_connection", blocked_create_connection
    ), mock.patch.object(urllib.request, "urlopen", blocked_urlopen):
        yield attempts


class LocalQwenTokenizerCandidate:
    """Offline tokenizer candidate; not yet provider-usage-equivalence evidence."""

    evidence_kind = "local_hf_chat_template_candidate_not_provider_validated"

    def __init__(self, model_name: str = "Qwen/Qwen2.5-7B-Instruct") -> None:
        from transformers import AutoTokenizer

        self.model_name = model_name
        cache_root = Path(
            os.environ.get(
                "HF_HUB_CACHE",
                Path.home() / ".cache" / "huggingface" / "hub",
            )
        ).resolve()
        repo_dir = cache_root / f"models--{model_name.replace('/', '--')}"
        ref_path = repo_dir / "refs" / "main"
        try:
            revision = ref_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise P3ContractError("offline_tokenizer_snapshot_missing") from exc
        if not revision or any(character not in "0123456789abcdef" for character in revision):
            raise P3ContractError("offline_tokenizer_revision_invalid")
        snapshot_path = (repo_dir / "snapshots" / revision).resolve()
        if not _is_relative_to(snapshot_path, repo_dir.resolve()) or not snapshot_path.is_dir():
            raise P3ContractError("offline_tokenizer_snapshot_missing")
        self.snapshot_revision = revision
        self.tokenizer = AutoTokenizer.from_pretrained(
            str(snapshot_path),
            local_files_only=True,
        )

    def __call__(self, messages: Iterable[Mapping[str, str]]) -> int:
        rows = [dict(message) for message in messages]
        token_ids = self.tokenizer.apply_chat_template(
            rows,
            tokenize=True,
            add_generation_prompt=True,
        )
        return len(token_ids)

    def evidence(self) -> dict[str, Any]:
        template = str(self.tokenizer.chat_template or "")
        fixture = [
            {"role": "system", "content": "短く日本語で返す。"},
            {"role": "user", "content": "まだ決められない。"},
        ]
        rendered = self.tokenizer.apply_chat_template(
            fixture,
            tokenize=False,
            add_generation_prompt=True,
        )
        return {
            "evidence_kind": self.evidence_kind,
            "model_name": self.model_name,
            "snapshot_revision": self.snapshot_revision,
            "tokenizer_class": type(self.tokenizer).__name__,
            "chat_template_present": bool(template),
            "chat_template_sha256": canonical_sha256(template),
            "fixture_render_sha256": canonical_sha256(rendered),
            "fixture_prompt_tokens": self(fixture),
            "local_files_only": True,
            "provider_usage_equivalence_validated": False,
        }


def _ollama_model_metadata(model: str) -> dict[str, Any]:
    ollama = shutil.which("ollama")
    if ollama is None:
        raise P3ContractError("ollama_command_unavailable")
    try:
        completed = subprocess.run(
            [ollama, "show", model, "--modelfile"],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise P3ContractError("ollama_metadata_unavailable") from exc
    if completed.returncode != 0:
        raise P3ContractError("ollama_metadata_unavailable")
    from_line = next(
        (line for line in completed.stdout.splitlines() if line.startswith("FROM ")),
        "",
    )
    digest = from_line.rsplit("sha256-", 1)[-1] if "sha256-" in from_line else ""
    return {
        "model": model,
        "digest": digest,
        "template_present": "TEMPLATE " in completed.stdout,
        "modelfile_sha256": canonical_sha256(completed.stdout),
        "metadata_command_calls": 1,
        "generation_calls": 0,
    }


def build_tokenizer_probe_preflight(probe_path: str | Path) -> dict[str, Any]:
    probe = load_tokenizer_binding_probe(probe_path)
    model = probe["model"]
    metadata = _ollama_model_metadata(model["ollama_model"])
    with network_forbidden() as network_attempts:
        tokenizer = LocalQwenTokenizerCandidate(model["hf_tokenizer"])
        fixture_counts = [
            {
                "fixture_id": fixture["fixture_id"],
                "role": fixture["role"],
                "messages_sha256": fixture["messages_sha256"],
                "hf_prompt_tokens": tokenizer(fixture["messages"]),
            }
            for fixture in probe["fixtures"]
        ]
        tokenizer_evidence = tokenizer.evidence()
    checks = {
        "probe_valid": True,
        "model_digest_matches": metadata["digest"] == model["ollama_blob_digest"],
        "model_template_present": metadata["template_present"],
        "offline_tokenizer_available": tokenizer_evidence["chat_template_present"],
        "four_fixture_counts_available": len(fixture_counts) == 4
        and all(row["hf_prompt_tokens"] > 0 for row in fixture_counts),
        "no_network_attempts_during_tokenizer_load": len(network_attempts) == 0,
        "config_does_not_self_authorize": probe["execution_boundary"][
            "real_model_calls_authorized_by_this_config"
        ]
        is False,
    }
    return {
        "schema": "uruha_p3_tokenizer_binding_probe_preflight_v1",
        "phase": "P3-B3",
        "status": "ready_for_execution_review" if all(checks.values()) else "not_ready_for_execution_review",
        "probe_sha256": probe["_probe_sha256"],
        "model_metadata": metadata,
        "tokenizer": tokenizer_evidence,
        "fixture_counts": fixture_counts,
        "checks": checks,
        "network_attempts": network_attempts,
        "network_generation_calls": 0,
        "real_model_calls": 0,
        "paid_calls": 0,
        "claim_boundary": (
            "This preflight reads model metadata and the offline tokenizer only. "
            "It does not establish provider token equivalence or authorize generation."
        ),
    }


def validate_tokenizer_probe_release(
    release_path: str | Path,
    probe: Mapping[str, Any],
) -> dict[str, Any]:
    release_file = Path(release_path)
    release = _read_json(release_file)
    expected_keys = {
        "schema",
        "phase",
        "status",
        "review_kind",
        "probe",
        "implementation_sha256",
        "preflight",
        "authorization",
        "claim_boundary",
    }
    if set(release) != expected_keys or release.get("schema") != TOKEN_PROBE_RELEASE_SCHEMA:
        raise P3ContractError("token_probe_release_schema_mismatch")
    if release.get("phase") != "P3-B3" or release.get("status") != "released_for_single_local_binding_probe":
        raise P3ContractError("token_probe_release_status_mismatch")
    if release.get("review_kind") != "same_task_self_review_not_independent":
        raise P3ContractError("token_probe_release_review_mismatch")
    repo = release_file.resolve().parent.parent
    probe_ref = release.get("probe")
    if not isinstance(probe_ref, Mapping) or set(probe_ref) != {"path", "sha256"}:
        raise P3ContractError("token_probe_release_probe_invalid")
    if probe_ref.get("sha256") != probe.get("_probe_sha256"):
        raise P3ContractError("token_probe_release_probe_digest_mismatch")
    probe_ref_path = (repo / str(probe_ref.get("path"))).resolve()
    if probe_ref_path != Path(str(probe.get("_probe_path"))).resolve():
        raise P3ContractError("token_probe_release_probe_path_mismatch")
    implementation = release.get("implementation_sha256")
    if not isinstance(implementation, Mapping) or set(implementation) != {
        "p3_product_comparison.py",
        "p3_product_worker.py",
        "test_p3_product_comparison.py",
    }:
        raise P3ContractError("token_probe_release_implementation_invalid")
    for name, expected_sha in implementation.items():
        path = repo / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
            raise P3ContractError("token_probe_release_implementation_digest_mismatch", name)
    preflight = release.get("preflight")
    if not isinstance(preflight, Mapping) or set(preflight) != {"path", "sha256", "status"}:
        raise P3ContractError("token_probe_release_preflight_invalid")
    preflight_path = (repo / str(preflight.get("path"))).resolve()
    if (
        not preflight_path.is_file()
        or hashlib.sha256(preflight_path.read_bytes()).hexdigest() != preflight.get("sha256")
        or preflight.get("status") != "ready_for_execution_review"
    ):
        raise P3ContractError("token_probe_release_preflight_mismatch")
    authorization = release.get("authorization")
    if authorization != {
        "run_id": "p3-b3-tokenizer-binding-probe-v1",
        "localhost_only": True,
        "model": "qwen2.5:7b",
        "model_digest": "2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730",
        "provider_calls_exact": 8,
        "completion_tokens_total_max": 8,
        "automatic_retry": False,
        "retain_output_text": False,
        "checkpoint_root": "analysis/p3_b3_tokenizer_binding_probe_checkpoints_v1",
        "result_path": "analysis/p3_b3_tokenizer_binding_probe_result_2026-09-14.json",
        "developer_smoke_access": False,
        "annotation_access": False,
        "production_database_access": False,
        "external_deployment": False,
    }:
        raise P3ContractError("token_probe_release_authorization_mismatch")
    return dict(release)


def _token_probe_request_commitment(
    probe: Mapping[str, Any],
    transport_id: str,
    fixture: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "probe_sha256": probe["_probe_sha256"],
        "transport": transport_id,
        "url_sha256": canonical_sha256(
            next(
                transport["url"]
                for transport in probe["transports"]
                if transport["id"] == transport_id
            )
        ),
        "fixture_id": fixture["fixture_id"],
        "fixture_role": fixture["role"],
        "messages_sha256": fixture["messages_sha256"],
        "model": probe["model"]["ollama_model"],
        "model_digest": probe["model"]["ollama_blob_digest"],
        "generation_options": probe["generation_options"],
    }


def _run_token_probe_call_once(
    *,
    probe: Mapping[str, Any],
    transport_id: str,
    fixture: Mapping[str, Any],
    hf_prompt_tokens: int,
    transport: Callable[[Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]],
    checkpoint_root: str | Path,
    clock: Callable[[], float],
) -> dict[str, Any]:
    request = _token_probe_request_commitment(probe, transport_id, fixture)
    request_sha = canonical_sha256(request)
    call_dir = Path(checkpoint_root) / transport_id / fixture["fixture_id"]
    intent_path = call_dir / "intent.json"
    complete_path = call_dir / "complete.json"
    failure_path = call_dir / "failure.json"
    if complete_path.exists():
        complete = _read_json(complete_path)
        _verify_signed_record(complete, "token_probe_complete_digest_mismatch")
        if complete.get("request_sha256") != request_sha:
            raise P3ContractError("token_probe_complete_source_mismatch")
        result = complete.get("result")
        if not isinstance(result, Mapping):
            raise P3ContractError("token_probe_complete_invalid")
        provider_call_evidence = result.get(
            "provider_call_evidence", result.get("real_model_calls")
        )
        if provider_call_evidence not in (0, 1):
            raise P3ContractError("token_probe_complete_evidence_invalid")
        return {
            **dict(result),
            "reused": True,
            "provider_call_evidence": provider_call_evidence,
            "real_model_calls": 0,
            "network_calls": 0,
        }
    if intent_path.exists():
        intent = _read_json(intent_path)
        _verify_signed_record(intent, "token_probe_intent_digest_mismatch")
        if intent.get("request_sha256") != request_sha:
            raise P3ContractError("token_probe_intent_source_mismatch")
        raise P3ContractError("token_probe_intent_without_complete_no_retry")
    intent = _signed_record(
        {
            "schema": "uruha_p3_tokenizer_probe_intent_v1",
            "request_sha256": request_sha,
            "transport": transport_id,
            "fixture_id": fixture["fixture_id"],
        }
    )
    write_new_json(intent_path, intent)
    started = clock()
    try:
        response = transport(fixture, probe)
        elapsed = clock() - started
        if not isinstance(response, Mapping) or set(response) != {
            "backend",
            "model",
            "prompt_tokens",
            "completion_tokens",
            "content",
            "real_model_calls",
            "network_calls",
        }:
            raise P3ContractError("token_probe_provider_payload_invalid")
        prompt_tokens = response.get("prompt_tokens")
        completion_tokens = response.get("completion_tokens")
        content = response.get("content")
        if (
            response.get("backend") != transport_id
            or response.get("model") != probe["model"]["ollama_model"]
            or isinstance(prompt_tokens, bool)
            or not isinstance(prompt_tokens, int)
            or prompt_tokens <= 0
            or isinstance(completion_tokens, bool)
            or not isinstance(completion_tokens, int)
            or completion_tokens < 0
            or completion_tokens > probe["generation_options"]["max_completion_tokens"]
            or not isinstance(content, str)
            or isinstance(elapsed, bool)
            or not isinstance(elapsed, (int, float))
            or elapsed < 0
            or elapsed > probe["generation_options"]["per_call_timeout_seconds"]
        ):
            raise P3ContractError("token_probe_provider_payload_invalid")
        for count_name in ("real_model_calls", "network_calls"):
            count = response.get(count_name)
            if isinstance(count, bool) or not isinstance(count, int) or count < 0 or count > 1:
                raise P3ContractError("token_probe_provider_call_count_invalid", count_name)
    except Exception as exc:
        code = (
            exc.code
            if isinstance(exc, P3ContractError)
            else "token_probe_transport_failure_no_retry"
        )
        failure = _signed_record(
            {
                "schema": "uruha_p3_tokenizer_probe_failure_v1",
                "request_sha256": request_sha,
                "code": code,
                "error_type": type(exc).__name__,
                "error_sha256": canonical_sha256(str(exc)),
            }
        )
        write_new_json(failure_path, failure)
        if isinstance(exc, P3ContractError):
            raise
        raise P3ContractError(
            "token_probe_transport_failure_no_retry",
            type(exc).__name__,
        ) from exc
    result = {
        "transport": transport_id,
        "fixture_id": fixture["fixture_id"],
        "fixture_role": fixture["role"],
        "request_sha256": request_sha,
        "hf_prompt_tokens": hf_prompt_tokens,
        "provider_prompt_tokens": prompt_tokens,
        "offset": prompt_tokens - hf_prompt_tokens,
        "completion_tokens": completion_tokens,
        "output_sha256": canonical_sha256(content),
        "wall_seconds": round(float(elapsed), 6),
        "provider_call_evidence": response["real_model_calls"],
        "real_model_calls": response["real_model_calls"],
        "network_calls": response["network_calls"],
        "reused": False,
    }
    complete = _signed_record(
        {
            "schema": "uruha_p3_tokenizer_probe_complete_v1",
            "request_sha256": request_sha,
            "result": result,
        }
    )
    write_new_json(complete_path, complete)
    return result


def execute_tokenizer_binding_probe(
    *,
    probe: Mapping[str, Any],
    token_counter: Callable[[Iterable[Mapping[str, str]]], int],
    transports: Mapping[
        str,
        Callable[[Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]],
    ],
    checkpoint_root: str | Path,
    evidence_kind: str,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    if evidence_kind not in {"contract_fake", "local_ollama_provider_usage"}:
        raise P3ContractError("token_probe_evidence_kind_invalid")
    expected_transports = [transport["id"] for transport in probe["transports"]]
    if set(transports) != set(expected_transports):
        raise P3ContractError("token_probe_transport_set_mismatch")
    started = clock()
    rows: list[dict[str, Any]] = []
    hf_counts: dict[str, int] = {}
    for fixture in probe["fixtures"]:
        count = token_counter(fixture["messages"])
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
            raise P3ContractError("token_probe_hf_count_invalid", fixture["fixture_id"])
        hf_counts[fixture["fixture_id"]] = count
    for transport_id in expected_transports:
        for fixture in probe["fixtures"]:
            rows.append(
                _run_token_probe_call_once(
                    probe=probe,
                    transport_id=transport_id,
                    fixture=fixture,
                    hf_prompt_tokens=hf_counts[fixture["fixture_id"]],
                    transport=transports[transport_id],
                    checkpoint_root=checkpoint_root,
                    clock=clock,
                )
            )
    total_wall = clock() - started
    if total_wall > probe["generation_options"]["total_wall_seconds_max"]:
        raise P3ContractError("token_probe_total_wall_exceeded")
    fit_ids = set(probe["fit_and_verification"]["fit_fixture_ids"])
    verification_id = probe["fit_and_verification"]["verification_fixture_ids"][0]
    offsets: dict[str, int | None] = {}
    fit_offset_consistent: dict[str, bool] = {}
    verification_exact: dict[str, bool] = {}
    for transport_id in expected_transports:
        transport_rows = [row for row in rows if row["transport"] == transport_id]
        fit_offsets = {row["offset"] for row in transport_rows if row["fixture_id"] in fit_ids}
        fit_offset_consistent[transport_id] = len(fit_offsets) == 1
        offset = next(iter(fit_offsets)) if len(fit_offsets) == 1 else None
        offsets[transport_id] = offset
        verify_row = next(row for row in transport_rows if row["fixture_id"] == verification_id)
        verification_exact[transport_id] = (
            offset is not None
            and verify_row["provider_prompt_tokens"]
            == verify_row["hf_prompt_tokens"] + offset
        )
    provider_counts_match = all(
        len(
            {
                row["provider_prompt_tokens"]
                for row in rows
                if row["fixture_id"] == fixture["fixture_id"]
            }
        )
        == 1
        for fixture in probe["fixtures"]
    )
    is_fake = evidence_kind == "contract_fake"
    provider_evidence_calls = sum(row["provider_call_evidence"] for row in rows)
    newly_executed_calls = sum(row["real_model_calls"] for row in rows)
    expected_provider_evidence = (
        0 if is_fake else probe["execution_boundary"]["expected_provider_calls"]
    )
    checks = {
        "eight_evidence_rows": len(rows) == 8,
        "fit_offsets_consistent": all(fit_offset_consistent.values()),
        "verification_exact": all(verification_exact.values()),
        "provider_counts_match_across_transports": provider_counts_match,
        "completion_tokens_within_total": sum(row["completion_tokens"] for row in rows)
        <= probe["execution_boundary"]["maximum_completion_tokens_total"],
        "no_output_text_retained": all("content" not in row for row in rows),
        "call_counts_within_release": newly_executed_calls
        <= probe["execution_boundary"]["maximum_provider_calls"],
        "provider_call_evidence_exact_for_scope": provider_evidence_calls
        == expected_provider_evidence,
    }
    status = (
        "offline_tokenizer_contract_pass"
        if is_fake and all(checks.values())
        else "provider_binding_pass"
        if not is_fake and all(checks.values())
        else "binding_failed_retained"
    )
    return {
        "schema": "uruha_p3_tokenizer_binding_probe_result_v1",
        "phase": "P3-B3",
        "status": status,
        "evidence_kind": evidence_kind,
        "probe_sha256": probe["_probe_sha256"],
        "rows": rows,
        "transport_offsets": offsets,
        "fit_offset_consistent": fit_offset_consistent,
        "verification_exact": verification_exact,
        "provider_counts_match_across_transports": provider_counts_match,
        "checks": checks,
        "total_wall_seconds": round(float(total_wall), 6),
        "provider_call_evidence": provider_evidence_calls,
        "real_model_calls": newly_executed_calls,
        "network_calls": sum(row["network_calls"] for row in rows),
        "paid_calls": 0,
        "output_text_retained": False,
        "binding_verified": (not is_fake and all(checks.values())),
        "claim_boundary": (
            "A passing local-provider result binds token counts only for this frozen "
            "model/template and probe shape; it is not reply-quality evidence."
        ),
    }


def build_tokenizer_probe_contract(probe_path: str | Path, checkpoint_root: str | Path) -> dict[str, Any]:
    probe = load_tokenizer_binding_probe(probe_path)

    def counter(messages: Iterable[Mapping[str, str]]) -> int:
        return 20 + sum(len(message["content"].encode("utf-8")) for message in messages)

    def fake(backend: str) -> Callable[[Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]]:
        def transport(fixture: Mapping[str, Any], raw_probe: Mapping[str, Any]) -> Mapping[str, Any]:
            return {
                "backend": backend,
                "model": raw_probe["model"]["ollama_model"],
                "prompt_tokens": counter(fixture["messages"]) + 2,
                "completion_tokens": 1,
                "content": f"contract-output-{backend}-{fixture['fixture_id']}",
                "real_model_calls": 0,
                "network_calls": 0,
            }

        return transport

    ticks = iter(float(index) * 0.01 for index in range(20))
    return execute_tokenizer_binding_probe(
        probe=probe,
        token_counter=counter,
        transports={transport_id: fake(transport_id) for transport_id in (
            "openai_compatible_local",
            "native_ollama_chat",
        )},
        checkpoint_root=checkpoint_root,
        evidence_kind="contract_fake",
        clock=lambda: next(ticks),
    )


def _local_provider_transport(
    transport_id: str,
) -> Callable[[Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]]:
    def transport(
        fixture: Mapping[str, Any], probe: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        transport_config = next(
            item for item in probe["transports"] if item["id"] == transport_id
        )
        options = probe["generation_options"]
        if transport_id == "openai_compatible_local":
            request_body = {
                "model": probe["model"]["ollama_model"],
                "messages": fixture["messages"],
                "temperature": options["temperature"],
                "seed": options["seed"],
                "top_p": options["top_p"],
                "max_tokens": options["max_completion_tokens"],
                "stream": options["stream"],
                "think": options["think"],
                "options": {"num_ctx": options["num_ctx"]},
            }
        else:
            request_body = {
                "model": probe["model"]["ollama_model"],
                "messages": fixture["messages"],
                "stream": options["stream"],
                "think": options["think"],
                "options": {
                    "temperature": options["temperature"],
                    "seed": options["seed"],
                    "top_p": options["top_p"],
                    "num_ctx": options["num_ctx"],
                    "num_predict": options["max_completion_tokens"],
                },
            }
        request = urllib.request.Request(
            transport_config["url"],
            data=json.dumps(request_body, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(
            request,
            timeout=options["per_call_timeout_seconds"],
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, Mapping):
            raise P3ContractError("token_probe_provider_payload_invalid")
        if transport_id == "openai_compatible_local":
            try:
                content = payload["choices"][0]["message"]["content"]
                prompt_tokens = payload["usage"]["prompt_tokens"]
                completion_tokens = payload["usage"]["completion_tokens"]
            except (KeyError, IndexError, TypeError) as exc:
                raise P3ContractError("token_probe_provider_payload_invalid") from exc
        else:
            content = (payload.get("message") or {}).get("content")
            prompt_tokens = payload.get("prompt_eval_count")
            completion_tokens = payload.get("eval_count")
        return {
            "backend": transport_id,
            "model": payload.get("model"),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "content": content,
            "real_model_calls": 1,
            "network_calls": 1,
        }

    return transport


def run_local_tokenizer_binding_probe(
    probe_path: str | Path,
    release_path: str | Path,
    checkpoint_root: str | Path,
) -> dict[str, Any]:
    probe = load_tokenizer_binding_probe(probe_path)
    release = validate_tokenizer_probe_release(release_path, probe)
    repo = Path(release_path).resolve().parent.parent
    expected_checkpoint = (repo / release["authorization"]["checkpoint_root"]).resolve()
    actual_checkpoint = Path(checkpoint_root).resolve()
    if actual_checkpoint != expected_checkpoint:
        raise P3ContractError("token_probe_checkpoint_path_mismatch")
    metadata = _ollama_model_metadata(probe["model"]["ollama_model"])
    if metadata["digest"] != release["authorization"]["model_digest"]:
        raise P3ContractError("token_probe_runtime_model_digest_mismatch")
    tokenizer = LocalQwenTokenizerCandidate(probe["model"]["hf_tokenizer"])
    result = execute_tokenizer_binding_probe(
        probe=probe,
        token_counter=tokenizer,
        transports={
            transport["id"]: _local_provider_transport(transport["id"])
            for transport in probe["transports"]
        },
        checkpoint_root=actual_checkpoint,
        evidence_kind="local_ollama_provider_usage",
    )
    result["release_sha256"] = hashlib.sha256(Path(release_path).read_bytes()).hexdigest()
    result["model_metadata"] = metadata
    return result


def build_openai_call(
    design: Mapping[str, Any], messages: list[dict[str, str]], cap: int
) -> dict[str, Any]:
    model = design["model"]
    return {
        "model": model["generation_model"],
        "messages": messages,
        "temperature": model["temperature"],
        "seed": model["seed"],
        "top_p": model["top_p"],
        "max_tokens": cap,
        "extra_body": {
            "options": {"num_ctx": model["num_ctx"]},
            "think": model["think"],
        },
    }


def build_native_call(
    design: Mapping[str, Any], messages: list[dict[str, str]], cap: int
) -> dict[str, Any]:
    model = design["model"]
    return {
        "model": model["generation_model"],
        "messages": messages,
        "stream": False,
        "think": model["think"],
        "options": {
            "temperature": model["temperature"],
            "seed": model["seed"],
            "top_p": model["top_p"],
            "num_ctx": model["num_ctx"],
            "num_predict": cap,
        },
    }


def _message_rows(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise P3ContractError("adapter_messages_invalid")
    result: list[dict[str, str]] = []
    for row in value:
        if not isinstance(row, Mapping) or set(row) != {"role", "content"}:
            raise P3ContractError("adapter_messages_invalid")
        role, content = row["role"], row["content"]
        if role not in {"system", "user", "assistant"} or not isinstance(content, str):
            raise P3ContractError("adapter_messages_invalid")
        result.append({"role": role, "content": content})
    return result


class ProductTransportGate:
    """Pre-call budget/model guard for both product transport routes."""

    def __init__(
        self,
        design: Mapping[str, Any],
        token_counter: Callable[[Iterable[Mapping[str, str]]], int],
        *,
        allow_real_transport: bool = False,
        provider_binding_verified: bool = False,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.design = design
        self.token_counter = token_counter
        self.allow_real_transport = allow_real_transport
        self.provider_binding_verified = provider_binding_verified
        self.clock = clock
        self.budget = new_budget(design, "product_system")
        self.interceptions: list[dict[str, Any]] = []

    def _assert_transport_release(self, contract_fake: bool) -> None:
        if contract_fake:
            return
        if not self.allow_real_transport:
            raise P3ContractError("real_product_transport_not_released")
        if not self.provider_binding_verified:
            raise P3ContractError("provider_tokenizer_binding_unverified")

    def _reserve(
        self,
        *,
        backend: str,
        stage: str,
        messages: list[dict[str, str]],
        cap: int,
    ) -> dict[str, Any]:
        prompt_tokens = self.token_counter(messages)
        if isinstance(prompt_tokens, bool) or not isinstance(prompt_tokens, int):
            raise P3ContractError("token_count_unavailable")
        request = make_request(
            design=self.design,
            condition="product_system",
            stage=stage,
            messages=messages,
            prompt_tokens=prompt_tokens,
            max_completion_tokens=cap,
            backend=backend,
        )
        return {"request": request, "reservation": reserve_call(self.budget, request)}

    def _finish(
        self,
        *,
        backend: str,
        stage: str,
        reservation: Mapping[str, Any],
        prompt_tokens: Any,
        completion_tokens: Any,
        content: Any,
        response_model: Any,
        elapsed: float,
        contract_fake: bool,
    ) -> dict[str, Any]:
        if response_model != self.design["model"]["generation_model"]:
            mark_transport_failure(self.budget, "transport_model_mismatch")
            raise P3ContractError("transport_model_mismatch")
        if not isinstance(content, str):
            mark_transport_failure(self.budget, "invalid_transport_payload")
            raise P3ContractError("invalid_transport_payload")
        usage = record_usage(
            self.budget,
            {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "wall_seconds": elapsed,
            },
            reservation,
        )
        row = {
            "backend": backend,
            "stage": stage,
            "model": response_model,
            "request_sha256": reservation["request_sha256"],
            "content_sha256": canonical_sha256(content),
            "usage": usage,
            "contract_fake": contract_fake,
            "network_calls": 0 if contract_fake else 1,
            "real_model_calls": 0 if contract_fake else 1,
        }
        self.interceptions.append(row)
        return {"content": content, **row}

    def intercept_openai(
        self,
        *,
        stage: str,
        call_kwargs: Mapping[str, Any],
        transport: Callable[[Mapping[str, Any]], Mapping[str, Any]],
        contract_fake: bool = False,
    ) -> dict[str, Any]:
        self._assert_transport_release(contract_fake)
        messages = _message_rows(call_kwargs.get("messages"))
        cap = call_kwargs.get("max_tokens")
        expected = build_openai_call(self.design, messages, cap)
        if dict(call_kwargs) != expected:
            raise P3ContractError("openai_product_options_mismatch")
        reserved = self._reserve(
            backend="openai_compatible_local",
            stage=stage,
            messages=messages,
            cap=cap,
        )
        started = self.clock()
        try:
            response = transport(call_kwargs)
        except Exception as exc:
            mark_transport_failure(self.budget, "transport_failure_no_retry")
            raise P3ContractError("transport_failure_no_retry", type(exc).__name__) from exc
        elapsed = self.clock() - started
        if not isinstance(response, Mapping) or not isinstance(response.get("usage"), Mapping):
            mark_transport_failure(self.budget, "invalid_transport_payload")
            raise P3ContractError("invalid_transport_payload")
        choices = response.get("choices")
        try:
            content = choices[0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            mark_transport_failure(self.budget, "invalid_transport_payload")
            raise P3ContractError("invalid_transport_payload") from exc
        return self._finish(
            backend="openai_compatible_local",
            stage=stage,
            reservation=reserved["reservation"],
            prompt_tokens=response["usage"].get("prompt_tokens"),
            completion_tokens=response["usage"].get("completion_tokens"),
            content=content,
            response_model=response.get("model"),
            elapsed=elapsed,
            contract_fake=contract_fake,
        )

    def intercept_native(
        self,
        *,
        stage: str,
        request_body: Mapping[str, Any],
        transport: Callable[[Mapping[str, Any]], Mapping[str, Any]],
        contract_fake: bool = False,
    ) -> dict[str, Any]:
        self._assert_transport_release(contract_fake)
        messages = _message_rows(request_body.get("messages"))
        options = request_body.get("options")
        if not isinstance(options, Mapping):
            raise P3ContractError("native_product_options_mismatch")
        cap = options.get("num_predict")
        expected = build_native_call(self.design, messages, cap)
        if dict(request_body) != expected:
            raise P3ContractError("native_product_options_mismatch")
        reserved = self._reserve(
            backend="native_ollama_chat",
            stage=stage,
            messages=messages,
            cap=cap,
        )
        started = self.clock()
        try:
            response = transport(request_body)
        except Exception as exc:
            mark_transport_failure(self.budget, "transport_failure_no_retry")
            raise P3ContractError("transport_failure_no_retry", type(exc).__name__) from exc
        elapsed = self.clock() - started
        if not isinstance(response, Mapping):
            mark_transport_failure(self.budget, "invalid_transport_payload")
            raise P3ContractError("invalid_transport_payload")
        content = (response.get("message") or {}).get("content")
        return self._finish(
            backend="native_ollama_chat",
            stage=stage,
            reservation=reserved["reservation"],
            prompt_tokens=response.get("prompt_eval_count"),
            completion_tokens=response.get("eval_count"),
            content=content,
            response_model=response.get("model"),
            elapsed=elapsed,
            contract_fake=contract_fake,
        )


def _value(value: Any, name: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(name)
    return getattr(value, name, None)


def _openai_response_mapping(response: Any) -> dict[str, Any]:
    choices = _value(response, "choices") or []
    mapped_choices = []
    for choice in choices:
        message = _value(choice, "message")
        mapped_choices.append(
            {"message": {"content": _value(message, "content")}}
        )
    usage = _value(response, "usage")
    return {
        "model": _value(response, "model"),
        "choices": mapped_choices,
        "usage": {
            "prompt_tokens": _value(usage, "prompt_tokens"),
            "completion_tokens": _value(usage, "completion_tokens"),
        },
    }


class _GuardedCompletions:
    def __init__(self, target: Any, gate: ProductTransportGate) -> None:
        self._target = target
        self._gate = gate

    def create(self, *args: Any, **kwargs: Any) -> Any:
        if args:
            raise P3ContractError("positional_product_generation_forbidden")
        captured: dict[str, Any] = {}

        def transport(call_kwargs: Mapping[str, Any]) -> Mapping[str, Any]:
            response = self._target.create(**dict(call_kwargs))
            captured["response"] = response
            return _openai_response_mapping(response)

        self._gate.intercept_openai(
            stage=f"product_openai_{self._gate.budget.attempts + 1}",
            call_kwargs=kwargs,
            transport=transport,
        )
        return captured["response"]


class _GuardedChat:
    def __init__(self, target: Any, gate: ProductTransportGate) -> None:
        self._target = target
        self.completions = _GuardedCompletions(target.completions, gate)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._target, name)


class _OfflineModelsMetadata:
    """Satisfy the product's startup probe without an unaccounted network call."""

    def __init__(self, model: str) -> None:
        self.model = model

    def list(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        if args or kwargs:
            raise P3ContractError("model_metadata_probe_arguments_forbidden")
        return {"data": [{"id": self.model}], "source": "reviewed_preflight_metadata"}


class ProductCallShapeObserver:
    """Record product call shapes without forwarding any model request."""

    def __init__(
        self,
        design: Mapping[str, Any],
        token_counter: Callable[[Iterable[Mapping[str, str]]], int],
        *,
        maximum_attempts: int = 16,
    ) -> None:
        self.design = design
        self.token_counter = token_counter
        self.maximum_attempts = maximum_attempts
        self.native_url = "http://127.0.0.1:11434/api/chat"
        self.calls: list[dict[str, Any]] = []

    @staticmethod
    def _optional_field(value: Mapping[str, Any], key: str) -> dict[str, Any]:
        return {"present": key in value, "value": value.get(key)}

    def _record(
        self,
        *,
        backend: str,
        messages: Any,
        payload: Mapping[str, Any],
        cap_key: str,
        option_source: Mapping[str, Any],
    ) -> None:
        if len(self.calls) >= self.maximum_attempts:
            raise P3ContractError("product_call_shape_attempt_cap_exceeded")
        rows = _message_rows(messages)
        prompt_tokens = self.token_counter(rows)
        model = payload.get("model")
        temperature = option_source.get("temperature")
        seed = option_source.get("seed")
        top_p = option_source.get("top_p")
        num_ctx = option_source.get("num_ctx")
        think = payload.get("think")
        if backend == "openai_compatible_local":
            extra_body = payload.get("extra_body")
            extra_options = (
                extra_body.get("options")
                if isinstance(extra_body, Mapping)
                and isinstance(extra_body.get("options"), Mapping)
                else {}
            )
            seed = payload.get("seed")
            top_p = payload.get("top_p")
            num_ctx = extra_options.get("num_ctx")
            think = extra_body.get("think") if isinstance(extra_body, Mapping) else None
        generation = {
            "temperature": self._optional_field(option_source, "temperature"),
            "seed": {"present": seed is not None, "value": seed},
            "top_p": {"present": top_p is not None, "value": top_p},
            "num_ctx": {"present": num_ctx is not None, "value": num_ctx},
            "think": {"present": think is not None, "value": think},
            "completion_cap": self._optional_field(option_source, cap_key),
        }
        frozen_model = self.design["model"]
        cap = generation["completion_cap"]["value"]
        normalization = {
            "model_exact": model == frozen_model["generation_model"],
            "temperature_exact": temperature == frozen_model["temperature"],
            "seed_exact": seed == frozen_model["seed"],
            "top_p_exact": top_p == frozen_model["top_p"],
            "num_ctx_exact": num_ctx == frozen_model["num_ctx"],
            "think_exact": think == frozen_model["think"],
            "completion_cap_present_and_within_system_limit": (
                isinstance(cap, int)
                and not isinstance(cap, bool)
                and 0 < cap
                <= self.design["budget"]["system_per_call_completion_max"]
            ),
        }
        self.calls.append(
            {
                "attempt_index": len(self.calls) + 1,
                "backend": backend,
                "kwarg_keys": sorted(str(key) for key in payload),
                "model": model,
                "message_count": len(rows),
                "message_roles": [row["role"] for row in rows],
                "messages_sha256": canonical_sha256(rows),
                "prompt_tokens": prompt_tokens,
                "generation": generation,
                "timeout_present": "timeout" in payload,
                "response_format_present": "response_format" in payload,
                "response_format_sha256": (
                    canonical_sha256(payload["response_format"])
                    if "response_format" in payload
                    else None
                ),
                "normalization": normalization,
                "forwarded_to_transport": False,
                "rejection_code": "product_call_shape_observed_no_generation",
            }
        )
        raise P3ContractError("product_call_shape_observed_no_generation")

    def observe_openai(self, args: tuple[Any, ...], kwargs: Mapping[str, Any]) -> None:
        if args:
            raise P3ContractError("positional_product_generation_forbidden")
        self._record(
            backend="openai_compatible_local",
            messages=kwargs.get("messages"),
            payload=kwargs,
            cap_key="max_tokens",
            option_source=kwargs,
        )

    def observe_native(self, request: Any, args: tuple[Any, ...]) -> None:
        if not isinstance(request, urllib.request.Request) or args:
            raise P3ContractError("unaccounted_product_network_route")
        try:
            payload = json.loads((request.data or b"").decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise P3ContractError("native_product_request_invalid") from exc
        if not isinstance(payload, Mapping) or str(request.full_url) != self.native_url:
            raise P3ContractError("unaccounted_product_network_route")
        options = payload.get("options")
        if not isinstance(options, Mapping):
            options = {}
        self._record(
            backend="native_ollama_chat",
            messages=payload.get("messages"),
            payload=payload,
            cap_key="num_predict",
            option_source=options,
        )


class _ObservedCompletions:
    def __init__(self, observer: ProductCallShapeObserver) -> None:
        self.observer = observer

    def create(self, *args: Any, **kwargs: Any) -> Any:
        self.observer.observe_openai(args, kwargs)


class _ObservedChat:
    def __init__(self, observer: ProductCallShapeObserver) -> None:
        self.completions = _ObservedCompletions(observer)


class _ObservedOpenAIClient:
    def __init__(self, observer: ProductCallShapeObserver) -> None:
        self.chat = _ObservedChat(observer)
        self.models = _OfflineModelsMetadata(
            observer.design["model"]["generation_model"]
        )


class _GuardedOpenAIClient:
    def __init__(self, target: Any, gate: ProductTransportGate) -> None:
        self._target = target
        self.chat = _GuardedChat(target.chat, gate)
        self.models = _OfflineModelsMetadata(gate.design["model"]["generation_model"])

    def __getattr__(self, name: str) -> Any:
        return getattr(self._target, name)


class _BufferedNativeResponse:
    def __init__(self, payload: bytes) -> None:
        self._buffer = io.BytesIO(payload)

    def read(self, *args: Any, **kwargs: Any) -> bytes:
        return self._buffer.read(*args, **kwargs)

    def close(self) -> None:
        self._buffer.close()

    def __enter__(self) -> "_BufferedNativeResponse":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()


def install_product_transport_gate(
    brain_module: Any,
    gate: ProductTransportGate,
) -> dict[str, Any]:
    """Bind the gate to the exact two globals used by the current product."""

    expected_model = gate.design["model"]["generation_model"]
    if getattr(brain_module, "M31_SEMANTIC_VERIFIER_MODEL", None) != expected_model:
        raise P3ContractError("m31_import_model_not_locked")
    original_openai = brain_module.OpenAI
    original_urlopen = brain_module.urllib.request.urlopen
    native_url = str(brain_module.M31_SEMANTIC_VERIFIER_URL)

    def guarded_openai(*args: Any, **kwargs: Any) -> _GuardedOpenAIClient:
        target = original_openai(*args, **kwargs)
        return _GuardedOpenAIClient(target, gate)

    def guarded_urlopen(request: Any, *args: Any, **kwargs: Any) -> _BufferedNativeResponse:
        if not isinstance(request, urllib.request.Request):
            raise P3ContractError("unaccounted_product_network_route")
        if str(request.full_url) != native_url or args:
            raise P3ContractError("unaccounted_product_network_route")
        try:
            request_body = json.loads((request.data or b"").decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise P3ContractError("native_product_request_invalid") from exc
        captured: dict[str, Any] = {}

        def transport(body: Mapping[str, Any]) -> Mapping[str, Any]:
            raw_response = original_urlopen(request, **kwargs)
            try:
                raw_payload = raw_response.read()
            finally:
                close = getattr(raw_response, "close", None)
                if callable(close):
                    close()
            captured["payload"] = raw_payload
            try:
                value = json.loads(raw_payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise P3ContractError("invalid_transport_payload") from exc
            if not isinstance(value, Mapping):
                raise P3ContractError("invalid_transport_payload")
            return value

        gate.intercept_native(
            stage=f"product_native_{gate.budget.attempts + 1}",
            request_body=request_body,
            transport=transport,
        )
        return _BufferedNativeResponse(captured["payload"])

    guarded_openai._p3_product_gate = gate  # type: ignore[attr-defined]
    guarded_urlopen._p3_product_gate = gate  # type: ignore[attr-defined]
    brain_module.OpenAI = guarded_openai
    brain_module.urllib.request.urlopen = guarded_urlopen
    return {
        "openai_global_guarded": getattr(brain_module.OpenAI, "_p3_product_gate", None)
        is gate,
        "native_urlopen_global_guarded": getattr(
            brain_module.urllib.request.urlopen,
            "_p3_product_gate",
            None,
        )
        is gate,
        "startup_models_list_network_bypassed": True,
        "unaccounted_network_routes_fail_closed": True,
        "real_transport_released": gate.allow_real_transport,
        "provider_binding_verified": gate.provider_binding_verified,
    }


def build_adapter_contract(design_path: str | Path) -> dict[str, Any]:
    design = load_design(design_path)

    def fixed_count(messages: Iterable[Mapping[str, str]]) -> int:
        return 96 + len(list(messages))

    ticks = iter([0.0, 0.01, 0.02, 0.035])
    gate = ProductTransportGate(design, fixed_count, clock=lambda: next(ticks))
    messages = [{"role": "user", "content": "確認用。"}]

    def fake_openai(kwargs: Mapping[str, Any]) -> Mapping[str, Any]:
        return {
            "model": kwargs["model"],
            "choices": [{"message": {"content": "分かった。"}}],
            "usage": {"prompt_tokens": fixed_count(kwargs["messages"]), "completion_tokens": 8},
        }

    def fake_native(body: Mapping[str, Any]) -> Mapping[str, Any]:
        return {
            "model": body["model"],
            "message": {"content": "うん。"},
            "prompt_eval_count": fixed_count(body["messages"]),
            "eval_count": 5,
        }

    with network_forbidden() as network_attempts:
        gate.intercept_openai(
            stage="adapter_openai_contract",
            call_kwargs=build_openai_call(design, messages, 128),
            transport=fake_openai,
            contract_fake=True,
        )
        gate.intercept_native(
            stage="adapter_native_contract",
            request_body=build_native_call(design, messages, 128),
            transport=fake_native,
            contract_fake=True,
        )
    return {
        "schema": ADAPTER_SCHEMA,
        "phase": "P3-B1",
        "status": "offline_transport_contract_pass",
        "design_sha256": design["_design_sha256"],
        "interceptions": gate.interceptions,
        "budget": gate.budget.snapshot(),
        "checks": {
            "openai_compatible_intercepted": gate.interceptions[0]["backend"]
            == "openai_compatible_local",
            "native_ollama_intercepted": gate.interceptions[1]["backend"]
            == "native_ollama_chat",
            "same_model_gate": all(
                row["model"] == design["model"]["generation_model"]
                for row in gate.interceptions
            ),
            "exact_usage_recorded": gate.budget.completed_calls == 2,
            "real_transport_disabled_by_default": gate.allow_real_transport is False,
            "network_forbidden_during_contract": len(network_attempts) == 0,
        },
        "network_attempts": network_attempts,
        "network_calls": 0,
        "real_model_calls": 0,
        "paid_calls": 0,
        "claim_boundary": (
            "Contract fakes prove pre-call interception and exact-usage plumbing only; "
            "they do not prove provider binding or product generation."
        ),
    }


def build_product_dry_run(
    design_path: str | Path,
    workspace_root: str | Path,
    case_id: str,
    state_slot: str | None = None,
) -> dict[str, Any]:
    design = load_design(design_path)
    case_workspace = claim_case_workspace(
        workspace_root,
        case_id,
        state_slot=state_slot,
    )
    env = prepare_isolated_environment(case_workspace, design)
    forbidden_modules = {"uruha_brain_mac", "uruha_web_ui", "uruha_web_ui_product"}
    already_loaded = sorted(forbidden_modules.intersection(sys.modules))
    if already_loaded:
        raise P3ContractError("product_import_not_fresh", ",".join(already_loaded))
    with network_forbidden() as attempts:
        import project_paths

        paths = case_workspace["paths"]
        project_paths.WEB_LOG_DIR = str(paths["web_logs"])
        project_paths.WEB_CONVERSATION_LOG_JSONL_PATH = env["URUHA_WEB_LOG_JSONL_PATH"]
        project_paths.WEB_CONVERSATION_LOG_TXT_PATH = env["URUHA_WEB_LOG_TXT_PATH"]
        product = importlib.import_module("uruha_web_ui_product")
        tokenizer = LocalQwenTokenizerCandidate()
        tokenizer_evidence = tokenizer.evidence()
    brain = product._brain
    base = product._base
    product_gate = ProductTransportGate(design, tokenizer)
    transport_binding = install_product_transport_gate(brain, product_gate)
    checks = {
        "product_entry_imported": product.__name__ == "uruha_web_ui_product",
        "brain_remained_lazy": getattr(product.RUNTIME, "_brain", None) is None,
        "prewarm_disabled": base.WEB_PREWARM_BRAIN is False,
        "idle_visible_disabled": brain.IDLE_VISIBLE_PROACTIVE_ENABLED is False,
        "rightbrain_model_loading_disabled": brain.RIGHT_BRAIN_MODEL_BLEND_ENABLED is False,
        "m31_model_locked": brain.M31_SEMANTIC_VERIFIER_MODEL
        == design["model"]["generation_model"],
        "memory_path_isolated": Path(brain.DB_PATH).resolve()
        == paths["memory"].resolve(),
        "production_db_unreachable": Path(brain.DB_PATH).resolve()
        != PRODUCTION_DB_PATH,
        "web_logs_isolated": Path(base.WEB_LOG_JSONL).resolve()
        == Path(env["URUHA_WEB_LOG_JSONL_PATH"]).resolve(),
        "no_network_attempts": len(attempts) == 0,
        "tokenizer_candidate_available": tokenizer_evidence["chat_template_present"],
        "provider_binding_still_unverified": tokenizer_evidence[
            "provider_usage_equivalence_validated"
        ]
        is False,
        "openai_product_route_guarded": transport_binding["openai_global_guarded"],
        "native_product_route_guarded": transport_binding[
            "native_urlopen_global_guarded"
        ],
        "real_transport_still_unreleased": transport_binding[
            "real_transport_released"
        ]
        is False,
    }
    return {
        "schema": DRY_RUN_SCHEMA,
        "phase": "P3-B1",
        "status": "isolated_import_pass" if all(checks.values()) else "isolated_import_failed",
        "design_sha256": design["_design_sha256"],
        "case_sha256": case_workspace["case_sha256"],
        "state_slot": case_workspace["state_slot"],
        "restart": case_workspace["restart"],
        "environment": {
            "m31_model": env["URUHA_M31_SEMANTIC_VERIFIER_MODEL"],
            "prewarm": env["URUHA_WEB_PREWARM_BRAIN"],
            "idle_visible": env["URUHA_IDLE_VISIBLE_PROACTIVE_ENABLED"],
            "rightbrain_model_blend": env["URUHA_RIGHT_BRAIN_MODEL_BLEND_ENABLED"],
            "offline": env["HF_HUB_OFFLINE"],
            "state_paths_sha256": canonical_sha256(
                {key: str(value.resolve()) for key, value in case_workspace["paths"].items()}
            ),
        },
        "tokenizer_candidate": tokenizer_evidence,
        "transport_binding": transport_binding,
        "checks": checks,
        "network_attempts": attempts,
        "network_calls": 0,
        "transport_attempts": 0,
        "real_model_calls": 0,
        "paid_calls": 0,
        "brain_instances": 0,
        "claim_boundary": (
            "This proves isolated product import and an offline tokenizer candidate only. "
            "Provider token equivalence and product generation remain unreleased."
        ),
    }


def build_product_call_shape_audit(
    design_path: str | Path,
    workspace_root: str | Path,
    case_id: str = "p3-b4-call-shape-fixture",
) -> dict[str, Any]:
    """Run one isolated product turn while every generation route is blocked."""

    design = load_design(design_path)
    case_workspace = claim_case_workspace(workspace_root, case_id)
    env = prepare_isolated_environment(case_workspace, design)
    forbidden_modules = {"uruha_brain_mac", "uruha_web_ui", "uruha_web_ui_product"}
    already_loaded = sorted(forbidden_modules.intersection(sys.modules))
    if already_loaded:
        raise P3ContractError("product_import_not_fresh", ",".join(already_loaded))
    synthetic_input = "今日は少し眠い。"
    turn_completed = False
    turn_error_code: str | None = None
    reply_sha256: str | None = None
    brain_instance: Any = None
    observer: ProductCallShapeObserver | None = None
    with network_forbidden() as network_attempts:
        import project_paths

        paths = case_workspace["paths"]
        project_paths.WEB_LOG_DIR = str(paths["web_logs"])
        project_paths.WEB_CONVERSATION_LOG_JSONL_PATH = env["URUHA_WEB_LOG_JSONL_PATH"]
        project_paths.WEB_CONVERSATION_LOG_TXT_PATH = env["URUHA_WEB_LOG_TXT_PATH"]
        product = importlib.import_module("uruha_web_ui_product")
        brain_module = product._brain
        tokenizer = LocalQwenTokenizerCandidate()
        observer = ProductCallShapeObserver(design, tokenizer)
        observer.native_url = str(brain_module.M31_SEMANTIC_VERIFIER_URL)
        original_openai = brain_module.OpenAI
        original_urlopen = brain_module.urllib.request.urlopen

        def observed_openai(*args: Any, **kwargs: Any) -> _ObservedOpenAIClient:
            return _ObservedOpenAIClient(observer)

        def observed_urlopen(request: Any, *args: Any, **kwargs: Any) -> Any:
            observer.observe_native(request, args)

        brain_module.OpenAI = observed_openai
        brain_module.urllib.request.urlopen = observed_urlopen
        try:
            brain_instance = product.RUNTIME.get_brain()
            try:
                turn = brain_instance.run_turn_debug(
                    synthetic_input,
                    input_context={"input_mode": "text", "acoustic_summary": None},
                )
                reply = turn.get("reply") if isinstance(turn, Mapping) else None
                if isinstance(reply, str):
                    reply_sha256 = canonical_sha256(reply)
                turn_completed = isinstance(reply, str) and bool(reply.strip())
            except P3ContractError as exc:
                turn_error_code = exc.code
        finally:
            brain_module.OpenAI = original_openai
            brain_module.urllib.request.urlopen = original_urlopen
    calls = list(observer.calls if observer is not None else [])
    drift_counts: dict[str, int] = {}
    for call in calls:
        for field, passed in call["normalization"].items():
            if not passed:
                drift_counts[field] = drift_counts.get(field, 0) + 1
    paths = case_workspace["paths"]
    checks = {
        "product_brain_instantiated": brain_instance is not None,
        "production_db_unreachable": Path(brain_module.DB_PATH).resolve()
        == paths["memory"].resolve()
        and Path(brain_module.DB_PATH).resolve() != PRODUCTION_DB_PATH,
        "at_least_one_call_shape_observed": len(calls) >= 1,
        "all_generation_stopped_before_transport": all(
            call["forwarded_to_transport"] is False for call in calls
        ),
        "no_socket_or_unaccounted_url_attempts": len(network_attempts) == 0,
        "no_raw_dialogue_in_result": all(
            "messages" not in call and "content" not in call for call in calls
        ),
    }
    return {
        "schema": "uruha_p3_product_call_shape_audit_v1",
        "phase": "P3-B4",
        "status": (
            "p3_b4_call_shape_audit_pass"
            if all(checks.values())
            else "p3_b4_call_shape_audit_failed"
        ),
        "design_sha256": design["_design_sha256"],
        "case_sha256": case_workspace["case_sha256"],
        "synthetic_input_sha256": canonical_sha256(synthetic_input),
        "turn_completed_with_fallback": turn_completed,
        "turn_error_code": turn_error_code,
        "reply_sha256": reply_sha256,
        "call_shapes": calls,
        "observed_attempts": len(calls),
        "normalization_drift_counts": drift_counts,
        "checks": checks,
        "environment": {
            "memory_path_sha256": canonical_sha256(env["URUHA_MEMORY_DB_PATH"]),
            "web_log_path_sha256": canonical_sha256(env["URUHA_WEB_LOG_JSONL_PATH"]),
            "m31_model": env["URUHA_M31_SEMANTIC_VERIFIER_MODEL"],
            "prewarm": env["URUHA_WEB_PREWARM_BRAIN"],
            "idle_visible": env["URUHA_IDLE_VISIBLE_PROACTIVE_ENABLED"],
        },
        "network_attempts": network_attempts,
        "network_calls": 0,
        "real_model_calls": 0,
        "paid_calls": 0,
        "developer_smoke_cases_accessed": 0,
        "production_database_accessed": False,
        "claim_boundary": (
            "This audit observes real product call shapes while blocking every generation "
            "before transport. It is adapter-design evidence, not output-quality evidence."
        ),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=(
            "dry-run",
            "adapter-contract",
            "tokenizer-preflight",
            "tokenizer-contract",
            "tokenizer-run",
            "call-shape-audit",
        ),
        required=True,
    )
    parser.add_argument("--design", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--workspace-root")
    parser.add_argument("--case-id")
    parser.add_argument("--state-slot")
    parser.add_argument("--probe")
    parser.add_argument("--probe-release")
    parser.add_argument("--checkpoint-root")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output = Path(args.output)
    if output.exists():
        return 2
    try:
        if args.mode == "adapter-contract":
            payload = build_adapter_contract(args.design)
        elif args.mode == "dry-run":
            if not args.workspace_root or not args.case_id:
                raise P3ContractError("dry_run_workspace_and_case_required")
            payload = build_product_dry_run(
                args.design,
                args.workspace_root,
                args.case_id,
                args.state_slot,
            )
        elif args.mode == "tokenizer-preflight":
            if not args.probe:
                raise P3ContractError("token_probe_path_required")
            payload = build_tokenizer_probe_preflight(args.probe)
        elif args.mode == "tokenizer-contract":
            if not args.probe:
                raise P3ContractError("token_probe_path_required")
            if args.checkpoint_root:
                payload = build_tokenizer_probe_contract(
                    args.probe,
                    args.checkpoint_root,
                )
            else:
                import tempfile

                with tempfile.TemporaryDirectory(prefix="uruha-p3-token-contract-") as temporary:
                    payload = build_tokenizer_probe_contract(args.probe, temporary)
        elif args.mode == "tokenizer-run":
            if not args.probe or not args.probe_release or not args.checkpoint_root:
                raise P3ContractError("token_probe_run_artifacts_required")
            release = _read_json(Path(args.probe_release))
            repo = Path(args.probe_release).resolve().parent.parent
            expected_output = (
                repo / str((release.get("authorization") or {}).get("result_path"))
            ).resolve()
            if output.resolve() != expected_output:
                raise P3ContractError("token_probe_result_path_mismatch")
            payload = run_local_tokenizer_binding_probe(
                args.probe,
                args.probe_release,
                args.checkpoint_root,
            )
        else:
            import tempfile

            with tempfile.TemporaryDirectory(prefix="uruha-p3b4-call-shape-") as temporary:
                temporary_path = Path(temporary)
                payload = build_product_call_shape_audit(
                    args.design,
                    temporary_path / "workspace",
                )
            payload["ephemeral_workspace_removed_after_audit"] = not temporary_path.exists()
        write_new_json(output, payload)
        return 0 if payload.get("status") in {
            "isolated_import_pass",
            "offline_transport_contract_pass",
            "ready_for_execution_review",
            "offline_tokenizer_contract_pass",
            "provider_binding_pass",
            "p3_b4_call_shape_audit_pass",
        } else 3
    except P3ContractError as exc:
        blocked_network_attempt = exc.code == "network_attempt_during_product_dry_run"
        phase = "P3-B3" if args.mode.startswith("tokenizer-") else "P3-B1"
        failure = {
            "schema": "uruha_p3_product_worker_failure_v1",
            "phase": phase,
            "status": "refused_before_product_transport",
            "contract_code": exc.code,
            "detail_sha256": canonical_sha256(exc.detail),
            "transport_attempts": 0,
            "network_attempts": 1 if blocked_network_attempt else 0,
            "network_calls": 0,
            "real_model_calls": 0,
            "paid_calls": 0,
        }
        if not output.exists():
            write_new_json(output, failure)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
