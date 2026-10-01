#!/usr/bin/env python3
"""P3-B12 exact tokenizer binding for user-role private scratch shapes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time
from typing import Any, Mapping

from p3_product_comparison import P3ContractError, canonical_sha256, write_new_json
from p3_product_worker import (
    LocalOllamaQwenStageCounter,
    _local_provider_transport,
    _ollama_model_metadata,
    _ollama_template_sha256,
    _run_token_probe_call_once,
    localhost_network_only,
    network_forbidden,
    summarize_checkpoint_evidence,
)


SCHEMA = "uruha_p3_private_scratch_tokenizer_binding_probe_v1"
RELEASE_SCHEMA = "uruha_p3_private_scratch_tokenizer_binding_release_v1"
MODEL = "qwen2.5:7b"
MODEL_DIGEST = "2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730"
TEMPLATE_SHA = "eb4402837c7829a690fa845de4d7f3fd842c2adee476d5341da8a46ea9255175"


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise P3ContractError("p3_b12_invalid_json", str(path)) from exc
    if not isinstance(value, dict):
        raise P3ContractError("p3_b12_invalid_json", str(path))
    return value


def _reference(repo: Path, value: Any, expected: Mapping[str, str], code: str) -> Path:
    if value != dict(expected):
        raise P3ContractError(code)
    path = (repo / expected["path"]).resolve()
    try:
        path.relative_to(repo)
    except ValueError as exc:
        raise P3ContractError(code) from exc
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected["sha256"]:
        raise P3ContractError(code)
    return path


def load_probe(path: str | Path) -> dict[str, Any]:
    probe_path = Path(path)
    raw = _read(probe_path)
    if set(raw) != {
        "schema", "status", "purpose", "prior_stage_binding", "diagnostic_result",
        "model", "generation_options", "fixtures", "execution_boundary", "success",
    } or raw.get("schema") != SCHEMA:
        raise P3ContractError("p3_b12_schema_mismatch")
    if raw.get("status") != "preregistered_not_executed" or raw.get("purpose") != (
        "bind_exact_counts_for_user_role_labeled_private_scratch_shapes"
    ):
        raise P3ContractError("p3_b12_status_mismatch")
    repo = probe_path.resolve().parent.parent
    prior = _reference(repo, raw.get("prior_stage_binding"), {
        "path": "analysis/p3_b8_1_stage_tokenizer_binding_confirmation_result_2026-09-15.json",
        "sha256": "e360e626931d40ff52f5a217131541701a1eb69831fa3b249214dbb4fed5774f",
        "required_status": "stage_provider_binding_pass",
    }, "p3_b12_prior_reference_mismatch")
    diagnostic = _reference(repo, raw.get("diagnostic_result"), {
        "path": "analysis/p3_b11_instruction_language_probe_result_2026-09-15.json",
        "sha256": "baf6c4c1581dfc1fd2c26e36114791526ed117dd6e13bd4137feb2b84bf6957a",
        "required_status": "instruction_language_probe_pass",
    }, "p3_b12_diagnostic_reference_mismatch")
    if _read(prior).get("binding_verified") is not True or _read(diagnostic).get("status") != "instruction_language_probe_pass":
        raise P3ContractError("p3_b12_upstream_status_invalid")
    if raw.get("model") != {
        "ollama_model": MODEL,
        "ollama_blob_digest": MODEL_DIGEST,
        "hf_tokenizer": "Qwen/Qwen2.5-7B-Instruct",
        "ollama_template_sha256": TEMPLATE_SHA,
        "local_files_only": True,
    }:
        raise P3ContractError("p3_b12_model_mismatch")
    if raw.get("generation_options") != {
        "temperature": 0, "seed": 20260909, "top_p": 1, "num_ctx": 8192,
        "think": False, "max_completion_tokens": 1, "stream": False,
        "transport_retries": 0, "concurrency": 1,
        "per_call_timeout_seconds": 45, "total_wall_seconds_max": 90,
    }:
        raise P3ContractError("p3_b12_options_mismatch")
    fixtures = raw.get("fixtures")
    if not isinstance(fixtures, list) or len(fixtures) != 2 or {
        row.get("stage") for row in fixtures if isinstance(row, Mapping)
    } != {"critique", "revise"}:
        raise P3ContractError("p3_b12_fixture_set_mismatch")
    for row in fixtures:
        if not isinstance(row, Mapping) or set(row) != {
            "fixture_id", "role", "stage", "messages", "messages_sha256"
        } or row.get("role") != "verification":
            raise P3ContractError("p3_b12_fixture_shape_mismatch")
        messages = row.get("messages")
        if not isinstance(messages, list) or len(messages) != 3:
            raise P3ContractError("p3_b12_messages_mismatch")
        if [message.get("role") for message in messages] != ["system", "user", "user"]:
            raise P3ContractError("p3_b12_private_scratch_role_mismatch")
        if canonical_sha256(messages) != row.get("messages_sha256"):
            raise P3ContractError("p3_b12_messages_digest_mismatch")
    if raw.get("execution_boundary") != {
        "provider_calls_exact": 2, "automatic_retry": False, "localhost_only": True,
        "raw_output_retained": False, "developer_case_access": False,
        "annotation_access": False, "confirmation_access": False,
        "production_database_access": False, "external_deployment": False,
        "real_model_calls_authorized_by_this_config": False,
    } or raw.get("success") != {
        "every_fixture_exact": True, "tolerance_tokens": 0,
        "two_intents_two_completes": True, "output_text_retained": False,
    }:
        raise P3ContractError("p3_b12_boundary_mismatch")
    probe = json.loads(json.dumps(raw, ensure_ascii=False))
    probe["_probe_sha256"] = hashlib.sha256(probe_path.read_bytes()).hexdigest()
    probe["_probe_path"] = str(probe_path.resolve())
    probe["_phase"] = "P3-B12"
    probe["transports"] = [{
        "id": "openai_compatible_local",
        "url": "http://127.0.0.1:11434/v1/chat/completions",
        "usage_prompt_field": "usage.prompt_tokens",
        "usage_completion_field": "usage.completion_tokens",
    }]
    return probe


def build_preflight(path: str | Path) -> dict[str, Any]:
    probe = load_probe(path)
    metadata = _ollama_model_metadata(MODEL)
    template_sha = _ollama_template_sha256(MODEL)
    with network_forbidden() as attempts:
        counter = LocalOllamaQwenStageCounter(
            merge_adjacent_assistant=False,
            merge_adjacent_same_role=True,
        )
        rows = [{
            "fixture_id": fixture["fixture_id"],
            "stage": fixture["stage"],
            "offline_prompt_tokens": counter(fixture["messages"]),
        } for fixture in probe["fixtures"]]
    checks = {
        "probe_valid": True,
        "model_digest_matches": metadata["digest"] == MODEL_DIGEST,
        "template_digest_matches": template_sha == TEMPLATE_SHA,
        "two_positive_offline_counts": len(rows) == 2 and all(row["offline_prompt_tokens"] > 0 for row in rows),
        "same_role_collation_mode_enabled": counter.evidence()["adjacent_same_role_rule"] != "not_applied",
        "no_network_during_offline_count": not attempts,
        "config_does_not_self_authorize": probe["execution_boundary"]["real_model_calls_authorized_by_this_config"] is False,
    }
    return {
        "schema": "uruha_p3_private_scratch_tokenizer_preflight_v1",
        "phase": "P3-B12",
        "status": "ready_for_private_scratch_binding_review" if all(checks.values()) else "not_ready_for_private_scratch_binding_review",
        "probe_sha256": probe["_probe_sha256"],
        "rows": rows,
        "counter_evidence": counter.evidence(),
        "model_metadata": metadata,
        "ollama_template_sha256": template_sha,
        "checks": checks,
        "real_model_calls": 0, "network_calls": 0, "paid_calls": 0,
        "developer_case_accessed": 0, "annotations_accessed": 0,
        "claim_boundary": "Preflight only; no provider binding or reply-quality evidence.",
    }


def validate_release(path: str | Path, probe: Mapping[str, Any]) -> dict[str, Any]:
    release_path = Path(path)
    release = _read(release_path)
    if set(release) != {
        "schema", "phase", "status", "review_kind", "probe", "implementation_sha256",
        "preflight", "authorization", "claim_boundary",
    } or release.get("schema") != RELEASE_SCHEMA:
        raise P3ContractError("p3_b12_release_schema_mismatch")
    if release.get("phase") != "P3-B12" or release.get("status") != "released_for_private_scratch_binding_probe":
        raise P3ContractError("p3_b12_release_status_mismatch")
    if release.get("review_kind") != "same_task_self_review_not_independent":
        raise P3ContractError("p3_b12_release_review_mismatch")
    repo = release_path.resolve().parent.parent
    if release.get("probe") != {
        "path": "configs/p3_private_scratch_tokenizer_binding_probe_v1.json",
        "sha256": probe["_probe_sha256"],
    }:
        raise P3ContractError("p3_b12_release_probe_mismatch")
    implementation = release.get("implementation_sha256")
    required = {"p3_product_worker.py", "p3_private_scratch_tokenizer_probe.py", "test_p3_private_scratch_tokenizer_probe.py"}
    if not isinstance(implementation, Mapping) or set(implementation) != required:
        raise P3ContractError("p3_b12_release_implementation_invalid")
    for name, sha in implementation.items():
        if hashlib.sha256((repo / name).read_bytes()).hexdigest() != sha:
            raise P3ContractError("p3_b12_release_implementation_mismatch", name)
    preflight = release.get("preflight")
    preflight_path = (repo / str((preflight or {}).get("path"))).resolve()
    if not isinstance(preflight, Mapping) or set(preflight) != {"path", "sha256", "status"} or (
        not preflight_path.is_file()
        or hashlib.sha256(preflight_path.read_bytes()).hexdigest() != preflight.get("sha256")
        or preflight.get("status") != "ready_for_private_scratch_binding_review"
    ):
        raise P3ContractError("p3_b12_release_preflight_mismatch")
    if release.get("authorization") != {
        "run_id": "p3-b12-private-scratch-binding-v1", "localhost_only": True,
        "model": MODEL, "model_digest": MODEL_DIGEST, "provider_calls_exact": 2,
        "automatic_retry": False,
        "checkpoint_root": "analysis/p3_b12_private_scratch_binding_checkpoints_v1",
        "result_path": "analysis/p3_b12_private_scratch_binding_result_2026-09-15.json",
        "developer_case_access": False, "annotation_access": False,
        "confirmation_access": False, "production_database_access": False,
        "external_deployment": False,
    }:
        raise P3ContractError("p3_b12_release_authorization_mismatch")
    return release


def run_probe(probe_path: str | Path, release_path: str | Path, checkpoint_root: str | Path) -> dict[str, Any]:
    probe = load_probe(probe_path)
    release = validate_release(release_path, probe)
    repo = Path(release_path).resolve().parent.parent
    checkpoint = Path(checkpoint_root).resolve()
    if checkpoint != (repo / release["authorization"]["checkpoint_root"]).resolve():
        raise P3ContractError("p3_b12_checkpoint_path_mismatch")
    if _ollama_model_metadata(MODEL)["digest"] != MODEL_DIGEST or _ollama_template_sha256(MODEL) != TEMPLATE_SHA:
        raise P3ContractError("p3_b12_runtime_model_or_template_mismatch")
    counter = LocalOllamaQwenStageCounter(
        merge_adjacent_assistant=False,
        merge_adjacent_same_role=True,
    )
    started = time.monotonic()
    rows = []
    with localhost_network_only() as attempts:
        transport = _local_provider_transport("openai_compatible_local")
        for fixture in probe["fixtures"]:
            rows.append(_run_token_probe_call_once(
                probe=probe,
                transport_id="openai_compatible_local",
                fixture=fixture,
                hf_prompt_tokens=counter(fixture["messages"]),
                transport=transport,
                checkpoint_root=checkpoint,
                clock=time.monotonic,
            ))
    total_wall = time.monotonic() - started
    provider_calls = sum(row["provider_call_evidence"] for row in rows)
    checks = {
        "two_rows_two_stages": len(rows) == 2 and {row["stage"] for row in rows} == {"critique", "revise"},
        "every_fixture_exact": all(row["offset"] == 0 for row in rows),
        "two_intents_two_completes": provider_calls == 2,
        "completion_tokens_within_total": sum(row["completion_tokens"] for row in rows) <= 2,
        "no_output_text_retained": all("content" not in row for row in rows),
        "localhost_only": all(row["loopback_allowed"] is True for row in attempts),
        "total_wall_within_limit": total_wall <= probe["generation_options"]["total_wall_seconds_max"],
    }
    passed = all(checks.values())
    return {
        "schema": "uruha_p3_private_scratch_tokenizer_binding_result_v1",
        "phase": "P3-B12",
        "status": "private_scratch_binding_pass" if passed else "private_scratch_binding_failed_retained",
        "binding_verified": passed,
        "probe_sha256": probe["_probe_sha256"],
        "release_sha256": hashlib.sha256(Path(release_path).read_bytes()).hexdigest(),
        "rows": rows,
        "counter_evidence": counter.evidence(),
        "checks": checks,
        "total_wall_seconds": round(total_wall, 6),
        "provider_call_evidence": provider_calls,
        "real_model_calls": sum(row["real_model_calls"] for row in rows),
        "network_calls": sum(row["network_calls"] for row in rows),
        "paid_calls": 0, "output_text_retained": False,
        "developer_case_accessed": 0, "annotations_accessed": 0,
        "confirmation_accessed": 0, "production_database_accessed": False,
        "claim_boundary": "A pass binds exact counts for two user-role private-scratch shapes only. It is not response-quality or product-advantage evidence.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preflight", "run"), required=True)
    parser.add_argument("--probe", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--release")
    parser.add_argument("--checkpoint-root")
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        return 2
    try:
        if args.mode == "preflight":
            payload = build_preflight(args.probe)
        else:
            if not args.release or not args.checkpoint_root:
                raise P3ContractError("p3_b12_run_artifacts_required")
            release = _read(Path(args.release))
            repo = Path(args.release).resolve().parent.parent
            if output.resolve() != (repo / release["authorization"]["result_path"]).resolve():
                raise P3ContractError("p3_b12_result_path_mismatch")
            payload = run_probe(args.probe, args.release, args.checkpoint_root)
    except P3ContractError as exc:
        evidence = summarize_checkpoint_evidence(args.checkpoint_root or "")
        payload = {
            "schema": "uruha_p3_private_scratch_tokenizer_failure_v1", "phase": "P3-B12",
            "status": "failed_after_transport_retained" if evidence["declared_invocation_intents"] else "refused_before_transport",
            "contract_code": exc.code, "checkpoint_evidence": evidence,
            "real_model_calls": evidence["provider_call_evidence"],
            "network_calls": evidence["network_call_evidence"], "paid_calls": 0,
        }
    write_new_json(output, payload)
    return 0 if payload.get("status") in {"ready_for_private_scratch_binding_review", "private_scratch_binding_pass"} else 3


if __name__ == "__main__":
    raise SystemExit(main())
