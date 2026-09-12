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
import socket
import sys
import time
import urllib.request
from typing import Any, Callable, Iterable, Mapping
from unittest import mock

from p3_product_comparison import (
    P3ContractError,
    canonical_sha256,
    load_design,
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

    def blocked_socket(*args: Any, **kwargs: Any) -> Any:
        attempts.append({"api": "socket", "target_sha256": canonical_sha256(str(args[1:] or kwargs))})
        raise P3ContractError("network_attempt_during_product_dry_run")

    def blocked_urlopen(*args: Any, **kwargs: Any) -> Any:
        attempts.append({"api": "urlopen", "target_sha256": canonical_sha256(str(args[:1] or kwargs))})
        raise P3ContractError("network_attempt_during_product_dry_run")

    with mock.patch.object(socket.socket, "connect", blocked_socket), mock.patch.object(
        socket, "create_connection", blocked_socket
    ), mock.patch.object(urllib.request, "urlopen", blocked_urlopen):
        yield attempts


class LocalQwenTokenizerCandidate:
    """Offline tokenizer candidate; not yet provider-usage-equivalence evidence."""

    evidence_kind = "local_hf_chat_template_candidate_not_provider_validated"

    def __init__(self, model_name: str = "Qwen/Qwen2.5-7B-Instruct") -> None:
        from transformers import AutoTokenizer

        self.model_name = model_name
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name,
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
            "tokenizer_class": type(self.tokenizer).__name__,
            "chat_template_present": bool(template),
            "chat_template_sha256": canonical_sha256(template),
            "fixture_render_sha256": canonical_sha256(rendered),
            "fixture_prompt_tokens": self(fixture),
            "local_files_only": True,
            "provider_usage_equivalence_validated": False,
        }


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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("dry-run", "adapter-contract"), required=True)
    parser.add_argument("--design", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--workspace-root")
    parser.add_argument("--case-id")
    parser.add_argument("--state-slot")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output = Path(args.output)
    if output.exists():
        return 2
    try:
        if args.mode == "adapter-contract":
            payload = build_adapter_contract(args.design)
        else:
            if not args.workspace_root or not args.case_id:
                raise P3ContractError("dry_run_workspace_and_case_required")
            payload = build_product_dry_run(
                args.design,
                args.workspace_root,
                args.case_id,
                args.state_slot,
            )
        write_new_json(output, payload)
        return 0 if payload.get("status", "").endswith("pass") else 2
    except P3ContractError as exc:
        blocked_network_attempt = exc.code == "network_attempt_during_product_dry_run"
        failure = {
            "schema": "uruha_p3_product_worker_failure_v1",
            "phase": "P3-B1",
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
