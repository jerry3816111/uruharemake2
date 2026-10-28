"""Fake-only non-B usage parity contract; every HTTP/identity value is injected."""

from copy import deepcopy
import hashlib
import json

import pytest

import p4_b_non_b_usage_parity as parity
from p4_b_isolated_ollama_identity_probe import (
    FROZEN_DAEMON_SHA256, FROZEN_MANIFEST_SHA256, FROZEN_RUNNER_SHA256,
    GGUF_SHA256, SYSTEM_SHA256, TEMPLATE_SHA256,
)


CANARY = "RAW_PARITY_CANARY_MUST_NOT_ESCAPE"
TEMPLATE = "synthetic template, not a real model blob"
SYSTEM = "synthetic system, not a real model blob"
STAGES = [
    "before_metadata", "after_render", "before_tokenize_true",
    "before_tokenize_default", "before_completion", "after_completion",
]


def _sha(raw):
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _json_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _binding():
    return {
        "run_id": "synthetic-run", "daemon_pid": 101, "daemon_port": 11455,
        "daemon_raw_generation": [101, 1, 1000, 12],
        "daemon_argv_sha256": "a" * 64,
        "daemon_binary_sha256": FROZEN_DAEMON_SHA256,
        "manifest_sha256": FROZEN_MANIFEST_SHA256,
        "template_sha256": parity.TEMPLATE_SHA256,
        "system_sha256": parity.SYSTEM_SHA256,
        "gguf_sha256": GGUF_SHA256,
        "daemon_url": "http://127.0.0.1:11455",
    }


def _observation(binding, stage):
    daemon = {
        "pid": binding["daemon_pid"], "port": binding["daemon_port"],
        "raw_generation": deepcopy(binding["daemon_raw_generation"]),
        "argv_sha256": binding["daemon_argv_sha256"],
        "binary_sha256": binding["daemon_binary_sha256"],
        "manifest_sha256": binding["manifest_sha256"],
        "template_sha256": binding["template_sha256"],
        "system_sha256": binding["system_sha256"],
        "gguf_sha256": binding["gguf_sha256"],
        "url": binding["daemon_url"],
    }
    runner = None if stage == "before_metadata" else {
        "pid": 102, "parent_pid": 101, "port": 55132,
        "raw_generation": [102, 101, 1001, 13],
        "argv_sha256": "b" * 64,
        "binary_sha256": FROZEN_RUNNER_SHA256,
        "gguf_sha256": GGUF_SHA256,
        "url": "http://127.0.0.1:55132",
        "context_total": 32768, "parallel": 4,
        "add_bos_token": False, "leading_bos": "",
        "truncation_observed": False,
    }
    return {"run_id": binding["run_id"], "daemon": daemon,
            "runner": runner, "identity_http_calls": 0}


def _harness(monkeypatch, *, synthetic_metadata=True):
    # This substitutes test-only preimages. Production digests are asserted
    # separately below; no private model blobs are read or copied.
    if synthetic_metadata:
        monkeypatch.setattr(parity, "TEMPLATE_SHA256", _sha(TEMPLATE))
        monkeypatch.setattr(parity, "SYSTEM_SHA256", _sha(SYSTEM))
    request = parity.fixed_transformed_request()
    binding = _binding()
    state = {
        "time": 100.0, "stages": [], "calls": [], "identity_change": None,
        "http_change": None, "body_change": None, "tokens_true": [1, 2, 3],
        "tokens_default": [1, 2, 3], "usage": {
            "prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5,
        },
    }
    rendered = ("<|im_start|>system\n" + request["messages"][0]["content"]
                + "<|im_end|>\n<|im_start|>user\n"
                + request["messages"][1]["content"]
                + "<|im_end|>\n<|im_start|>assistant\n" + CANARY)

    def observe_identity(stage):
        state["stages"].append(stage)
        result = _observation(binding, stage)
        if state["identity_change"] is not None:
            state["identity_change"](result, stage)
        return result

    def http_call(method, url, payload, remaining):
        state["calls"].append((method, url, deepcopy(payload), remaining))
        assert 0 < remaining <= 5.0
        index = len(state["calls"])
        if index == 1:
            body = {"version": "0.34.4"}
        elif index == 2:
            body = {"models": [{"name": "qwen2.5:7b",
                                "digest": FROZEN_MANIFEST_SHA256}]}
        elif index == 3:
            body = {"template": TEMPLATE, "system": SYSTEM}
        elif index == 4:
            body = {"model": "qwen2.5:7b",
                    "_debug_info": {"rendered_template": rendered},
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0,
                              "total_tokens": 0},
                    "choices": [{"message": {"content": ""}}]}
        elif index in (5, 6):
            body = {"tokens": deepcopy(state["tokens_true"] if index == 5
                                       else state["tokens_default"])}
        elif index == 7:
            body = {"model": "qwen2.5:7b", "usage": deepcopy(state["usage"]),
                    "choices": [{"message": {"content": CANARY}}]}
        else:
            pytest.fail("an eighth HTTP operation was attempted")
        if state["body_change"] is not None:
            state["body_change"](body, index)
        result = {"requested_url": url, "effective_url": url,
                  "proxy_used": False, "redirected": False,
                  "status": 200, "body": _json_bytes(body)}
        if state["http_change"] is not None:
            state["http_change"](result, index)
        return result

    kwargs = {"request": request, "daemon_binding": binding,
              "observe_identity": observe_identity, "http_call": http_call,
              "clock": lambda: state["time"]}
    return kwargs, state, rendered


def _error(kwargs, code):
    with pytest.raises(parity.ParityError) as caught:
        parity.compare_non_b_parity(**kwargs)
    assert str(caught.value) == code
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert CANARY not in repr(caught.value)


def test_fixed_fixture_real_compact_shape_digest_and_env_restoration(monkeypatch):
    monkeypatch.setenv("URUHA_P4_COMPACT_JSON_SCHEMA", "outer")
    monkeypatch.setenv("URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT", "1")
    request = parity.fixed_transformed_request()
    assert set(request) == {"model", "messages", "temperature", "timeout",
                            "max_tokens", "response_format"}
    assert request["model"] == "qwen2.5:7b"
    assert request["temperature"] == 0.1
    assert request["timeout"] == 20.0
    assert request["max_tokens"] == 256
    assert request["response_format"]["type"] == "json_schema"
    assert len(_json_bytes(request)) == 1833
    assert hashlib.sha256(_json_bytes(request)).hexdigest() == (
        "7ea87c8e8985dfe7fb2b5dc9198cd9f26caaaa3fbf4c93559405a06230b4eb56")
    assert request is not parity.fixed_transformed_request()
    assert __import__("os").environ["URUHA_P4_COMPACT_JSON_SCHEMA"] == "outer"
    assert __import__("os").environ["URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT"] == "1"


def test_fixed_fixture_detects_compact_or_environment_drift(monkeypatch):
    monkeypatch.setattr(parity, "compact_request", lambda _: {"model": "wrong"})
    with pytest.raises(parity.ParityError, match="^parity_fixed_request_drift$"):
        parity.fixed_transformed_request()


def test_unpatched_model_constants_remain_frozen_and_reject_synthetic_show(monkeypatch):
    assert parity.TEMPLATE_SHA256 == TEMPLATE_SHA256
    assert parity.SYSTEM_SHA256 == SYSTEM_SHA256
    assert parity.GGUF_SHA256 == GGUF_SHA256
    kwargs, state, _ = _harness(monkeypatch, synthetic_metadata=False)
    _error(kwargs, "parity_model_metadata_drift")
    assert len(state["calls"]) == 3


def test_positive_fake_parity_exact_order_payloads_receipt_and_no_authority(monkeypatch):
    kwargs, state, rendered = _harness(monkeypatch)
    original_request = deepcopy(kwargs["request"])
    original_binding = deepcopy(kwargs["daemon_binding"])
    receipt = parity.compare_non_b_parity(**kwargs)
    assert kwargs["request"] == original_request
    assert kwargs["daemon_binding"] == original_binding
    assert state["stages"] == STAGES
    assert [(method, url) for method, url, _, _ in state["calls"]] == [
        ("GET", "http://127.0.0.1:11455/api/version"),
        ("GET", "http://127.0.0.1:11455/api/tags"),
        ("POST", "http://127.0.0.1:11455/api/show"),
        ("POST", "http://127.0.0.1:11455/v1/chat/completions"),
        ("POST", "http://127.0.0.1:55132/tokenize"),
        ("POST", "http://127.0.0.1:55132/tokenize"),
        ("POST", "http://127.0.0.1:11455/v1/chat/completions"),
    ]
    assert [call[2] for call in state["calls"][:3]] == [None, None,
                                                         {"model": "qwen2.5:7b"}]
    normal = deepcopy(original_request)
    del normal["timeout"]
    assert state["calls"][3][2] == {**normal, "_debug_render_only": True}
    assert state["calls"][4][2] == {"content": rendered, "add_special": False,
                                    "parse_special": True}
    assert state["calls"][5][2] == {"content": rendered, "add_special": False}
    assert state["calls"][6][2] == normal
    assert receipt["status"] == "fake_non_b_parity_pass"
    assert receipt["signed_delta"] == 0
    assert receipt["http_calls"] == 7
    assert receipt["identity_checks"] == 6
    assert receipt["external_completion_attempts"] == 1
    assert receipt["internal_runner_generations"] == "unknown"
    assert receipt["upper_bound_proven"] is False
    assert receipt["b_safari_send_authorized"] is False
    assert receipt["request_utf8_bytes"] == 1833
    assert receipt["rendered_prompt_utf8_bytes"] == len(rendered.encode())
    assert receipt["runner_token_count_parse_special_true"] == 3
    assert receipt["runner_token_count_parse_special_default"] == 3
    assert receipt["provider_usage"] == {
        "prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5}
    serialized = json.dumps(receipt)
    assert CANARY not in serialized
    assert rendered not in serialized
    assert "tokens" not in receipt
    assert set(receipt) == parity._RECEIPT_KEYS


def test_nonzero_delta_is_retained_negative_without_retry_or_authority(monkeypatch):
    kwargs, state, _ = _harness(monkeypatch)
    state["usage"]["prompt_tokens"] = 4
    state["usage"]["total_tokens"] = 6
    receipt = parity.compare_non_b_parity(**kwargs)
    assert receipt["status"] == "fake_non_b_parity_mismatch"
    assert receipt["signed_delta"] == 1
    assert receipt["external_completion_attempts"] == 1
    assert receipt["upper_bound_proven"] is False
    assert receipt["b_safari_send_authorized"] is False
    assert len(state["calls"]) == 7


def test_negative_delta_is_also_a_retained_negative_without_retry(monkeypatch):
    kwargs, state, _ = _harness(monkeypatch)
    state["usage"]["prompt_tokens"] = 2
    state["usage"]["total_tokens"] = 4
    receipt = parity.compare_non_b_parity(**kwargs)
    assert receipt["status"] == "fake_non_b_parity_mismatch"
    assert receipt["signed_delta"] == -1
    assert receipt["external_completion_attempts"] == 1
    assert receipt["upper_bound_proven"] is False
    assert receipt["b_safari_send_authorized"] is False
    assert len(state["calls"]) == 7


@pytest.mark.parametrize("change", [
    lambda value: value.update(model="qwen2.5:14b"),
    lambda value: value.update(timeout=21.0),
    lambda value: value.update(max_tokens=257),
    lambda value: value.update(stream=True),
    lambda value: value["messages"][1].update(content="User Input: B question"),
    lambda value: value.update(response_format={"type": "json_object"}),
])
def test_request_drift_rejected_before_callbacks(monkeypatch, change):
    kwargs, state, _ = _harness(monkeypatch)
    change(kwargs["request"])
    _error(kwargs, "parity_fixed_request_drift")
    assert state["stages"] == state["calls"] == []


@pytest.mark.parametrize("field,replacement", [
    ("daemon_port", 11434), ("daemon_port", True),
    ("daemon_url", "http://localhost:11455"),
    ("daemon_url", "http://127.0.0.1:11455/evil"),
    ("daemon_binary_sha256", "0" * 64),
    ("manifest_sha256", "0" * 64),
    ("template_sha256", "0" * 64),
    ("gguf_sha256", "0" * 64),
    ("daemon_raw_generation", [999, 1, 1000, 12]),
])
def test_bad_run_binding_rejected_before_callbacks(monkeypatch, field, replacement):
    kwargs, state, _ = _harness(monkeypatch)
    kwargs["daemon_binding"][field] = replacement
    _error(kwargs, "parity_binding_invalid")
    assert state["stages"] == state["calls"] == []


@pytest.mark.parametrize("change", [
    lambda value: value.pop("body"),
    lambda value: value.update(extra=True),
    lambda value: value.update(requested_url="http://127.0.0.1:11434/api/version"),
    lambda value: value.update(effective_url="http://foreign.test/api/version"),
    lambda value: value.update(proxy_used=True),
    lambda value: value.update(redirected=True),
    lambda value: value.update(status=301),
    lambda value: value.update(status=True),
    lambda value: value.update(body=b"x" * (2 * 1024 * 1024 + 1)),
    lambda value: value.update(body=b"not-json"),
    lambda value: value.update(body=b"[1,2,3]"),
])
def test_transport_exact_six_keys_and_body_limits(monkeypatch, change):
    kwargs, state, _ = _harness(monkeypatch)
    state["http_change"] = lambda value, index: change(value) if index == 1 else None
    with pytest.raises(parity.ParityError) as caught:
        parity.compare_non_b_parity(**kwargs)
    assert str(caught.value) in {"parity_transport_drift", "parity_response_too_large",
                                  "parity_response_invalid"}
    assert len(state["calls"]) == 1
    assert state["stages"] == ["before_metadata"]


@pytest.mark.parametrize("index,change,code", [
    (1, lambda body: body.update(version="0.34.3"), "parity_model_metadata_drift"),
    (2, lambda body: body["models"].append({"name": "other"}), "parity_model_metadata_drift"),
    (2, lambda body: body["models"][0].update(digest="0" * 64), "parity_model_metadata_drift"),
    (3, lambda body: body.update(template="wrong"), "parity_model_metadata_drift"),
    (3, lambda body: body.update(system="wrong"), "parity_model_metadata_drift"),
    (4, lambda body: body.update(model="wrong"), "parity_render_drift"),
    (4, lambda body: body["usage"].update(prompt_tokens=True), "parity_render_drift"),
    (4, lambda body: body["choices"][0]["message"].update(content="not empty"), "parity_render_drift"),
    (4, lambda body: body["_debug_info"].update(rendered_template="wrong"), "parity_render_drift"),
])
def test_metadata_and_render_negative_controls(monkeypatch, index, change, code):
    kwargs, state, _ = _harness(monkeypatch)
    state["body_change"] = lambda body, current: change(body) if current == index else None
    _error(kwargs, code)
    assert len(state["calls"]) == index


@pytest.mark.parametrize("index,tokens", [
    (5, []), (5, [True, 2]), (5, [-1]), (5, [1.0]),
    (6, [1, 2, 4]), (6, [1, 2]),
])
def test_tokenizer_exact_id_and_treatment_parity(monkeypatch, index, tokens):
    kwargs, state, _ = _harness(monkeypatch)
    state["tokens_true" if index == 5 else "tokens_default"] = tokens
    _error(kwargs, "parity_tokenizer_drift")
    assert len(state["calls"]) == index
    assert "before_completion" not in state["stages"]


@pytest.mark.parametrize("stage,change", [
    ("before_metadata", lambda obs: obs.update(identity_http_calls=1)),
    ("before_metadata", lambda obs: obs.update(runner={"pid": 102})),
    ("after_render", lambda obs: obs.update(runner=None)),
    ("after_render", lambda obs: obs["runner"].update(parent_pid=999)),
    ("after_render", lambda obs: obs["runner"].update(raw_generation=[102, 999, 1001, 13])),
    ("after_render", lambda obs: obs["runner"].update(port=11434)),
    ("after_render", lambda obs: obs["runner"].update(url="http://foreign.test:55132")),
    ("after_render", lambda obs: obs["runner"].update(binary_sha256="0" * 64)),
    ("after_render", lambda obs: obs["runner"].update(context_total=0)),
    ("after_render", lambda obs: obs["runner"].update(parallel=3)),
    ("after_render", lambda obs: obs["runner"].update(add_bos_token=True)),
    ("after_render", lambda obs: obs["runner"].update(leading_bos="<s>")),
    ("after_render", lambda obs: obs["runner"].update(truncation_observed=True)),
    ("before_completion", lambda obs: obs["runner"].update(argv_sha256="0" * 64)),
])
def test_identity_missing_rotation_context_bos_or_http_drift(monkeypatch, stage, change):
    kwargs, state, _ = _harness(monkeypatch)
    state["identity_change"] = lambda obs, current: change(obs) if current == stage else None
    _error(kwargs, "parity_identity_drift")
    assert state["stages"][-1] == stage
    assert len(state["calls"]) < 7


def test_token_length_equal_effective_context_blocks_completion(monkeypatch):
    kwargs, state, _ = _harness(monkeypatch)
    original = kwargs["observe_identity"]

    def small_context(stage):
        result = original(stage)
        if result["runner"] is not None:
            result["runner"]["context_total"] = 12
        return result

    kwargs["observe_identity"] = small_context
    _error(kwargs, "parity_context_not_proven")
    assert len(state["calls"]) == 6


@pytest.mark.parametrize("usage", [
    None, {}, {"prompt_tokens": True, "completion_tokens": 2, "total_tokens": 3},
    {"prompt_tokens": -1, "completion_tokens": 2, "total_tokens": 1},
    {"prompt_tokens": 3, "completion_tokens": 0, "total_tokens": 3},
    {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 6},
])
def test_usage_negative_controls_consume_only_one_completion(monkeypatch, usage):
    kwargs, state, _ = _harness(monkeypatch)
    state["usage"] = usage
    _error(kwargs, "parity_usage_drift")
    assert len(state["calls"]) == 7
    assert sum(url.endswith("/v1/chat/completions") and
               not payload.get("_debug_render_only", False)
               for _, url, payload, _ in state["calls"] if payload is not None) == 1


@pytest.mark.parametrize("change", [
    lambda body: body.update(choices=[]),
    lambda body: body["choices"][0].update(message={}),
    lambda body: body["choices"][0].update(message={"content": None}),
    lambda body: body["choices"][0].update(message={"content": ""}),
    lambda body: body.update(model="wrong"),
])
def test_missing_choice_content_or_wrong_completion_model_is_negative(monkeypatch, change):
    kwargs, state, _ = _harness(monkeypatch)
    state["body_change"] = lambda body, index: change(body) if index == 7 else None
    _error(kwargs, "parity_usage_drift")
    assert len(state["calls"]) == 7


def test_request_callback_mutation_is_detected_without_changing_parity(monkeypatch):
    kwargs, state, _ = _harness(monkeypatch)
    original = kwargs["http_call"]

    def mutating_http(method, url, payload, remaining):
        result = original(method, url, payload, remaining)
        if len(state["calls"]) == 1:
            kwargs["request"]["model"] = "mutated"
        return result

    kwargs["http_call"] = mutating_http
    _error(kwargs, "parity_request_mutated")
    assert len(state["calls"]) == 1


def test_daemon_binding_nested_mutation_is_detected(monkeypatch):
    kwargs, state, _ = _harness(monkeypatch)
    original = kwargs["http_call"]

    def mutating_http(method, url, payload, remaining):
        result = original(method, url, payload, remaining)
        if len(state["calls"]) == 1:
            kwargs["daemon_binding"]["daemon_raw_generation"][2] += 1
        return result

    kwargs["http_call"] = mutating_http
    _error(kwargs, "parity_request_mutated")
    assert len(state["calls"]) == 1


def test_http_callback_mutating_its_payload_is_detected(monkeypatch):
    kwargs, state, _ = _harness(monkeypatch)
    original = kwargs["http_call"]

    def mutating_http(method, url, payload, remaining):
        result = original(method, url, payload, remaining)
        if len(state["calls"]) == 3:
            payload["model"] = "mutated"
        return result

    kwargs["http_call"] = mutating_http
    _error(kwargs, "parity_request_mutated")
    assert len(state["calls"]) == 3


def test_deep_json_response_is_rejected_before_following_http(monkeypatch):
    kwargs, state, _ = _harness(monkeypatch)
    original = kwargs["http_call"]

    def deeply_nested_http(method, url, payload, remaining):
        result = original(method, url, payload, remaining)
        if len(state["calls"]) == 1:
            nested = "leaf"
            for _ in range(70):
                nested = [nested]
            result["body"] = _json_bytes({"nested": nested})
        return result

    kwargs["http_call"] = deeply_nested_http
    _error(kwargs, "parity_response_invalid")
    assert len(state["calls"]) == 1


@pytest.mark.parametrize("index,number", [
    (1, b"NaN"), (7, b"NaN"), (1, b"1e9999"), (7, b"1e9999"),
])
def test_nonfinite_json_number_is_rejected_at_metadata_or_completion(
        monkeypatch, index, number):
    kwargs, state, _ = _harness(monkeypatch)
    original = kwargs["http_call"]

    def malformed_http(method, url, payload, remaining):
        result = original(method, url, payload, remaining)
        if len(state["calls"]) == index:
            result["body"] = result["body"][:-1] + b',"junk":' + number + b'}'
        return result

    kwargs["http_call"] = malformed_http
    _error(kwargs, "parity_response_invalid")
    assert len(state["calls"]) == index


def test_duplicate_json_key_is_rejected(monkeypatch):
    kwargs, state, _ = _harness(monkeypatch)
    original = kwargs["http_call"]

    def duplicate_http(method, url, payload, remaining):
        result = original(method, url, payload, remaining)
        if len(state["calls"]) == 1:
            result["body"] = b'{"version":"0.34.4","version":"0.34.4"}'
        return result

    kwargs["http_call"] = duplicate_http
    _error(kwargs, "parity_response_invalid")
    assert len(state["calls"]) == 1


@pytest.mark.parametrize("raw", [
    b'{"version":"0.34.4","junk":"\\uD800"}',
    b'{"version":"0.34.4","\\uD800":"junk"}',
])
def test_lone_surrogate_json_key_or_value_is_rejected(monkeypatch, raw):
    kwargs, state, _ = _harness(monkeypatch)
    original = kwargs["http_call"]

    def surrogate_http(method, url, payload, remaining):
        result = original(method, url, payload, remaining)
        if len(state["calls"]) == 1:
            result["body"] = raw
        return result

    kwargs["http_call"] = surrogate_http
    _error(kwargs, "parity_response_invalid")
    assert len(state["calls"]) == 1


def test_callback_supplied_url_never_becomes_next_target(monkeypatch):
    kwargs, state, _ = _harness(monkeypatch)
    state["http_change"] = lambda result, index: result.update(
        effective_url="http://127.0.0.1:11434/steal") if index == 4 else None
    _error(kwargs, "parity_transport_drift")
    assert len(state["calls"]) == 4
    assert all("11434" not in url for _, url, _, _ in state["calls"])


def test_elapsed_counts_all_callbacks_and_deadline_blocks_later_call(monkeypatch):
    kwargs, state, _ = _harness(monkeypatch)
    identity, http = kwargs["observe_identity"], kwargs["http_call"]

    def timed_identity(stage):
        result = identity(stage)
        state["time"] += 0.1
        return result

    def timed_http(method, url, payload, remaining):
        result = http(method, url, payload, remaining)
        state["time"] += 0.1
        return result

    kwargs["observe_identity"] = timed_identity
    kwargs["http_call"] = timed_http
    receipt = parity.compare_non_b_parity(**kwargs)
    assert receipt["elapsed_seconds"] == pytest.approx(1.3)
    assert state["calls"][0][3] < 5.0
    kwargs, state, _ = _harness(monkeypatch)
    original = kwargs["http_call"]

    def expiry_http(method, url, payload, remaining):
        result = original(method, url, payload, remaining)
        if len(state["calls"]) == 4:
            state["time"] = 105.0
        return result

    kwargs["http_call"] = expiry_http
    _error(kwargs, "parity_deadline_exceeded")
    assert len(state["calls"]) == 4


def test_bad_clock_and_configuration_fail_without_callbacks(monkeypatch):
    kwargs, state, _ = _harness(monkeypatch)
    kwargs["clock"] = lambda: float("nan")
    _error(kwargs, "parity_clock_invalid")
    assert state["stages"] == state["calls"] == []
    kwargs, state, _ = _harness(monkeypatch)
    kwargs["max_elapsed_seconds"] = 90
    _error(kwargs, "parity_configuration_invalid")
    assert state["stages"] == state["calls"] == []


@pytest.mark.parametrize("callback", ["http_call", "observe_identity", "clock"])
def test_raw_canary_exception_has_no_context_or_receipt(monkeypatch, callback):
    kwargs, _, _ = _harness(monkeypatch)

    def explode(*_args):
        raise RuntimeError(CANARY)

    kwargs[callback] = explode
    with pytest.raises(parity.ParityError) as caught:
        parity.compare_non_b_parity(**kwargs)
    assert CANARY not in str(caught.value)
    assert CANARY not in repr(caught.value)
    assert caught.value.__context__ is None
    assert caught.value.__cause__ is None


@pytest.mark.parametrize("index", [4, 7])
def test_render_or_normal_callback_exception_has_no_raw_chain(monkeypatch, index):
    kwargs, state, _ = _harness(monkeypatch)
    original = kwargs["http_call"]

    def exploding_http(method, url, payload, remaining):
        if len(state["calls"]) + 1 == index:
            state["calls"].append((method, url, deepcopy(payload), remaining))
            raise RuntimeError(CANARY)
        return original(method, url, payload, remaining)

    kwargs["http_call"] = exploding_http
    _error(kwargs, "parity_http_failed")
    assert len(state["calls"]) == index
