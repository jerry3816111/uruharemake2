#!/usr/bin/env python3
"""Bounded read-only Function Calling seam for the P4 local product.

The module is intentionally independent from the heavyweight Web runtime.  It
first gates a current, explicit status request; only then may a provider choose
the single allowlisted tool.  Validation happens before the supplied executor
is invoked and all invalid/provider/executor paths fail closed.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import time
from typing import Any, Callable
import unicodedata
from urllib import request


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs" / "p4_c_read_only_function_calling_contract_v1.json"
TOOL_NAME = "get_runtime_status"
TRACE_LABELS = (
    "function_request_p4_c",
    "function_model_decision_p4_c",
    "function_validated_call_p4_c",
    "function_tool_result_p4_c",
    "function_surface_p4_c",
)
ALLOWED_STATUS_FIELDS = (
    "schema",
    "brain_loaded",
    "turn_count",
    "memory_isolation",
    "tool_capability",
)
MEMORY_ISOLATION_VALUES = {"isolated", "production", "unknown"}
TOOL_CAPABILITY_VALUES = {"get_runtime_status_only"}


class P4CContractError(ValueError):
    pass


class P4CProviderError(RuntimeError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def load_contract(path: str | Path = CONTRACT_PATH) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def tool_schema(contract: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    spec = deepcopy((contract or load_contract())["tool"])
    return [
        {
            "type": "function",
            "function": {
                "name": spec["name"],
                "description": spec["description"],
                "parameters": spec["parameters"],
            },
        }
    ]


_INJECTION_OR_OTHER_TOOL = re.compile(
    r"(?:忽略|無視|无视).{0,24}(?:規則|规则|指令|前文|system|developer)|"
    r"\bignore\s+(?:all\s+)?(?:previous|prior|system|developer)\b|"
    r"(?:delete_file|write_file|shell|exec(?:ute)?|curl|rm\s+-)|"
    r"(?:呼叫|调用|使って|実行して|call).{0,24}(?:刪除|删除|寫入|写入|shell|exec|delete|write)",
    re.I,
)
_META_OR_QUOTED = re.compile(
    r"(?:翻譯|翻译|訳して|翻訳|引用|例文|台本|脚本|假設題|假设题)|"
    r"\b(?:translate|quote|example|script)\b",
    re.I,
)
_THIRD_PERSON = re.compile(
    r"(?:他|她|朋友|老師|老师|彼|彼女|友達).{0,30}(?:系統|系统|ランタイム|runtime).{0,16}(?:狀態|状态|状態|status)|"
    r"\b(?:he|she|they|my\s+friend).{0,30}(?:runtime|system).{0,16}(?:status|state)\b",
    re.I,
)
_HYPOTHETICAL = re.compile(
    r"(?:如果|假如|假設|假设|要是|もし|仮に).{0,60}(?:系統|系统|ランタイム|runtime).{0,24}(?:狀態|状态|状態|status)|"
    r"\bif\s+(?:i|we|someone).{0,40}(?:ask|asked|request).{0,30}(?:runtime|system).{0,16}(?:status|state)\b|"
    r"\bwhat\s+would\s+(?:you|the\s+system).{0,32}(?:status|state|tool)\b",
    re.I,
)
_NEGATED = re.compile(
    r"(?:不要|不用|別|别|不必).{0,20}(?:查看|檢查|检查|顯示|显示|告訴|告诉|系統狀態|系统状态)|"
    r"(?:確認|チェック|表示|教え)(?:しないで|なくていい|ないで)|"
    r"\b(?:do\s+not|don't|no\s+need\s+to)\s+(?:check|show|report|tell).{0,24}(?:status|state)\b",
    re.I,
)

_EXPLICIT_PATTERNS = {
    "zh": (
        re.compile(
            r"(?:請|请|可以|能不能|幫我|帮我|麻煩|麻烦|查看|檢查|检查|顯示|显示|告訴我|告诉我)"
            r".{0,24}(?:UruhaBrain|系統|系统|運行|运行|腦|脑).{0,16}(?:狀態|状态|是否啟動|是否启动|有沒有啟動|有没有启动|是否運行|是否运行)"
        ),
        re.compile(
            r"(?:UruhaBrain|系統|系统|運行|运行|腦|脑).{0,16}(?:狀態|状态|是否啟動|是否启动|有沒有啟動|有没有启动|是否運行|是否运行)"
            r".{0,16}(?:查看|檢查|检查|顯示|显示|告訴我|告诉我|給我看|给我看)"
        ),
    ),
    "en": (
        re.compile(
            r"\b(?:please\s+)?(?:check|show|report|tell\s+me|give\s+me)\b.{0,28}"
            r"\b(?:UruhaBrain|runtime|system|brain)\b.{0,18}\b(?:status|state|loaded|running|health)\b",
            re.I,
        ),
        re.compile(
            r"\b(?:what(?:'s|\s+is)|show)\b.{0,18}\b(?:the\s+)?(?:UruhaBrain|runtime|system|brain)\b"
            r".{0,18}\b(?:status|state|health)\b",
            re.I,
        ),
    ),
    "ja": (
        re.compile(
            r"(?:今|現在|いま)?\s*(?:の)?(?:UruhaBrain|システム|ランタイム|脳).{0,16}"
            r"(?:状態|起動状態|動作状態).{0,16}(?:確認して|チェックして|教えて|見せて|表示して)"
        ),
        re.compile(
            r"(?:確認して|チェックして|教えて|見せて|表示して).{0,16}"
            r"(?:UruhaBrain|システム|ランタイム|脳).{0,16}(?:状態|起動状態|動作状態)"
        ),
    ),
}


def classify_runtime_status_request(user_input: str) -> dict[str, Any]:
    text = unicodedata.normalize("NFKC", str(user_input or "")).strip()
    base = {
        "schema": "uruha_p4_c_runtime_status_request_gate_v1",
        "selected": False,
        "status": "not_selected",
        "reason": "no_explicit_current_status_request",
        "input_sha256": sha256_text(text),
        "raw_dialogue_persisted": False,
        "model_call_authorized": False,
    }
    if not text:
        return {**base, "reason": "empty_input"}
    for pattern, reason in (
        (_INJECTION_OR_OTHER_TOOL, "prompt_injection_or_other_tool_request"),
        (_META_OR_QUOTED, "quoted_or_translation_request"),
        (_THIRD_PERSON, "third_person_or_example_request"),
        (_HYPOTHETICAL, "hypothetical_or_conditional"),
        (_NEGATED, "negated_request"),
    ):
        if pattern.search(text):
            return {**base, "reason": reason}
    for language, patterns in _EXPLICIT_PATTERNS.items():
        if any(pattern.search(text) for pattern in patterns):
            return {
                **base,
                "selected": True,
                "status": "explicit_current_runtime_status_request",
                "reason": "explicit_current_status_request",
                "language": language,
                "model_call_authorized": True,
            }
    return base


def validate_contract(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors: list[str] = []
    if contract.get("schema") != "uruha_p4_c_read_only_function_calling_contract_v1":
        errors.append("schema")
    if contract.get("status") != "prospective_offline_contract_before_any_p4_c_model_call":
        errors.append("status")
    if contract.get("single_changed_variable") != "one get_runtime_status function-call path for explicit current status requests":
        errors.append("single_changed_variable")
    gate = contract.get("request_gate") or {}
    if gate.get("supported_input_languages") != ["zh", "en", "ja"]:
        errors.append("request_gate:languages")
    if gate.get("requires_explicit_current_status_request") is not True:
        errors.append("request_gate:explicit")
    if gate.get("blocked_requests_fall_through_to_existing_chat") is not True:
        errors.append("request_gate:fallthrough")
    expected_blocked = {
        "ordinary_conversation",
        "negated_request",
        "hypothetical_or_conditional",
        "quoted_or_translation_request",
        "third_person_or_example_request",
        "prompt_injection_or_other_tool_request",
    }
    if set(gate.get("blocked_contexts") or []) != expected_blocked:
        errors.append("request_gate:blocked_contexts")
    tool = contract.get("tool") or {}
    if tool.get("name") != TOOL_NAME:
        errors.append("tool:name")
    if tool.get("parameters") != {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    }:
        errors.append("tool:parameters")
    if tool.get("maximum_calls_per_turn") != 1 or tool.get("side_effects") != "none":
        errors.append("tool:cardinality_or_side_effect")
    if tool.get("allowed_result_fields") != list(ALLOWED_STATUS_FIELDS):
        errors.append("tool:result_fields")
    if tool.get("maximum_serialized_result_bytes") != 640:
        errors.append("tool:result_budget")
    provider = contract.get("provider") or {}
    expected_provider = {
        "kind": "local_ollama_chat_tools",
        "endpoint": "http://127.0.0.1:11434/api/chat",
        "model": "qwen3.5:9b",
        "model_blob_sha256": "dec52a44569a2a25341c4e4d3fee25846eed4f6f0b936278e3a3c900bb99d37c",
        "timeout_seconds": 90,
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0,
            "seed": 260920,
            "top_p": 1,
            "num_ctx": 4096,
            "num_predict": 96,
        },
        "retry_or_fallback_allowed": False,
        "raw_prompt_or_response_persistence_allowed": False,
    }
    if provider != expected_provider:
        errors.append("provider")
    if (contract.get("trace") or {}).get("ordered_labels") != list(TRACE_LABELS):
        errors.append("trace:labels")
    if (contract.get("offline_acceptance") or {}).get("model_call_count") != 0:
        errors.append("offline:model_calls")
    denied = contract.get("denied_actions") or {}
    if not denied or any(value is not True for value in denied.values()):
        errors.append("denied_actions")
    if contract.get("release_order") != [
        "contract",
        "offline_fake_provider_tests",
        "implementation_freeze_commit",
        "one_real_positive_model_call",
        "real_negative_request_guards",
        "product_integration",
        "isolated_safari_acceptance",
    ]:
        errors.append("release_order")
    return {"valid": not errors, "errors": errors}


def runtime_status_payload(
    *, brain_loaded: bool, turn_count: int, memory_isolation: str
) -> dict[str, Any]:
    if not isinstance(brain_loaded, bool):
        raise P4CContractError("status:brain_loaded")
    if isinstance(turn_count, bool) or not isinstance(turn_count, int) or not 0 <= turn_count <= 1_000_000:
        raise P4CContractError("status:turn_count")
    if memory_isolation not in MEMORY_ISOLATION_VALUES:
        raise P4CContractError("status:memory_isolation")
    return {
        "schema": "uruha_p4_c_runtime_status_result_v1",
        "brain_loaded": brain_loaded,
        "turn_count": turn_count,
        "memory_isolation": memory_isolation,
        "tool_capability": "get_runtime_status_only",
    }


def validate_status_payload(
    payload: Any, contract: dict[str, Any] | None = None
) -> dict[str, Any]:
    contract = contract or load_contract()
    if not isinstance(payload, dict):
        raise P4CContractError("tool_result:not_object")
    if set(payload) != set(ALLOWED_STATUS_FIELDS):
        raise P4CContractError("tool_result:field_set")
    if payload.get("schema") != "uruha_p4_c_runtime_status_result_v1":
        raise P4CContractError("tool_result:schema")
    normalized = runtime_status_payload(
        brain_loaded=payload.get("brain_loaded"),
        turn_count=payload.get("turn_count"),
        memory_isolation=payload.get("memory_isolation"),
    )
    if payload.get("tool_capability") not in TOOL_CAPABILITY_VALUES:
        raise P4CContractError("tool_result:capability")
    serialized = canonical_json(normalized).encode("utf-8")
    if len(serialized) > int(contract["tool"]["maximum_serialized_result_bytes"]):
        raise P4CContractError("tool_result:byte_budget")
    return normalized


def _canonical_tool_calls(
    response: Any, *, expected_model: str
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not isinstance(response, dict):
        raise P4CContractError("provider_response:not_object")
    message = response.get("message")
    if not isinstance(message, dict):
        raise P4CContractError("provider_response:message")
    calls = message.get("tool_calls")
    if calls is None:
        calls = []
    if not isinstance(calls, list):
        raise P4CContractError("provider_response:tool_calls")
    metadata = {
        "model_identity_match": response.get("model") == expected_model,
        "prompt_tokens": int(response.get("prompt_eval_count") or 0),
        "completion_tokens": int(response.get("eval_count") or 0),
        "provider_done": response.get("done") is True,
        "raw_provider_response_persisted": False,
    }
    return calls, metadata


def validate_single_tool_call(calls: Any) -> dict[str, Any]:
    if not isinstance(calls, list):
        raise P4CContractError("tool_call:list_required")
    if len(calls) == 0:
        raise P4CContractError("tool_call:missing")
    if len(calls) != 1:
        raise P4CContractError("tool_call:cardinality")
    call = calls[0]
    if not isinstance(call, dict):
        raise P4CContractError("tool_call:not_object")
    function = call.get("function")
    if not isinstance(function, dict):
        raise P4CContractError("tool_call:function")
    if function.get("name") != TOOL_NAME:
        raise P4CContractError("tool_call:name")
    arguments = function.get("arguments", {})
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except (TypeError, json.JSONDecodeError) as exc:
            raise P4CContractError("tool_call:malformed_arguments") from exc
    if not isinstance(arguments, dict) or arguments:
        raise P4CContractError("tool_call:arguments_must_be_empty")
    return {"name": TOOL_NAME, "arguments": {}}


def _trace_node(stage: str, label: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "stage": stage,
        "label": label,
        "payload": deepcopy(payload),
        "salience": 1.0,
    }


def _success_surface(status: dict[str, Any]) -> str:
    brain = "脳は起動済み" if status["brain_loaded"] else "脳はまだ待機中"
    isolation = {
        "isolated": "記憶は隔離環境",
        "production": "記憶は通常環境",
        "unknown": "記憶の隔離状態は未確認",
    }[status["memory_isolation"]]
    return (
        f"うん、{brain}。記録は{status['turn_count']}ターン、{isolation}。"
        "今使えるのは読み取り専用の状態確認だけ。"
    )


def _failure_surface() -> str:
    return "今の状態確認は取れなかった。動かしたとは言わないでおく。"


def _provider_messages() -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "The user has already passed a deterministic explicit-current-status gate. "
                "Call exactly get_runtime_status once with an empty JSON object. "
                "Do not answer in text and do not call any other function."
            ),
        },
        {
            "role": "user",
            "content": "Read the current local runtime status now.",
        },
    ]


def run_function_call_turn(
    user_input: str,
    *,
    provider: Any,
    status_reader: Callable[[], dict[str, Any]],
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    contract_validation = validate_contract(contract)
    if not contract_validation["valid"]:
        raise P4CContractError("contract:" + ";".join(contract_validation["errors"]))
    gate = classify_runtime_status_request(user_input)
    if not gate["selected"]:
        return {
            "schema": "uruha_p4_c_function_turn_v1",
            "handled": False,
            "status": "fallthrough_existing_chat",
            "gate": gate,
            "model_call_count": 0,
            "tool_execution_count": 0,
            "trace": [],
            "raw_dialogue_persisted": False,
        }

    trace = [
        _trace_node(
            "observe",
            TRACE_LABELS[0],
            {
                "schema": gate["schema"],
                "status": gate["status"],
                "language": gate["language"],
                "input_sha256": gate["input_sha256"],
                "raw_dialogue_persisted": False,
            },
        )
    ]
    provider_started = time.perf_counter()
    try:
        response = provider.invoke(
            model=contract["provider"]["model"],
            messages=_provider_messages(),
            tools=tool_schema(contract),
            options=deepcopy(contract["provider"]["options"]),
            think=contract["provider"]["think"],
            timeout_seconds=contract["provider"]["timeout_seconds"],
        )
        calls, provider_metadata = _canonical_tool_calls(
            response, expected_model=contract["provider"]["model"]
        )
        if not provider_metadata["model_identity_match"]:
            raise P4CContractError("provider_response:model_identity")
    except Exception as exc:
        category = (
            str(exc)
            if isinstance(exc, P4CContractError)
            else "provider_exception"
        )
        trace.append(
            _trace_node(
                "infer",
                TRACE_LABELS[1],
                {
                    "status": "failed_closed",
                    "failure_category": category[:96],
                    "tool_call_count": 0,
                    "latency_seconds": round(time.perf_counter() - provider_started, 4),
                    "raw_provider_response_persisted": False,
                },
            )
        )
        reply = _failure_surface()
        trace.append(
            _trace_node(
                "surface",
                TRACE_LABELS[4],
                {
                    "status": "failure_surface",
                    "visible_reply_sha256": sha256_text(reply),
                    "language": "ja",
                    "claimed_status_read": False,
                },
            )
        )
        return {
            "schema": "uruha_p4_c_function_turn_v1",
            "handled": True,
            "status": "failed_closed",
            "failure_category": category[:96],
            "reply": reply,
            "gate": gate,
            "model_call_count": 1,
            "tool_execution_count": 0,
            "trace": trace,
            "raw_dialogue_persisted": False,
        }

    decision_payload = {
        "status": "model_decision_received",
        "tool_call_count": len(calls),
        "latency_seconds": round(time.perf_counter() - provider_started, 4),
        **provider_metadata,
    }
    try:
        validated_call = validate_single_tool_call(calls)
    except P4CContractError as exc:
        decision_payload.update(
            status="failed_closed", failure_category=str(exc)[:96]
        )
        trace.append(_trace_node("infer", TRACE_LABELS[1], decision_payload))
        reply = _failure_surface()
        trace.append(
            _trace_node(
                "surface",
                TRACE_LABELS[4],
                {
                    "status": "failure_surface",
                    "visible_reply_sha256": sha256_text(reply),
                    "language": "ja",
                    "claimed_status_read": False,
                },
            )
        )
        return {
            "schema": "uruha_p4_c_function_turn_v1",
            "handled": True,
            "status": "failed_closed",
            "failure_category": str(exc)[:96],
            "reply": reply,
            "gate": gate,
            "provider_metadata": provider_metadata,
            "model_call_count": 1,
            "tool_execution_count": 0,
            "trace": trace,
            "raw_dialogue_persisted": False,
        }

    decision_payload["status"] = "single_allowlisted_call"
    trace.append(_trace_node("infer", TRACE_LABELS[1], decision_payload))
    trace.append(
        _trace_node(
            "select",
            TRACE_LABELS[2],
            {
                "status": "validated",
                "name": validated_call["name"],
                "arguments": {},
                "read_only": True,
                "side_effects": "none",
            },
        )
    )
    try:
        status = validate_status_payload(status_reader(), contract)
    except Exception as exc:
        category = (
            str(exc)
            if isinstance(exc, P4CContractError)
            else "executor_exception"
        )
        reply = _failure_surface()
        trace.append(
            _trace_node(
                "act",
                TRACE_LABELS[3],
                {
                    "status": "failed_closed",
                    "failure_category": category[:96],
                    "result_exposed": False,
                    "side_effect_count": 0,
                },
            )
        )
        trace.append(
            _trace_node(
                "surface",
                TRACE_LABELS[4],
                {
                    "status": "failure_surface",
                    "visible_reply_sha256": sha256_text(reply),
                    "language": "ja",
                    "claimed_status_read": False,
                },
            )
        )
        return {
            "schema": "uruha_p4_c_function_turn_v1",
            "handled": True,
            "status": "failed_closed",
            "failure_category": category[:96],
            "reply": reply,
            "gate": gate,
            "provider_metadata": provider_metadata,
            "model_call_count": 1,
            "tool_execution_count": 1,
            "trace": trace,
            "raw_dialogue_persisted": False,
        }

    trace.append(
        _trace_node(
            "act",
            TRACE_LABELS[3],
            {
                **status,
                "status": "read_complete",
                "result_bytes": len(canonical_json(status).encode("utf-8")),
                "side_effect_count": 0,
            },
        )
    )
    reply = _success_surface(status)
    trace.append(
        _trace_node(
            "surface",
            TRACE_LABELS[4],
            {
                "status": "natural_japanese_status_surface",
                "visible_reply_sha256": sha256_text(reply),
                "language": "ja",
                "claimed_status_read": True,
            },
        )
    )
    return {
        "schema": "uruha_p4_c_function_turn_v1",
        "handled": True,
        "status": "tool_call_complete",
        "reply": reply,
        "gate": gate,
        "provider_metadata": provider_metadata,
        "tool_result": status,
        "model_call_count": 1,
        "tool_execution_count": 1,
        "trace": trace,
        "raw_dialogue_persisted": False,
    }


class LocalOllamaToolsProvider:
    """Single-attempt local Ollama adapter.  No retry or fallback is present."""

    def __init__(self, endpoint: str | None = None):
        self.endpoint = endpoint or load_contract()["provider"]["endpoint"]
        if self.endpoint != "http://127.0.0.1:11434/api/chat":
            raise P4CProviderError("endpoint_not_allowlisted")

    def invoke(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        options: dict[str, Any],
        think: bool,
        timeout_seconds: int,
    ) -> dict[str, Any]:
        body = {
            "model": model,
            "messages": messages,
            "tools": tools,
            "stream": False,
            "think": bool(think),
            "options": options,
        }
        transport = request.Request(
            self.endpoint,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(transport, timeout=timeout_seconds) as response:
                parsed = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise P4CProviderError("local_provider_failure") from exc
        if not isinstance(parsed, dict) or parsed.get("model") != model:
            raise P4CProviderError("provider_identity_or_shape")
        return parsed
