"""Raw-text-free per-item compute accounting for matched evaluations."""

from __future__ import annotations

import contextlib
import contextvars
import hashlib
import inspect
import json
import threading
import time
from copy import deepcopy


SCHEMA = "uruha_compute_ledger_v2"
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


def _flatten_strings(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        values = []
        for key in sorted(value):
            values.extend(_flatten_strings(value[key]))
        return values
    if isinstance(value, (list, tuple)):
        values = []
        for item in value:
            values.extend(_flatten_strings(item))
        return values
    return []


def _text_shape(value):
    texts = _flatten_strings(value)
    return {
        "count": len(texts),
        "char_count": sum(len(text) for text in texts),
        "sha256": _json_hash(texts),
    }


def _sequence_shape(value):
    if value is None:
        rows = []
    elif isinstance(value, (list, tuple)):
        rows = list(value)
    else:
        rows = [value]
    return {
        "count": len(rows),
        "sha256": _json_hash(rows),
    }


def _vector_shape(value):
    if value is None:
        rows = []
    elif isinstance(value, (list, tuple)):
        rows = list(value)
    else:
        rows = [value]
    dimensions = []
    for row in rows:
        try:
            dimensions.append(len(row))
        except TypeError:
            dimensions.append(None)
    return {
        "count": len(rows),
        "dimensions": dimensions,
        "sha256": _json_hash(rows),
    }


def _numeric_value(payload, name):
    value = (payload or {}).get(name)
    return int(value) if isinstance(value, (int, float)) else None


def _result_row_count(result):
    if not isinstance(result, dict):
        return None
    ids = result.get("ids")
    if not isinstance(ids, list):
        return 0
    if ids and all(isinstance(row, list) for row in ids):
        return sum(len(row) for row in ids)
    return len(ids)


def _resource_summary(calls):
    by_kind = {}
    by_backend = {}
    by_stage = {}
    by_operation = {}
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    generative_calls = []
    for call in calls:
        kind = str(call.get("resource_kind") or "generative_inference")
        backend = str(call.get("backend") or "unknown")
        stage = str(call.get("stage") or "unscoped")
        by_kind[kind] = by_kind.get(kind, 0) + 1
        by_backend[backend] = by_backend.get(backend, 0) + 1
        by_stage[stage] = by_stage.get(stage, 0) + 1
        operation = str((call.get("request") or {}).get("operation") or "")
        if operation:
            by_operation[operation] = by_operation.get(operation, 0) + 1
        if kind == "generative_inference":
            generative_calls.append(call)
        response = call.get("response") or {}
        prompt_tokens += int(response.get("prompt_tokens") or 0)
        completion_tokens += int(response.get("completion_tokens") or 0)
        total_tokens += int(response.get("total_tokens") or 0)
    token_complete = all(
        (call.get("response") or {}).get("prompt_tokens") is not None
        and (call.get("response") or {}).get("completion_tokens") is not None
        for call in generative_calls
    )
    return {
        "by_resource_kind": by_kind,
        "by_backend": by_backend,
        "by_stage": by_stage,
        "by_operation": by_operation,
        "scoped_call_count": sum(
            1 for call in calls if call.get("item_id") != "unscoped"
        ),
        "unscoped_call_count": sum(
            1 for call in calls if call.get("item_id") == "unscoped"
        ),
        "generative_call_count": len(generative_calls),
        "vector_store_operation_count": by_kind.get("vector_store_operation", 0),
        "embedding_expected_operation_count": sum(
            1
            for call in calls
            if bool((call.get("request") or {}).get("embedding_expected"))
        ),
        "failed_call_count": sum(1 for call in calls if call.get("error_type")),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "generative_token_accounting_complete": token_complete,
        "summed_operation_latency_seconds": round(
            sum(float(call.get("latency_seconds") or 0.0) for call in calls),
            6,
        ),
    }


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
            "resource_kind": "generative_inference",
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

    def record_native_ollama_chat(
        self,
        request_body,
        response_payload,
        latency_seconds,
        error=None,
    ):
        request_body = dict(request_body or {})
        response_payload = dict(response_payload or {})
        messages = list(request_body.get("messages") or [])
        message_shapes = []
        for message in messages:
            content = str((message or {}).get("content") or "")
            message_shapes.append(
                {
                    "role": str((message or {}).get("role") or ""),
                    "content_char_count": len(content),
                    "content_sha256": _sha256_text(content),
                }
            )
        response_text = str(
            ((response_payload.get("message") or {}).get("content") or "")
        )
        prompt_tokens = _numeric_value(response_payload, "prompt_eval_count")
        completion_tokens = _numeric_value(response_payload, "eval_count")
        record = {
            "call_index": 0,
            "item_id": _ITEM.get(),
            "condition_id": _CONDITION.get(),
            "stage": _STAGE.get(),
            "resource_kind": "generative_inference",
            "backend": "ollama_native_chat",
            "model": str(request_body.get("model") or ""),
            "request": {
                "message_count": len(message_shapes),
                "messages": message_shapes,
                "options": deepcopy(request_body.get("options") or {}),
                "stream": bool(request_body.get("stream")),
                "think": request_body.get("think"),
                "format_sha256": (
                    _json_hash(request_body.get("format"))
                    if request_body.get("format") is not None
                    else None
                ),
            },
            "response": {
                "content_char_count": len(response_text),
                "content_sha256": _sha256_text(response_text),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": (
                    prompt_tokens + completion_tokens
                    if prompt_tokens is not None and completion_tokens is not None
                    else None
                ),
                "done_reason": str(response_payload.get("done_reason") or ""),
                "provider_durations_ns": {
                    name: _numeric_value(response_payload, name)
                    for name in (
                        "total_duration",
                        "load_duration",
                        "prompt_eval_duration",
                        "eval_duration",
                    )
                },
            },
            "latency_seconds": round(max(0.0, float(latency_seconds)), 6),
            "error_type": type(error).__name__ if error is not None else "",
        }
        self._append(record)

    def record_vector_store_operation(
        self,
        *,
        collection_name,
        embedding_function,
        operation,
        arguments,
        result,
        latency_seconds,
        error=None,
    ):
        arguments = dict(arguments or {})
        query_texts = arguments.get("query_texts")
        documents = arguments.get("documents")
        provided_embeddings = arguments.get("embeddings")
        provided_query_embeddings = arguments.get("query_embeddings")
        text_supplied = bool(_flatten_strings(query_texts) or _flatten_strings(documents))
        caller_vectors_supplied = provided_embeddings is not None or provided_query_embeddings is not None
        embedding_expected = text_supplied and not caller_vectors_supplied
        record = {
            "call_index": 0,
            "item_id": _ITEM.get(),
            "condition_id": _CONDITION.get(),
            "stage": (
                _STAGE.get()
                if _STAGE.get() != "unscoped"
                else f"memory_{collection_name}_{operation}"
            ),
            "resource_kind": "vector_store_operation",
            "backend": "chromadb_local",
            "model": str(embedding_function or "unavailable"),
            "request": {
                "operation": str(operation),
                "collection_name": str(collection_name),
                "query_texts": _text_shape(query_texts),
                "documents": _text_shape(documents),
                "ids": _sequence_shape(arguments.get("ids")),
                "embeddings": _vector_shape(provided_embeddings),
                "query_embeddings": _vector_shape(provided_query_embeddings),
                "metadata_count": len(arguments.get("metadatas") or []),
                "metadata_sha256": _json_hash(arguments.get("metadatas") or []),
                "filter_sha256": _json_hash(
                    {
                        "where": arguments.get("where"),
                        "where_document": arguments.get("where_document"),
                    }
                ),
                "n_results": arguments.get("n_results"),
                "include_sha256": _json_hash(arguments.get("include")),
                "caller_vectors_supplied": caller_vectors_supplied,
                "embedding_expected": embedding_expected,
                "token_count_available": False,
            },
            "response": {
                "result_row_count": _result_row_count(result),
                "prompt_tokens": None,
                "completion_tokens": None,
                "total_tokens": None,
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
            "resource_kind": "generative_inference",
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
            "summary": _resource_summary(calls),
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


def _bound_arguments(method, args, kwargs):
    try:
        return dict(inspect.signature(method).bind_partial(*args, **kwargs).arguments)
    except (TypeError, ValueError):
        return dict(kwargs)


def _embedding_function_name(collection):
    embedding_function = getattr(collection, "_embedding_function", None)
    if embedding_function is None:
        return "unavailable"
    name = getattr(embedding_function, "name", None)
    if callable(name):
        try:
            value = name()
            if value:
                return str(value)
        except Exception:
            pass
    cls = type(embedding_function)
    return f"{cls.__module__}.{cls.__qualname__}"


class InstrumentedChromaCollection:
    _RECORDED_OPERATIONS = {"add", "delete", "get", "peek", "query", "update", "upsert"}

    def __init__(self, target, ledger, collection_name=None):
        self._target = target
        self._ledger = ledger
        self._collection_name = str(
            collection_name or getattr(target, "name", None) or "unknown"
        )
        self._embedding_function_name = _embedding_function_name(target)

    def __getattr__(self, name):
        target = getattr(self._target, name)
        if name not in self._RECORDED_OPERATIONS or not callable(target):
            return target

        def recorded(*args, **kwargs):
            started = time.perf_counter()
            result = None
            error = None
            arguments = _bound_arguments(target, args, kwargs)
            try:
                result = target(*args, **kwargs)
                return result
            except Exception as exc:
                error = exc
                raise
            finally:
                self._ledger.record_vector_store_operation(
                    collection_name=self._collection_name,
                    embedding_function=self._embedding_function_name,
                    operation=name,
                    arguments=arguments,
                    result=result,
                    latency_seconds=time.perf_counter() - started,
                    error=error,
                )

        return recorded


def instrument_openai_client(client, ledger):
    if ledger is None:
        return client
    if not isinstance(ledger, ComputeLedger):
        raise TypeError("compute_ledger must be a ComputeLedger")
    return InstrumentedOpenAIClient(client, ledger)


def instrument_chroma_collection(collection, ledger, collection_name=None):
    if ledger is None:
        return collection
    if not isinstance(ledger, ComputeLedger):
        raise TypeError("compute_ledger must be a ComputeLedger")
    return InstrumentedChromaCollection(collection, ledger, collection_name)


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
