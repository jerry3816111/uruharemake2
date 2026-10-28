#!/usr/bin/env python3
"""P3-B46 checkpoint adapter for the product's two real local transports."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Mapping
import urllib.request

from p3_product_comparison import P3ContractError, canonical_sha256, write_new_json
import p3_product_worker as worker


def _read(path: str | Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise P3ContractError("p3_b46_invalid_checkpoint_json", str(path)) from exc
    if not isinstance(value, dict):
        raise P3ContractError("p3_b46_invalid_checkpoint_json", str(path))
    return value


def _signed(payload: Mapping[str, Any]) -> dict[str, Any]:
    value = dict(payload)
    value["record_sha256"] = canonical_sha256(value)
    return value


def _verify_signed(value: Mapping[str, Any], code: str) -> None:
    expected = value.get("record_sha256")
    payload = dict(value)
    payload.pop("record_sha256", None)
    if not isinstance(expected, str) or expected != canonical_sha256(payload):
        raise P3ContractError(code)


def _safe_component(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def _normalize_provider_response(kind: str, response: Mapping[str, Any]) -> dict[str, Any]:
    if kind == "openai":
        choices = response.get("choices")
        usage = response.get("usage")
        try:
            content = choices[0]["message"]["content"]
        except (IndexError, KeyError, TypeError) as exc:
            raise P3ContractError("p3_b46_openai_response_invalid") from exc
        prompt_tokens = usage.get("prompt_tokens") if isinstance(usage, Mapping) else None
        completion_tokens = usage.get("completion_tokens") if isinstance(usage, Mapping) else None
        extra = {}
    elif kind == "native":
        message = response.get("message")
        content = message.get("content") if isinstance(message, Mapping) else None
        prompt_tokens = response.get("prompt_eval_count")
        completion_tokens = response.get("eval_count")
        extra = {
            key: response[key]
            for key in ("done", "done_reason", "total_duration", "load_duration", "prompt_eval_duration", "eval_duration")
            if key in response
        }
    else:
        raise P3ContractError("p3_b46_provider_kind_invalid", kind)
    if (
        not isinstance(content, str)
        or not isinstance(prompt_tokens, int) or isinstance(prompt_tokens, bool) or prompt_tokens < 0
        or not isinstance(completion_tokens, int) or isinstance(completion_tokens, bool) or completion_tokens < 0
        or not isinstance(response.get("model"), str)
    ):
        raise P3ContractError("p3_b46_provider_response_invalid", kind)
    return {
        "kind": kind, "model": response["model"], "content": content,
        "content_sha256": canonical_sha256(content),
        "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens},
        "extra": extra, "real_model_calls": 1, "network_calls": 1,
    }


def _reconstruct_provider_response(result: Mapping[str, Any]) -> dict[str, Any]:
    if result.get("content_sha256") != canonical_sha256(result.get("content")):
        raise P3ContractError("p3_b46_complete_output_digest_mismatch")
    usage = result.get("usage")
    if not isinstance(usage, Mapping):
        raise P3ContractError("p3_b46_complete_usage_invalid")
    if result.get("kind") == "openai":
        return {
            "model": result["model"],
            "choices": [{"message": {"content": result["content"]}}],
            "usage": dict(usage),
        }
    if result.get("kind") == "native":
        return {
            "model": result["model"], "message": {"role": "assistant", "content": result["content"]},
            "prompt_eval_count": usage["prompt_tokens"], "eval_count": usage["completion_tokens"],
            **dict(result.get("extra") or {}),
        }
    raise P3ContractError("p3_b46_complete_kind_invalid")


class ProviderCallJournal:
    """Immutable per-provider-call journal with complete-only reuse."""

    def __init__(
        self, root: str | Path, run_commitment_sha256: str,
        *, after_intent_hook: Callable[[str], None] | None = None,
    ) -> None:
        if not isinstance(run_commitment_sha256, str) or len(run_commitment_sha256) != 64:
            raise P3ContractError("p3_b46_run_commitment_invalid")
        self.root = Path(root)
        self.run_commitment_sha256 = run_commitment_sha256
        self.after_intent_hook = after_intent_hook
        self.last_call: dict[str, Any] | None = None

    def call_once(
        self, *, call_id: str, kind: str, stage: str, request: Mapping[str, Any],
        transport: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    ) -> dict[str, Any]:
        request_commitment = {
            "run_commitment_sha256": self.run_commitment_sha256,
            "call_id_sha256": canonical_sha256(call_id),
            "kind": kind, "stage": stage,
            "provider_request_sha256": canonical_sha256(request),
        }
        request_sha = canonical_sha256(request_commitment)
        folder = self.root / _safe_component(call_id) / _safe_component(stage)
        intent_path, complete_path, failure_path = (
            folder / "intent.json", folder / "complete.json", folder / "failure.json"
        )
        if failure_path.exists():
            failure = _read(failure_path)
            _verify_signed(failure, "p3_b46_failure_checkpoint_drift")
            raise P3ContractError("p3_b46_terminal_provider_failure_no_retry", call_id)
        if complete_path.exists():
            complete = _read(complete_path)
            _verify_signed(complete, "p3_b46_complete_checkpoint_drift")
            result = complete.get("result")
            if (
                complete.get("request_sha256") != request_sha
                or complete.get("run_commitment_sha256") != self.run_commitment_sha256
                or not isinstance(result, Mapping)
            ):
                raise P3ContractError("p3_b46_complete_checkpoint_source_mismatch", call_id)
            mapped = _reconstruct_provider_response(result)
            self.last_call = {
                "call_id": call_id, "stage": stage, "kind": kind, "reused": True,
                "request_sha256": request_sha, "result": dict(result),
            }
            return mapped
        if intent_path.exists():
            intent = _read(intent_path)
            _verify_signed(intent, "p3_b46_intent_checkpoint_drift")
            if (
                intent.get("request_sha256") != request_sha
                or intent.get("run_commitment_sha256") != self.run_commitment_sha256
            ):
                raise P3ContractError("p3_b46_intent_checkpoint_source_mismatch", call_id)
            raise P3ContractError("p3_b46_intent_without_complete_no_retry", call_id)
        intent = _signed({
            "schema": "uruha_p3_b46_provider_invocation_intent_v1",
            "run_commitment_sha256": self.run_commitment_sha256,
            "call_id_sha256": canonical_sha256(call_id),
            "kind": kind, "stage": stage, "request_sha256": request_sha,
            "provider_request_sha256": request_commitment["provider_request_sha256"],
            "transport_attempt_authorized": 1, "retry_count": 0, "fallback_count": 0,
        })
        write_new_json(intent_path, intent)
        if self.after_intent_hook is not None:
            self.after_intent_hook(call_id)
        try:
            response = transport(request)
            if not isinstance(response, Mapping):
                raise P3ContractError("p3_b46_provider_response_invalid", kind)
            result = _normalize_provider_response(kind, response)
        except Exception as exc:
            failure = _signed({
                "schema": "uruha_p3_b46_provider_failure_v1",
                "run_commitment_sha256": self.run_commitment_sha256,
                "call_id_sha256": canonical_sha256(call_id),
                "kind": kind, "stage": stage, "request_sha256": request_sha,
                "contract_code": (
                    exc.code if isinstance(exc, P3ContractError)
                    else "p3_b46_transport_failure_no_retry"
                ),
                "error_type": type(exc).__name__, "error_sha256": canonical_sha256(str(exc)),
                "transport_attempted": True, "response_received": not isinstance(exc, RuntimeError),
                "retry_authorized": False,
            })
            write_new_json(failure_path, failure)
            if isinstance(exc, P3ContractError):
                raise
            raise P3ContractError("p3_b46_transport_failure_no_retry", type(exc).__name__) from exc
        complete = _signed({
            "schema": "uruha_p3_b46_provider_complete_v1",
            "run_commitment_sha256": self.run_commitment_sha256,
            "call_id_sha256": canonical_sha256(call_id),
            "kind": kind, "stage": stage, "request_sha256": request_sha,
            "result": result,
        })
        write_new_json(complete_path, complete)
        self.last_call = {
            "call_id": call_id, "stage": stage, "kind": kind, "reused": False,
            "request_sha256": request_sha, "result": result,
        }
        return _reconstruct_provider_response(result)


class CheckpointedProductTransportGate(worker.ProductTransportGate):
    """Product budget gate whose two transports are journaled before I/O."""

    def __init__(self, *args: Any, journal: ProviderCallJournal, logical_step_id: str, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.journal = journal
        self.logical_step_id = logical_step_id
        self.last_provider_mapping: dict[str, Any] | None = None

    def _journaled(
        self, kind: str, stage: str, request: Mapping[str, Any],
        transport: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    ) -> Mapping[str, Any]:
        call_id = f"{self.logical_step_id}:{kind}:{stage}"
        mapped = self.journal.call_once(
            call_id=call_id, kind=kind, stage=stage, request=request, transport=transport
        )
        self.last_provider_mapping = dict(mapped)
        return mapped

    def intercept_openai(self, *, stage: str, call_kwargs: Mapping[str, Any], transport, contract_fake: bool = False):
        try:
            result = super().intercept_openai(
                stage=stage, call_kwargs=call_kwargs,
                transport=lambda request: self._journaled("openai", stage, request, transport),
                contract_fake=contract_fake,
            )
        except P3ContractError as exc:
            if exc.code == "transport_failure_no_retry" and isinstance(exc.__cause__, P3ContractError):
                raise exc.__cause__
            raise
        if self.journal.last_call and self.journal.last_call["reused"]:
            result["network_calls"] = result["real_model_calls"] = 0
            self.interceptions[-1]["network_calls"] = self.interceptions[-1]["real_model_calls"] = 0
            self.interceptions[-1]["checkpoint_reused"] = True
        else:
            self.interceptions[-1]["checkpoint_reused"] = False
        return result

    def intercept_native(self, *, stage: str, request_body: Mapping[str, Any], transport, contract_fake: bool = False):
        try:
            result = super().intercept_native(
                stage=stage, request_body=request_body,
                transport=lambda request: self._journaled("native", stage, request, transport),
                contract_fake=contract_fake,
            )
        except P3ContractError as exc:
            if exc.code == "transport_failure_no_retry" and isinstance(exc.__cause__, P3ContractError):
                raise exc.__cause__
            raise
        if self.journal.last_call and self.journal.last_call["reused"]:
            result["network_calls"] = result["real_model_calls"] = 0
            self.interceptions[-1]["network_calls"] = self.interceptions[-1]["real_model_calls"] = 0
            self.interceptions[-1]["checkpoint_reused"] = True
        else:
            self.interceptions[-1]["checkpoint_reused"] = False
        return result


def _openai_object(mapping: Mapping[str, Any]) -> SimpleNamespace:
    usage = mapping["usage"]
    return SimpleNamespace(
        model=mapping["model"],
        choices=[SimpleNamespace(message=SimpleNamespace(content=mapping["choices"][0]["message"]["content"]))],
        usage=SimpleNamespace(
            prompt_tokens=usage["prompt_tokens"], completion_tokens=usage["completion_tokens"]
        ),
    )


class _CheckpointedCompletions:
    def __init__(self, target: Any, gate: CheckpointedProductTransportGate) -> None:
        self.target, self.gate = target, gate

    def create(self, *args: Any, **kwargs: Any) -> Any:
        if args:
            raise P3ContractError("positional_product_generation_forbidden")

        def transport(request: Mapping[str, Any]) -> Mapping[str, Any]:
            return worker._openai_response_mapping(self.target.create(**dict(request)))

        stage = f"product_openai_{self.gate.budget.attempts + 1}"
        self.gate.intercept_openai(stage=stage, call_kwargs=kwargs, transport=transport)
        if self.gate.last_provider_mapping is None:
            raise P3ContractError("p3_b46_openai_mapping_missing")
        return _openai_object(self.gate.last_provider_mapping)


class _CheckpointedChat:
    def __init__(self, target: Any, gate: CheckpointedProductTransportGate) -> None:
        self.completions = _CheckpointedCompletions(target.completions, gate)


class _CheckpointedClient:
    def __init__(self, target: Any, gate: CheckpointedProductTransportGate) -> None:
        self._target = target
        self.chat = _CheckpointedChat(target.chat, gate)
        self.models = worker._OfflineModelsMetadata(gate.design["model"]["generation_model"])

    def __getattr__(self, name: str) -> Any:
        return getattr(self._target, name)


class _BufferedResponse:
    def __init__(self, payload: bytes) -> None:
        self._buffer = io.BytesIO(payload)

    def read(self, *args: Any, **kwargs: Any) -> bytes:
        return self._buffer.read(*args, **kwargs)

    def close(self) -> None:
        self._buffer.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()


def install_checkpointed_product_transport_gate(
    brain_module: Any, gate: CheckpointedProductTransportGate
) -> dict[str, Any]:
    expected_model = gate.design["model"]["generation_model"]
    if getattr(brain_module, "M31_SEMANTIC_VERIFIER_MODEL", None) != expected_model:
        raise P3ContractError("m31_import_model_not_locked")
    original_openai = brain_module.OpenAI
    original_urlopen = brain_module.urllib.request.urlopen
    native_url = str(brain_module.M31_SEMANTIC_VERIFIER_URL)

    def guarded_openai(*args: Any, **kwargs: Any) -> _CheckpointedClient:
        return _CheckpointedClient(original_openai(*args, **kwargs), gate)

    def guarded_urlopen(request: Any, *args: Any, **kwargs: Any) -> _BufferedResponse:
        if not isinstance(request, urllib.request.Request) or str(request.full_url) != native_url or args:
            raise P3ContractError("unaccounted_product_network_route")
        try:
            request_body = json.loads((request.data or b"").decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise P3ContractError("native_product_request_invalid") from exc

        def transport(body: Mapping[str, Any]) -> Mapping[str, Any]:
            normalized_request = urllib.request.Request(
                request.full_url,
                data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                headers=dict(request.headers), method=request.get_method(),
            )
            raw_response = original_urlopen(normalized_request, **kwargs)
            try:
                payload = raw_response.read()
            finally:
                close = getattr(raw_response, "close", None)
                if callable(close):
                    close()
            try:
                value = json.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise P3ContractError("invalid_transport_payload") from exc
            if not isinstance(value, Mapping):
                raise P3ContractError("invalid_transport_payload")
            return value

        stage = f"product_native_{gate.budget.attempts + 1}"
        gate.intercept_native(stage=stage, request_body=request_body, transport=transport)
        if gate.last_provider_mapping is None:
            raise P3ContractError("p3_b46_native_mapping_missing")
        payload = json.dumps(gate.last_provider_mapping, ensure_ascii=False).encode("utf-8")
        return _BufferedResponse(payload)

    guarded_openai._p3_product_gate = gate  # type: ignore[attr-defined]
    guarded_urlopen._p3_product_gate = gate  # type: ignore[attr-defined]
    brain_module.OpenAI = guarded_openai
    brain_module.urllib.request.urlopen = guarded_urlopen
    return {
        "openai_global_guarded": getattr(brain_module.OpenAI, "_p3_product_gate", None) is gate,
        "native_urlopen_global_guarded": getattr(brain_module.urllib.request.urlopen, "_p3_product_gate", None) is gate,
        "startup_models_list_network_bypassed": True,
        "unaccounted_network_routes_fail_closed": True,
        "real_transport_released": gate.allow_real_transport,
        "provider_binding_verified": gate.provider_binding_verified,
        "per_provider_call_checkpointed": True,
    }
