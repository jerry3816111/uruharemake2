"""Product-disconnected P4-B transformed-request diagnostic contract.

No real transport default, CLI, product gate activation, or B Send authority.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import re

from p4_b_isolated_ollama_identity_probe import (
    FROZEN_DAEMON_SHA256, FROZEN_MANIFEST_SHA256, FROZEN_RUNNER_SHA256,
    SYSTEM_SHA256, TEMPLATE_SHA256,
)
from uruha_compact_planner_p2 import _REQUIRED_JSON_SCHEMA_FORMAT
from uruha_p4_b_private_endpoint_binding import (
    PrivateEndpointBinding, _binding_shape,
)


_REQUEST_KEYS = frozenset({
    "model", "messages", "temperature", "timeout", "max_tokens",
    "response_format",
})
_IDENTITY_KEYS = frozenset({
    "run_id", "daemon_pid", "runner_pid", "daemon_port", "runner_port",
    "daemon_raw_generation", "runner_raw_generation", "daemon_argv_sha256",
    "runner_argv_sha256", "daemon_binary_sha256", "runner_binary_sha256",
    "manifest_sha256", "template_sha256", "system_sha256", "daemon_url",
    "runner_url",
})
_TRANSPORT_KEYS = frozenset({
    "requested_url", "effective_url", "proxy_used", "redirected",
    "completion_generated", "status", "body",
})
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_REQUEST_LIMIT = 256 * 1024
_RESPONSE_LIMIT = 2 * 1024 * 1024
_SYSTEM_PREFIX = "You are the Left Brain Planner for a dual-brain character system."


class DiagnosticError(RuntimeError):
    """Fixed, raw-free failure code."""


def _fail(reason: str):
    raise DiagnosticError(reason) from None


def _canonical(value) -> bytes:
    invalid = False
    try:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    except Exception:
        invalid = True
    if invalid:
        _fail("diagnostic_json_invalid")
    return raw


def _digest(value) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _now(clock, previous: float | None, deadline: float | None) -> float:
    failed = False
    try:
        value = clock()
    except Exception:
        failed = True
    if failed:
        _fail("diagnostic_clock_unavailable")
    try:
        valid = (type(value) in (int, float) and math.isfinite(value)
                 and value >= 0 and (previous is None or value >= previous))
    except (OverflowError, TypeError, ValueError):
        valid = False
    if not valid:
        _fail("diagnostic_clock_invalid")
    if deadline is not None and value >= deadline:
        _fail("diagnostic_deadline_exceeded")
    return float(value)


def _validate_request(request) -> tuple[dict, str]:
    if type(request) is not dict or set(request) != _REQUEST_KEYS:
        _fail("m21_request_drift")
    messages = request.get("messages")
    if (request.get("model") != "qwen2.5:7b"
            or type(request.get("temperature")) not in (int, float)
            or request["temperature"] != 0.1
            or type(request.get("timeout")) not in (int, float)
            or request["timeout"] != 20.0
            or type(request.get("max_tokens")) is not int
            or request["max_tokens"] != 256
            or _canonical(request.get("response_format"))
               != _canonical(_REQUIRED_JSON_SCHEMA_FORMAT)
            or type(messages) is not list or len(messages) != 2
            or any(type(message) is not dict or set(message) != {"role", "content"}
                   for message in messages)
            or messages[0].get("role") != "system"
            or messages[1].get("role") != "user"
            or type(messages[0].get("content")) is not str
            or not messages[0]["content"].startswith(
                (_SYSTEM_PREFIX, "\n" + _SYSTEM_PREFIX))
            or type(messages[1].get("content")) is not str
            or not messages[1]["content"].startswith("User Input: ")):
        _fail("m21_request_drift")
    copied = deepcopy(request)
    raw = _canonical(copied)
    if len(raw) > _REQUEST_LIMIT:
        _fail("diagnostic_request_too_large")
    return copied, hashlib.sha256(raw).hexdigest()


def _expected_identity(binding: PrivateEndpointBinding) -> dict:
    daemon_url = f"http://127.0.0.1:{binding.daemon_port}/v1/chat/completions"
    runner_url = f"http://127.0.0.1:{binding.runner_port}/tokenize"
    return {
        "run_id": binding.run_id,
        "daemon_pid": binding.daemon_pid, "runner_pid": binding.runner_pid,
        "daemon_port": binding.daemon_port, "runner_port": binding.runner_port,
        "daemon_raw_generation": list(binding.daemon_raw_generation),
        "runner_raw_generation": list(binding.runner_raw_generation),
        "daemon_argv_sha256": binding.daemon_argv_sha256,
        "runner_argv_sha256": binding.runner_argv_sha256,
        "daemon_binary_sha256": FROZEN_DAEMON_SHA256,
        "runner_binary_sha256": FROZEN_RUNNER_SHA256,
        "manifest_sha256": FROZEN_MANIFEST_SHA256,
        "template_sha256": TEMPLATE_SHA256,
        "system_sha256": SYSTEM_SHA256,
        "daemon_url": daemon_url, "runner_url": runner_url,
    }


def _checked_identity(identity_check, binding, deadline, expected):
    failed = False
    try:
        observation = identity_check(binding, deadline)
    except Exception:
        failed = True
    if failed:
        _fail("diagnostic_identity_unavailable")
    if (type(observation) is not dict or set(observation) != _IDENTITY_KEYS
            or any(type(observation[key]) is not type(expected[key])
                   or observation[key] != expected[key] for key in _IDENTITY_KEYS)
            or any(any(type(value) is not int for value in observation[key])
                   for key in ("daemon_raw_generation", "runner_raw_generation"))
            or any(type(observation[key]) is not str or not _HEX.fullmatch(observation[key])
                   for key in ("daemon_argv_sha256", "runner_argv_sha256",
                               "daemon_binary_sha256", "runner_binary_sha256",
                               "manifest_sha256", "template_sha256", "system_sha256"))):
        _fail("diagnostic_identity_drift")
    return _digest(observation)


def _checked_post(http_post, url, payload, remaining):
    if remaining <= 0:
        _fail("diagnostic_deadline_exceeded")
    failed = False
    try:
        observation = http_post(url, payload, remaining)
    except Exception:
        failed = True
    if failed:
        _fail("diagnostic_http_failed")
    if (type(observation) is not dict or set(observation) != _TRANSPORT_KEYS
            or observation["requested_url"] != url
            or observation["effective_url"] != url
            or any(observation[key] is not False for key in (
                "proxy_used", "redirected", "completion_generated"))
            or type(observation["status"]) is not int or observation["status"] != 200
            or type(observation["body"]) is not bytes):
        _fail("diagnostic_transport_drift")
    body = observation["body"]
    if len(body) > _RESPONSE_LIMIT:
        _fail("diagnostic_response_too_large")
    invalid = False
    try:
        parsed = json.loads(body)
    except Exception:
        invalid = True
    if invalid:
        _fail("diagnostic_response_invalid")
    if type(parsed) is not dict:
        _fail("diagnostic_response_invalid")
    return parsed


def _rendered_template(result, request) -> str:
    invalid = False
    try:
        rendered = result["_debug_info"]["rendered_template"]
        usage = result["usage"]
        choices = result["choices"]
        if (result.get("model") != "qwen2.5:7b"
                or type(rendered) is not str or not rendered
                or type(usage) is not dict
                or any(type(usage.get(key)) is not int or usage[key] != 0
                       for key in ("prompt_tokens", "completion_tokens", "total_tokens"))
                or type(choices) is not list or len(choices) != 1
                or choices[0]["message"]["content"] != ""):
            _fail("render_only_contract_drift")
        system = request["messages"][0]["content"]
        user = request["messages"][1]["content"]
        system_marker = rendered.find("<|im_start|>system")
        system_text = rendered.find(system, system_marker + 18)
        user_marker = rendered.find("<|im_start|>user", system_text + len(system))
        user_text = rendered.find(user, user_marker + 16)
        if min(system_marker, system_text, user_marker, user_text) < 0:
            _fail("rendered_prompt_branch_unverified")
    except (KeyError, TypeError, IndexError):
        invalid = True
    if invalid:
        _fail("render_only_contract_drift")
    return rendered


def diagnose_transformed_request(*, request, binding, identity_check, http_post,
                                 clock, max_elapsed_seconds=5.0) -> dict:
    """Observe one copied M21 request using only injected identity/HTTP fakes.

    The result is a private diagnostic, never a token-bound certificate. A
    future real transport and product gate require separate review.
    """
    if not callable(clock):
        _fail("diagnostic_configuration_invalid")
    started = _now(clock, None, None)
    try:
        valid_budget = (type(max_elapsed_seconds) in (int, float)
                        and math.isfinite(max_elapsed_seconds)
                        and 0 < max_elapsed_seconds <= 5.0)
    except (OverflowError, TypeError, ValueError):
        valid_budget = False
    if (not valid_budget or not callable(identity_check)
            or not callable(http_post)):
        _fail("diagnostic_configuration_invalid")
    deadline = started + max_elapsed_seconds
    if not math.isfinite(deadline):
        _fail("diagnostic_clock_invalid")
    copied, request_sha = _validate_request(request)
    invalid_binding = False
    try:
        if type(binding) is not PrivateEndpointBinding:
            _fail("diagnostic_binding_invalid")
        _binding_shape(binding, require_digest=True)
    except Exception:
        invalid_binding = True
    if invalid_binding:
        _fail("diagnostic_binding_invalid")
    previous = started
    expected = _expected_identity(binding)
    wire = deepcopy(copied)
    del wire["timeout"]
    wire["_debug_render_only"] = True
    wire_sha = _digest(wire)

    def check_mutation():
        if (_digest(request) != request_sha or _digest(copied) != request_sha
                or _digest(wire) != wire_sha
                or _expected_identity(binding) != expected):
            _fail("diagnostic_request_mutated")

    previous = _now(clock, previous, deadline)
    before_identity = _checked_identity(identity_check, binding, deadline, expected)
    previous = _now(clock, previous, deadline)
    check_mutation()

    daemon_url = expected["daemon_url"]
    previous = _now(clock, previous, deadline)
    result = _checked_post(http_post, daemon_url, wire, deadline - previous)
    previous = _now(clock, previous, deadline)
    check_mutation()
    rendered = _rendered_template(result, copied)
    invalid_rendered = False
    try:
        rendered_bytes = rendered.encode("utf-8")
    except UnicodeError:
        invalid_rendered = True
    if invalid_rendered:
        _fail("render_only_contract_drift")
    rendered_sha = hashlib.sha256(rendered_bytes).hexdigest()

    token_payload = {"content": rendered, "add_special": False, "parse_special": True}
    token_payload_sha = _digest(token_payload)
    previous = _now(clock, previous, deadline)
    token_result = _checked_post(http_post, expected["runner_url"],
                                 token_payload, deadline - previous)
    previous = _now(clock, previous, deadline)
    check_mutation()
    if _digest(token_payload) != token_payload_sha:
        _fail("diagnostic_token_request_mutated")
    tokens = token_result.get("tokens")
    if (type(tokens) is not list or not tokens
            or any(type(token) is not int or token < 0 for token in tokens)):
        _fail("runner_tokenizer_contract_drift")

    previous = _now(clock, previous, deadline)
    after_identity = _checked_identity(identity_check, binding, deadline, expected)
    previous = _now(clock, previous, deadline)
    check_mutation()
    if after_identity != before_identity:
        _fail("diagnostic_identity_changed")
    return {
        "schema": "p4_b_transformed_request_fake_diagnostic_v1",
        "status": "fake_mechanics_only_no_b_authority",
        "request_sha256": request_sha,
        "rendered_prompt_sha256": rendered_sha,
        "rendered_prompt_chars": len(rendered),
        "identity_observation_sha256": before_identity,
        "runner_token_count": len(tokens),
        "diagnostic_http_calls": 2, "identity_checks": 2,
        "elapsed_seconds": previous - started,
        "add_special": False, "parse_special": True,
        "leading_bos_gap_unresolved": True,
        "generated_completions": 0,
        "upper_bound_proven": False,
        "b_safari_send_authorized": False,
    }
