"""Raw-text-free per-item compute accounting for matched evaluations."""

from __future__ import annotations

import contextlib
import contextvars
import hashlib
import json
import threading
import time
from copy import deepcopy


SCHEMA = "uruha_compute_ledger_v1"
_STAGE = contextvars.ContextVar("uruha_compute_stage", default="unscoped")
_ITEM = contextvars.ContextVar("uruha_compute_item", default="unscoped")
_CONDITION = contextvars.ContextVar("uruha_compute_condition", default="unscoped")


def _sha256_text(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _json_hash(value):
    return _sha256_text(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str))


def _usage_value(usage, name):
    if usage is None:
        return None
    if isinstance(usage, dict):
        value = usage.get(name)
    else:
        value = getattr(usage, name, None)
    return int(value) if isinstance(value, (int, float)) else None


def _response_texts(response):
    texts = []
    for choice in getattr(response, "choices", None) or []:
        message = getattr(choice, "message", None)
        content = getattr(message, "content", None)
        if content is not None:
            texts.append(str(content))
    return texts


def request_shape(kwargs):
    messages = kwargs.get("messages") or []
    message_shapes = []
    for message in messages:
        content = str((message or {}).get("content") or "")
        message_shapes.append(
            {
                "role": str((message or {}).get("role") or ""),
                "content_char_count": len(content),
                "content_sha256": _sha256_text(content),
                "tool_call_count": len((message or {}).get("tool_calls") or []),
            }
        )
    options = {
        key: kwargs.get(key)
        for key in (
            "temperature",
            "top_p",
            "max_tokens",
            "max_completion_tokens",
            "seed",
            "frequency_penalty",
            "presence_penalty",
        )
        if key in kwargs
    }
    return {
        "model": str(kwargs.get("model") or ""),
        "message_count": len(message_shapes),
        "messages": message_shapes,
        "options": options,
        "response_format_sha256": _json_hash(kwargs.get("response_format")) if kwargs.get("response_format") is not None else None,
        "tool_schema_count": len(kwargs.get("tools") or []),
        "tool_schema_sha256": _json_hash(kwargs.get("tools")) if kwargs.get("tools") is not None else None,
        "tool_choice_sha256": _json_hash(kwargs.get("tool_choice")) if kwargs.get("tool_choice") is not None else None,
    }


class ComputeLedger:
    def __init__(self):
        self._calls = []
        self._lock = threading.Lock()

    @contextlib.contextmanager
    def stage(self, name):
        token = _STAGE.set(str(name or "unscoped"))
        try:
            yield self
        finally:
            _STAGE.reset(token)

    @contextlib.contextmanager
    def item_scope(self, item_id, condition_id):
        item_token = _ITEM.set(str(item_id or "unscoped"))
        condition_token = _CONDITION.set(str(condition_id or "unscoped"))
        try:
            yield self
        finally:
            _CONDITION.reset(condition_token)
            _ITEM.reset(item_token)

    def record_chat_completion(self, kwargs, response, latency_seconds, error=None):
        shape = request_shape(kwargs)
        usage = getattr(response, "usage", None) if response is not None else None
        texts = _response_texts(response) if response is not None else []
        record = {
            "call_index": 0,
            "item_id": _ITEM.get(),
            "condition_id": _CONDITION.get(),
            "stage": _STAGE.get(),
            "backend": "openai_compatible_local",
            "model": shape["model"],
            "request": shape,
            "response": {
                "choice_count": len(texts),
                "content_char_count": sum(len(text) for text in texts),
                "content_sha256": _json_hash(texts),
                "prompt_tokens": _usage_value(usage, "prompt_tokens"),
                "completion_tokens": _usage_value(usage, "completion_tokens"),
                "total_tokens": _usage_value(usage, "total_tokens"),
            },
            "latency_seconds": round(max(0.0, float(latency_seconds)), 6),
            "error_type": type(error).__name__ if error is not None else "",
        }
        self._append(record)

    def record_local_generation(
        self,
        model,
        prompt_text,
        prompt_tokens,
        completion_text,
        completion_tokens,
        generation_options,
        latency_seconds,
        error=None,
        active_prompt_tokens=None,
        masked_prompt_tokens=None,
    ):
        allocated_prompt_tokens = int(prompt_tokens) if prompt_tokens is not None else None
        active_prompt_tokens = (
            int(active_prompt_tokens)
            if active_prompt_tokens is not None
            else allocated_prompt_tokens
        )
        masked_prompt_tokens = (
            int(masked_prompt_tokens)
            if masked_prompt_tokens is not None
            else (
                allocated_prompt_tokens - active_prompt_tokens
                if allocated_prompt_tokens is not None and active_prompt_tokens is not None
                else None
            )
        )
        record = {
            "call_index": 0,
            "item_id": _ITEM.get(),
            "condition_id": _CONDITION.get(),
            "stage": _STAGE.get(),
            "backend": "transformers_local",
            "model": str(model or ""),
            "request": {
                "prompt_char_count": len(str(prompt_text or "")),
                "prompt_sha256": _sha256_text(prompt_text),
                "options": deepcopy(generation_options or {}),
                "allocation": {
                    "active_prompt_tokens": active_prompt_tokens,
                    "allocated_prompt_tokens": allocated_prompt_tokens,
                    "masked_prompt_tokens": masked_prompt_tokens,
                },
            },
            "response": {
                "content_char_count": len(str(completion_text or "")),
                "content_sha256": _sha256_text(completion_text),
                "prompt_tokens": allocated_prompt_tokens,
                "active_prompt_tokens": active_prompt_tokens,
                "masked_prompt_tokens": masked_prompt_tokens,
                "completion_tokens": int(completion_tokens) if completion_tokens is not None else None,
                "total_tokens": (
                    int(prompt_tokens) + int(completion_tokens)
                    if prompt_tokens is not None and completion_tokens is not None
                    else None
                ),
            },
            "latency_seconds": round(max(0.0, float(latency_seconds)), 6),
            "error_type": type(error).__name__ if error is not None else "",
        }
        self._append(record)

    def _append(self, record):
        with self._lock:
            record["call_index"] = len(self._calls) + 1
            self._calls.append(record)

    def snapshot(self):
        with self._lock:
            calls = deepcopy(self._calls)
        return {
            "schema": SCHEMA,
            "call_count": len(calls),
            "contains_raw_prompt_or_reply": False,
            "calls": calls,
        }

    def reset(self):
        with self._lock:
            self._calls = []


class _CompletionProxy:
    def __init__(self, target, ledger):
        self._target = target
        self._ledger = ledger

    def create(self, *args, **kwargs):
        started = time.perf_counter()
        response = None
        error = None
        try:
            response = self._target.create(*args, **kwargs)
            return response
        except Exception as exc:
            error = exc
            raise
        finally:
            self._ledger.record_chat_completion(
                kwargs,
                response,
                time.perf_counter() - started,
                error=error,
            )


class _ChatProxy:
    def __init__(self, target, ledger):
        self._target = target
        self.completions = _CompletionProxy(target.completions, ledger)

    def __getattr__(self, name):
        return getattr(self._target, name)


class InstrumentedOpenAIClient:
    def __init__(self, target, ledger):
        self._target = target
        self.chat = _ChatProxy(target.chat, ledger)

    def __getattr__(self, name):
        return getattr(self._target, name)


def instrument_openai_client(client, ledger):
    if ledger is None:
        return client
    if not isinstance(ledger, ComputeLedger):
        raise TypeError("compute_ledger must be a ComputeLedger")
    return InstrumentedOpenAIClient(client, ledger)


def ledger_stage(ledger, stage_name):
    return ledger.stage(stage_name) if ledger is not None else contextlib.nullcontext()


def compare_compute_envelopes(left_snapshot, right_snapshot):
    left_calls = list((left_snapshot or {}).get("calls") or [])
    right_calls = list((right_snapshot or {}).get("calls") or [])

    def signature(call):
        request = call.get("request") or {}
        return {
            "stage": call.get("stage"),
            "backend": call.get("backend"),
            "model": call.get("model"),
            "options": request.get("options") or {},
            "message_count": request.get("message_count"),
            "message_roles": [
                message.get("role")
                for message in (request.get("messages") or [])
            ],
            "tool_schema_count": request.get("tool_schema_count"),
            "tool_schema_sha256": request.get("tool_schema_sha256"),
            "tool_choice_sha256": request.get("tool_choice_sha256"),
            "response_format_sha256": request.get("response_format_sha256"),
        }

    left_signatures = [signature(call) for call in left_calls]
    right_signatures = [signature(call) for call in right_calls]
    left_prompt_tokens = [
        (call.get("response") or {}).get("prompt_tokens")
        for call in left_calls
    ]
    right_prompt_tokens = [
        (call.get("response") or {}).get("prompt_tokens")
        for call in right_calls
    ]
    prompt_tokens_available = all(
        value is not None
        for value in left_prompt_tokens + right_prompt_tokens
    )
    prompt_token_schedule_equal = (
        prompt_tokens_available and left_prompt_tokens == right_prompt_tokens
    )
    left_active_prompt_tokens = [
        (call.get("response") or {}).get("active_prompt_tokens")
        for call in left_calls
    ]
    right_active_prompt_tokens = [
        (call.get("response") or {}).get("active_prompt_tokens")
        for call in right_calls
    ]
    active_prompt_tokens_available = all(
        value is not None
        for value in left_active_prompt_tokens + right_active_prompt_tokens
    )
    active_prompt_token_schedule_equal = (
        active_prompt_tokens_available
        and left_active_prompt_tokens == right_active_prompt_tokens
    )
    schedule_equal = left_signatures == right_signatures
    call_count_equal = len(left_calls) == len(right_calls)
    return {
        "call_count_equal": call_count_equal,
        "model_decoding_and_tool_schedule_equal": schedule_equal,
        "prompt_tokens_available": prompt_tokens_available,
        "prompt_token_schedule_equal": prompt_token_schedule_equal,
        "left_call_count": len(left_calls),
        "right_call_count": len(right_calls),
        "left_prompt_tokens": left_prompt_tokens,
        "right_prompt_tokens": right_prompt_tokens,
        "active_prompt_tokens_available": active_prompt_tokens_available,
        "active_prompt_token_schedule_equal": active_prompt_token_schedule_equal,
        "left_active_prompt_tokens": left_active_prompt_tokens,
        "right_active_prompt_tokens": right_active_prompt_tokens,
        "parity_pass": call_count_equal and schedule_equal and prompt_token_schedule_equal,
    }
