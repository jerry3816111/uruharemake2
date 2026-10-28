"""Injected fake-only comparison of one synthetic non-B prompt and usage.

This module has no transport, process, filesystem, CLI, or product-gate
default. Its callbacks are test observations, not evidence of a live runner.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import os
import re
from threading import Lock

from p4_b_isolated_ollama_identity_probe import (
    FROZEN_DAEMON_SHA256, FROZEN_MANIFEST_SHA256, FROZEN_RUNNER_SHA256,
    GGUF_SHA256, MODEL, SYSTEM_SHA256, TEMPLATE_SHA256, VERSION,
)
from uruha_compact_planner_p2 import compact_request


_SCHEMA = "p4_b_non_b_usage_parity_fake_v1"
_FIXED_SHA256 = "7ea87c8e8985dfe7fb2b5dc9198cd9f26caaaa3fbf4c93559405a06230b4eb56"
_FIXED_UTF8_BYTES = 1833
_PRECOMPACT_SYSTEM = (
    "You are the Left Brain Planner for a dual-brain character system.\n"
    "Synthetic parity only.\n[Output JSON schema]\nNever part of the experiment."
)
_PRECOMPACT_USER = 'User Input: 非Bの検証用。改行\nJSON記号 {"x":1} だけ。'
_REQUEST_KEYS = frozenset({"model", "messages", "temperature", "timeout",
                           "max_tokens", "response_format"})
_BINDING_KEYS = frozenset({
    "run_id", "daemon_pid", "daemon_port", "daemon_raw_generation",
    "daemon_argv_sha256", "daemon_binary_sha256", "manifest_sha256",
    "template_sha256", "system_sha256", "gguf_sha256", "daemon_url",
})
_IDENTITY_KEYS = frozenset({"run_id", "daemon", "runner", "identity_http_calls"})
_DAEMON_KEYS = frozenset({
    "pid", "port", "raw_generation", "argv_sha256", "binary_sha256",
    "manifest_sha256", "template_sha256", "system_sha256", "gguf_sha256", "url",
})
_RUNNER_KEYS = frozenset({
    "pid", "parent_pid", "port", "raw_generation", "argv_sha256",
    "binary_sha256", "gguf_sha256", "url", "context_total", "parallel",
    "add_bos_token", "leading_bos", "truncation_observed",
})
_HTTP_KEYS = frozenset({"requested_url", "effective_url", "proxy_used",
                        "redirected", "status", "body"})
_RECEIPT_KEYS = frozenset({
    "schema", "status", "request_sha256", "request_utf8_bytes",
    "rendered_prompt_sha256", "rendered_prompt_utf8_bytes",
    "rendered_prompt_chars", "identity_observation_sha256",
    "runner_token_count_parse_special_true",
    "runner_token_count_parse_special_default", "provider_usage", "signed_delta",
    "http_calls", "identity_checks", "external_completion_attempts",
    "internal_runner_generations", "elapsed_seconds", "upper_bound_proven",
    "b_safari_send_authorized",
})
_SHA_RE = re.compile(r"[0-9a-f]{64}\Z")
_RUN_RE = re.compile(r"[A-Za-z0-9._-]{1,128}\Z")
_REQUEST_LIMIT = 256 * 1024
_RESPONSE_LIMIT = 2 * 1024 * 1024
_FIXTURE_LOCK = Lock()


class ParityError(RuntimeError):
    """A fixed, raw-free failure code, never a callback exception wrapper."""


def _fail(code: str):
    raise ParityError(code) from None


def _canonical(value, code: str) -> bytes:
    failed = False
    try:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    except Exception:
        failed = True
    if failed:
        _fail(code)
    return raw


def _sha_text(value, code: str) -> str:
    if type(value) is not str:
        _fail(code)
    failed = False
    try:
        result = hashlib.sha256(value.encode("utf-8")).hexdigest()
    except Exception:
        failed = True
    if failed:
        _fail(code)
    return result


def _generation(value, pid: int) -> bool:
    return (type(value) is list and len(value) == 4
            and all(type(part) is int and part >= 0 for part in value)
            and value[0] == pid)


def _valid_port(value) -> bool:
    return type(value) is int and 1 <= value <= 65535 and value != 11434


def _valid_sha(value) -> bool:
    return type(value) is str and _SHA_RE.fullmatch(value) is not None


def fixed_transformed_request() -> dict:
    """Run the real compact transform under two explicit, restored env arms.

    The temporary environment is process-global; the lock serializes this
    helper, while callers must not invoke it concurrently with unrelated code
    that edits or reads the same environment settings.
    """
    before = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": _PRECOMPACT_SYSTEM},
            {"role": "user", "content": _PRECOMPACT_USER},
        ],
        "temperature": 0.1, "timeout": 20.0, "max_tokens": 256,
    }
    schema_arm = "URUHA_P4_COMPACT_JSON_SCHEMA"
    source_arm = "URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT"
    with _FIXTURE_LOCK:
        old_schema = os.environ.get(schema_arm)
        old_source = os.environ.get(source_arm)
        failed = False
        transformed = None
        try:
            os.environ[schema_arm] = "1"
            os.environ.pop(source_arm, None)
            transformed = compact_request(deepcopy(before))
        except Exception:
            failed = True
        finally:
            if old_schema is None:
                os.environ.pop(schema_arm, None)
            else:
                os.environ[schema_arm] = old_schema
            if old_source is None:
                os.environ.pop(source_arm, None)
            else:
                os.environ[source_arm] = old_source
    if failed:
        _fail("parity_fixed_request_drift")
    _fixed_request_bytes(transformed)
    return deepcopy(transformed)


def _fixed_request_bytes(request) -> bytes:
    if type(request) is not dict:
        _fail("parity_fixed_request_drift")
    raw = _canonical(request, "parity_fixed_request_drift")
    if (len(raw) != _FIXED_UTF8_BYTES
            or hashlib.sha256(raw).hexdigest() != _FIXED_SHA256):
        _fail("parity_fixed_request_drift")
    if set(json.loads(raw)) != _REQUEST_KEYS:
        _fail("parity_fixed_request_drift")
    return raw


def _binding_copy(value) -> tuple[dict, bytes]:
    if type(value) is not dict:
        _fail("parity_binding_invalid")
    raw = _canonical(value, "parity_binding_invalid")
    failed = False
    try:
        binding = json.loads(raw)
    except Exception:
        failed = True
    if failed:
        _fail("parity_binding_invalid")
    if set(binding) != _BINDING_KEYS:
        _fail("parity_binding_invalid")
    pid = binding["daemon_pid"]
    port = binding["daemon_port"]
    if (type(binding["run_id"]) is not str
            or _RUN_RE.fullmatch(binding["run_id"]) is None
            or type(pid) is not int or pid <= 0
            or not _valid_port(port)
            or not _generation(binding["daemon_raw_generation"], pid)
            or binding["daemon_url"] != f"http://127.0.0.1:{port}"
            or type(binding["daemon_url"]) is not str
            or not _valid_sha(binding["daemon_argv_sha256"])
            or binding["daemon_binary_sha256"] != FROZEN_DAEMON_SHA256
            or binding["manifest_sha256"] != FROZEN_MANIFEST_SHA256
            or binding["template_sha256"] != TEMPLATE_SHA256
            or binding["system_sha256"] != SYSTEM_SHA256
            or binding["gguf_sha256"] != GGUF_SHA256):
        _fail("parity_binding_invalid")
    return binding, raw


def _now(clock, previous: float | None, deadline: float | None) -> float:
    failed = False
    try:
        value = clock()
    except Exception:
        failed = True
    if failed:
        _fail("parity_clock_unavailable")
    try:
        valid = (type(value) in (int, float) and math.isfinite(value)
                 and value >= 0 and (previous is None or value >= previous))
    except (OverflowError, TypeError, ValueError):
        valid = False
    if not valid:
        _fail("parity_clock_invalid")
    if deadline is not None and value >= deadline:
        _fail("parity_deadline_exceeded")
    return float(value)


def _check_unchanged(request, request_raw: bytes, binding, binding_raw: bytes):
    if (_canonical(request, "parity_request_mutated") != request_raw
            or _canonical(binding, "parity_request_mutated") != binding_raw):
        _fail("parity_request_mutated")


def _daemon_record(binding) -> dict:
    return {
        "pid": binding["daemon_pid"], "port": binding["daemon_port"],
        "raw_generation": deepcopy(binding["daemon_raw_generation"]),
        "argv_sha256": binding["daemon_argv_sha256"],
        "binary_sha256": binding["daemon_binary_sha256"],
        "manifest_sha256": binding["manifest_sha256"],
        "template_sha256": binding["template_sha256"],
        "system_sha256": binding["system_sha256"],
        "gguf_sha256": binding["gguf_sha256"], "url": binding["daemon_url"],
    }


def _validate_identity(value, binding, *, runner_required: bool, bound_raw: bytes | None):
    if (type(value) is not dict or set(value) != _IDENTITY_KEYS
            or type(value["run_id"]) is not str
            or value["run_id"] != binding["run_id"]
            or type(value["identity_http_calls"]) is not int
            or value["identity_http_calls"] != 0):
        _fail("parity_identity_drift")
    daemon = value["daemon"]
    expected_daemon = _daemon_record(binding)
    if (type(daemon) is not dict or set(daemon) != _DAEMON_KEYS
            or any(type(daemon[key]) is not type(expected_daemon[key])
                   or daemon[key] != expected_daemon[key] for key in _DAEMON_KEYS)
            or not _generation(daemon["raw_generation"], daemon["pid"])):
        _fail("parity_identity_drift")
    runner = value["runner"]
    if not runner_required:
        if runner is not None:
            _fail("parity_identity_drift")
    else:
        if type(runner) is not dict or set(runner) != _RUNNER_KEYS:
            _fail("parity_identity_drift")
        pid, port = runner["pid"], runner["port"]
        if (type(pid) is not int or pid <= 0 or pid == daemon["pid"]
                or type(runner["parent_pid"]) is not int
                or runner["parent_pid"] != daemon["pid"]
                or not _valid_port(port) or port == daemon["port"]
                or not _generation(runner["raw_generation"], pid)
                or runner["raw_generation"][1] != daemon["pid"]
                or not _valid_sha(runner["argv_sha256"])
                or not _valid_sha(runner["binary_sha256"])
                or runner["binary_sha256"] != FROZEN_RUNNER_SHA256
                or not _valid_sha(runner["gguf_sha256"])
                or runner["gguf_sha256"] != GGUF_SHA256
                or type(runner["url"]) is not str
                or runner["url"] != f"http://127.0.0.1:{port}"
                or type(runner["context_total"]) is not int
                or runner["context_total"] <= 0
                or type(runner["parallel"]) is not int
                or runner["parallel"] <= 0
                or runner["context_total"] % runner["parallel"] != 0
                or runner["add_bos_token"] is not False
                or type(runner["leading_bos"]) is not str
                or runner["leading_bos"] != ""
                or runner["truncation_observed"] is not False):
            _fail("parity_identity_drift")
    raw = _canonical(value, "parity_identity_drift")
    if bound_raw is not None and raw != bound_raw:
        _fail("parity_identity_drift")
    return raw


def _parse_response(body: bytes) -> dict:
    def reject_constant(_text):
        raise ValueError

    def finite_float(text):
        value = float(text)
        if not math.isfinite(value):
            raise ValueError
        return value

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError
            result[key] = value
        return result

    failed = False
    try:
        result = json.loads(body, parse_constant=reject_constant,
                            parse_float=finite_float, object_pairs_hook=unique_object)
    except Exception:
        failed = True
    if failed or type(result) is not dict:
        _fail("parity_response_invalid")
    # JSON decoding itself has a depth limit, but a shallower contract keeps
    # callback-supplied trees bounded before metadata/usage inspection.
    pending = [(result, 0)]
    visited = 0
    while pending:
        item, depth = pending.pop()
        visited += 1
        if visited > 100_000 or depth > 64:
            _fail("parity_response_invalid")
        if type(item) is dict:
            if any(not _utf8_encodable(key) for key in item):
                _fail("parity_response_invalid")
            pending.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            pending.extend((child, depth + 1) for child in item)
        elif type(item) is str:
            if not _utf8_encodable(item):
                _fail("parity_response_invalid")
        elif type(item) is float and not math.isfinite(item):
            _fail("parity_response_invalid")
    return result


def _utf8_encodable(value: str) -> bool:
    try:
        value.encode("utf-8")
    except UnicodeError:
        return False
    return True


def _model_metadata(index: int, response: dict):
    if index == 1:
        if response.get("version") != VERSION:
            _fail("parity_model_metadata_drift")
    elif index == 2:
        rows = response.get("models")
        if (type(rows) is not list or len(rows) != 1
                or type(rows[0]) is not dict
                or rows[0].get("name") != MODEL
                or rows[0].get("digest") != FROZEN_MANIFEST_SHA256):
            _fail("parity_model_metadata_drift")
    else:
        if (_sha_text(response.get("template"), "parity_model_metadata_drift")
                != TEMPLATE_SHA256
                or _sha_text(response.get("system"), "parity_model_metadata_drift")
                != SYSTEM_SHA256):
            _fail("parity_model_metadata_drift")


def _rendered(response: dict, request: dict) -> tuple[str, bytes]:
    failed = False
    try:
        rendered = response["_debug_info"]["rendered_template"]
        usage = response["usage"]
        choices = response["choices"]
        valid = (response.get("model") == MODEL and type(rendered) is str
                 and bool(rendered) and type(usage) is dict
                 and all(type(usage.get(key)) is int and usage[key] == 0
                         for key in ("prompt_tokens", "completion_tokens", "total_tokens"))
                 and type(choices) is list and len(choices) == 1
                 and type(choices[0]) is dict
                 and type(choices[0].get("message")) is dict
                 and choices[0]["message"].get("content") == "")
    except (KeyError, TypeError, IndexError):
        failed = True
    if failed or not valid:
        _fail("parity_render_drift")
    system = request["messages"][0]["content"]
    user = request["messages"][1]["content"]
    system_marker = rendered.find("<|im_start|>system")
    system_text = rendered.find(system, system_marker + 18)
    user_marker = rendered.find("<|im_start|>user", system_text + len(system))
    user_text = rendered.find(user, user_marker + 16)
    if min(system_marker, system_text, user_marker, user_text) < 0:
        _fail("parity_render_drift")
    encoded = False
    try:
        raw = rendered.encode("utf-8")
    except Exception:
        encoded = True
    if encoded:
        _fail("parity_render_drift")
    return rendered, raw


def _token_ids(response: dict) -> list[int]:
    tokens = response.get("tokens")
    if (type(tokens) is not list or not tokens
            or any(type(token) is not int or token < 0 for token in tokens)):
        _fail("parity_tokenizer_drift")
    return tokens


def _usage(response: dict) -> dict:
    usage = response.get("usage")
    choices = response.get("choices")
    if (response.get("model") != MODEL or type(usage) is not dict
            or type(choices) is not list or not choices
            or type(choices[0]) is not dict
            or type(choices[0].get("message")) is not dict
            or type(choices[0]["message"].get("content")) is not str
            or not choices[0]["message"]["content"]):
        _fail("parity_usage_drift")
    fields = ("prompt_tokens", "completion_tokens", "total_tokens")
    if (any(type(usage.get(key)) is not int for key in fields)
            or usage["prompt_tokens"] <= 0 or usage["completion_tokens"] <= 0
            or usage["total_tokens"] != usage["prompt_tokens"] + usage["completion_tokens"]):
        _fail("parity_usage_drift")
    return {key: usage[key] for key in fields}


def compare_non_b_parity(*, request, daemon_binding, observe_identity,
                         http_call, clock, max_elapsed_seconds=5.0) -> dict:
    """Run seven injected fake HTTP operations and six OS-only observations.

    Nonzero Δ is an in-memory negative receipt, never a revised tolerance or
    retry. No receipt from this function proves B bounds or authorizes Send.
    """
    if not callable(clock):
        _fail("parity_configuration_invalid")
    started = _now(clock, None, None)
    try:
        valid_budget = (type(max_elapsed_seconds) in (int, float)
                        and math.isfinite(max_elapsed_seconds)
                        and 0 < max_elapsed_seconds <= 5.0)
    except (OverflowError, TypeError, ValueError):
        valid_budget = False
    if (not valid_budget or not callable(observe_identity)
            or not callable(http_call)):
        _fail("parity_configuration_invalid")
    deadline = started + max_elapsed_seconds
    if not math.isfinite(deadline):
        _fail("parity_clock_invalid")
    request_raw = _fixed_request_bytes(request)
    binding, binding_raw = _binding_copy(daemon_binding)
    # json.loads provides a fresh plain-data copy without retaining caller
    # objects or asking callbacks to serialize the original request.
    copied = json.loads(request_raw)
    normal = deepcopy(copied)
    del normal["timeout"]
    debug = deepcopy(normal)
    debug["_debug_render_only"] = True
    previous = started
    http_count = 0
    identity_count = 0
    external_attempts = 0

    def tick():
        nonlocal previous
        previous = _now(clock, previous, deadline)
        return previous

    def check():
        _check_unchanged(request, request_raw, daemon_binding, binding_raw)

    def observe(stage: str, *, runner_required: bool, bound_raw: bytes | None = None):
        nonlocal identity_count
        tick()
        failed = False
        try:
            value = observe_identity(stage)
        except Exception:
            failed = True
        identity_count += 1
        tick()
        check()
        if failed:
            _fail("parity_identity_unavailable")
        validation_failed = False
        try:
            raw = _validate_identity(value, binding, runner_required=runner_required,
                                     bound_raw=bound_raw)
        except Exception:
            validation_failed = True
        if validation_failed:
            _fail("parity_identity_drift")
        return raw

    def send(method: str, url: str, payload) -> dict:
        nonlocal http_count
        tick()
        if http_count >= 7:
            _fail("parity_http_budget_exceeded")
        if payload is not None:
            payload_raw = _canonical(payload, "parity_request_invalid")
            if len(payload_raw) > _REQUEST_LIMIT:
                _fail("parity_request_too_large")
            sent = json.loads(payload_raw)
        else:
            payload_raw = None
            sent = None
        remaining = deadline - previous
        failed = False
        try:
            value = http_call(method, url, sent, remaining)
        except Exception:
            failed = True
        http_count += 1
        tick()
        check()
        if payload_raw is not None and _canonical(sent, "parity_request_mutated") != payload_raw:
            _fail("parity_request_mutated")
        if failed:
            _fail("parity_http_failed")
        invalid_transport = False
        try:
            invalid_transport = (type(value) is not dict or set(value) != _HTTP_KEYS
                                 or type(value["requested_url"]) is not str
                                 or value["requested_url"] != url
                                 or type(value["effective_url"]) is not str
                                 or value["effective_url"] != url
                                 or value["proxy_used"] is not False
                                 or value["redirected"] is not False
                                 or type(value["status"]) is not int
                                 or value["status"] != 200
                                 or type(value["body"]) is not bytes)
        except Exception:
            invalid_transport = True
        if invalid_transport:
            _fail("parity_transport_drift")
        body = value["body"]
        if len(body) > _RESPONSE_LIMIT:
            _fail("parity_response_too_large")
        return _parse_response(body)

    observe("before_metadata", runner_required=False)
    daemon_url = f"http://127.0.0.1:{binding['daemon_port']}"
    for index, (method, suffix, payload) in enumerate((
            ("GET", "/api/version", None),
            ("GET", "/api/tags", None),
            ("POST", "/api/show", {"model": MODEL}),
    ), start=1):
        _model_metadata(index, send(method, daemon_url + suffix, payload))
    render_result = send("POST", daemon_url + "/v1/chat/completions", debug)
    rendered, rendered_raw = _rendered(render_result, copied)
    bound_identity_raw = observe("after_render", runner_required=True)
    runner_port = json.loads(bound_identity_raw)["runner"]["port"]
    runner_url = f"http://127.0.0.1:{runner_port}"
    observe("before_tokenize_true", runner_required=True, bound_raw=bound_identity_raw)
    true_tokens = _token_ids(send("POST", runner_url + "/tokenize", {
        "content": rendered, "add_special": False, "parse_special": True,
    }))
    observe("before_tokenize_default", runner_required=True, bound_raw=bound_identity_raw)
    default_tokens = _token_ids(send("POST", runner_url + "/tokenize", {
        "content": rendered, "add_special": False,
    }))
    if true_tokens != default_tokens:
        _fail("parity_tokenizer_drift")
    runner = json.loads(bound_identity_raw)["runner"]
    effective_num_ctx = runner["context_total"] // runner["parallel"]
    if len(true_tokens) >= effective_num_ctx:
        _fail("parity_context_not_proven")
    observe("before_completion", runner_required=True, bound_raw=bound_identity_raw)
    external_attempts += 1
    completion = send("POST", daemon_url + "/v1/chat/completions", normal)
    observe("after_completion", runner_required=True, bound_raw=bound_identity_raw)
    provider_usage = _usage(completion)
    delta = provider_usage["prompt_tokens"] - len(true_tokens)
    tick()
    check()
    receipt = {
        "schema": _SCHEMA,
        "status": "fake_non_b_parity_pass" if delta == 0 else "fake_non_b_parity_mismatch",
        "request_sha256": _FIXED_SHA256,
        "request_utf8_bytes": len(request_raw),
        "rendered_prompt_sha256": hashlib.sha256(rendered_raw).hexdigest(),
        "rendered_prompt_utf8_bytes": len(rendered_raw),
        "rendered_prompt_chars": len(rendered),
        "identity_observation_sha256": hashlib.sha256(bound_identity_raw).hexdigest(),
        "runner_token_count_parse_special_true": len(true_tokens),
        "runner_token_count_parse_special_default": len(default_tokens),
        "provider_usage": provider_usage,
        "signed_delta": delta,
        "http_calls": http_count,
        "identity_checks": identity_count,
        "external_completion_attempts": external_attempts,
        "internal_runner_generations": "unknown",
        "elapsed_seconds": previous - started,
        "upper_bound_proven": False,
        "b_safari_send_authorized": False,
    }
    return receipt
