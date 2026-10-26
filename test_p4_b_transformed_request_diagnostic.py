"""Fake-only exact transformed-request diagnostic contract; no physical HTTP."""

from copy import deepcopy
from dataclasses import replace
import hashlib
import json

import pytest

import p4_b_transformed_request_diagnostic as diagnostic
from p4_b_isolated_ollama_identity_probe import (
    FROZEN_DAEMON_SHA256, FROZEN_MANIFEST_SHA256, FROZEN_RUNNER_SHA256,
    SYSTEM_SHA256, TEMPLATE_SHA256,
)
from uruha_compact_planner_p2 import _REQUIRED_JSON_SCHEMA_FORMAT, compact_request
from uruha_p4_b_private_endpoint_binding import PrivateEndpointBinding


CANARY = "SYNTHETIC_CANARY_NEVER_SEND"


def _binding(tmp_path):
    root = (tmp_path / "private").resolve()
    root.mkdir(mode=0o700, parents=True)
    return PrivateEndpointBinding(
        run_id="synthetic-run", private_root=root,
        shared_models=(tmp_path / "shared/models").resolve(),
        receipt_path=root / "p4_b_private_endpoint_launch_receipt.json",
        receipt_sha256="a" * 64, base_url="http://127.0.0.1:11455/v1",
        daemon_pid=101, runner_pid=102, daemon_port=11455, runner_port=55132,
        daemon_process_start="synthetic-daemon", runner_process_start="synthetic-runner",
        daemon_raw_generation=(101, 1, 1000, 12),
        runner_raw_generation=(102, 101, 1001, 13),
        daemon_argv_sha256="b" * 64, runner_argv_sha256="c" * 64,
        operator_source_sha256="d" * 64,
        daemon_binary=(tmp_path / "ollama").resolve(),
        runner_binary=(tmp_path / "runner").resolve(),
    )


def _request():
    return {
        "model": "qwen2.5:7b",
        "messages": [
            {"role": "system", "content": "\nYou are the Left Brain Planner for a dual-brain character system.\nSynthetic only."},
            {"role": "user", "content": "User Input: " + CANARY},
        ],
        "temperature": 0.1, "timeout": 20.0, "max_tokens": 256,
        "response_format": deepcopy(_REQUIRED_JSON_SCHEMA_FORMAT),
    }


def _identity(binding):
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
        "daemon_url": f"http://127.0.0.1:{binding.daemon_port}/v1/chat/completions",
        "runner_url": f"http://127.0.0.1:{binding.runner_port}/tokenize",
    }


def _harness(tmp_path, request=None):
    binding = _binding(tmp_path)
    request = _request() if request is None else request
    original = deepcopy(request)
    state = {"identity_calls": 0, "http_calls": [], "time": 100.0,
             "identity_mutation": None, "identity_second_mutation": None,
             "http_mutation": None,
             "render_mutation": None, "token_mutation": None}
    rendered = ("<|im_start|>system\n" + request["messages"][0]["content"]
                + "<|im_end|>\n<|im_start|>user\n" + request["messages"][1]["content"]
                + "<|im_end|>\n<|im_start|>assistant\n")

    def identity_check(actual_binding, deadline):
        state["identity_calls"] += 1
        assert actual_binding == binding
        assert deadline == 105.0
        value = _identity(binding)
        if state["identity_mutation"]:
            value[state["identity_mutation"][0]] = state["identity_mutation"][1]
        if state["identity_second_mutation"] and state["identity_calls"] == 2:
            value[state["identity_second_mutation"][0]] = state["identity_second_mutation"][1]
        return value

    def http_post(url, payload, timeout_seconds):
        state["http_calls"].append((url, deepcopy(payload), timeout_seconds))
        assert 0 < timeout_seconds <= 5
        if len(state["http_calls"]) == 1:
            body = {
                "model": "qwen2.5:7b", "_debug_info": {"rendered_template": rendered},
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "choices": [{"message": {"content": ""}}],
            }
            if state["render_mutation"]:
                state["render_mutation"](body)
        else:
            body = {"tokens": [1, 2, 3]}
            if state["token_mutation"]:
                state["token_mutation"](body)
        result = {"requested_url": url, "effective_url": url, "proxy_used": False,
                  "redirected": False, "completion_generated": False, "status": 200,
                  "body": json.dumps(body).encode("utf-8")}
        if state["http_mutation"]:
            state["http_mutation"](result)
        return result

    kwargs = dict(request=request, binding=binding, identity_check=identity_check,
                  http_post=http_post, clock=lambda: state["time"])
    return kwargs, state, original, rendered


def test_exact_transformed_request_two_fake_diagnostics_no_authority(tmp_path):
    kwargs, state, original, rendered = _harness(tmp_path)
    report = diagnostic.diagnose_transformed_request(**kwargs)
    assert kwargs["request"] == original
    assert state["identity_calls"] == 2
    assert [url for url, _, _ in state["http_calls"]] == [
        "http://127.0.0.1:11455/v1/chat/completions",
        "http://127.0.0.1:55132/tokenize",
    ]
    first = state["http_calls"][0][1]
    assert first == {**{key: deepcopy(value) for key, value in original.items() if key != "timeout"},
                     "_debug_render_only": True}
    assert state["http_calls"][1][1] == {
        "content": rendered, "add_special": False, "parse_special": True,
    }
    assert report["diagnostic_http_calls"] == 2
    assert report["identity_checks"] == 2
    assert report["runner_token_count"] == 3
    assert report["generated_completions"] == 0
    assert report["upper_bound_proven"] is False
    assert report["b_safari_send_authorized"] is False
    assert report["leading_bos_gap_unresolved"] is True
    assert report["request_sha256"] == hashlib.sha256(json.dumps(
        original, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest()
    assert CANARY not in json.dumps(report)
    assert rendered not in json.dumps(report)


def test_actual_compact_request_output_enters_fake_diagnostic_unchanged(tmp_path, monkeypatch):
    monkeypatch.setenv("URUHA_P4_COMPACT_JSON_SCHEMA", "1")
    precompact = _request()
    precompact["messages"][0]["content"] += "\n[Output JSON schema]\nBefore-compact-only text"
    before = deepcopy(precompact)
    transformed = compact_request(precompact)
    assert transformed is not None
    assert precompact == before
    assert transformed["messages"][0]["content"] != before["messages"][0]["content"]
    assert "Before-compact-only text" not in transformed["messages"][0]["content"]
    assert transformed["response_format"] == _REQUIRED_JSON_SCHEMA_FORMAT
    kwargs, state, original, rendered = _harness(tmp_path, transformed)
    report = diagnostic.diagnose_transformed_request(**kwargs)
    assert kwargs["request"] == original == transformed
    assert state["http_calls"][0][1]["messages"] == transformed["messages"]
    assert state["http_calls"][1][1]["content"] == rendered
    assert report["diagnostic_http_calls"] == 2
    assert report["upper_bound_proven"] is False
    assert report["b_safari_send_authorized"] is False


def test_fake_elapsed_cost_includes_both_identity_checks_and_both_http_calls(tmp_path):
    kwargs, state, _, _ = _harness(tmp_path)
    identity = kwargs["identity_check"]
    post = kwargs["http_post"]

    def timed_identity(binding, deadline):
        result = identity(binding, deadline)
        state["time"] += 0.5
        return result

    def timed_post(url, payload, timeout_seconds):
        result = post(url, payload, timeout_seconds)
        state["time"] += 0.5
        return result

    kwargs["identity_check"] = timed_identity
    kwargs["http_post"] = timed_post
    report = diagnostic.diagnose_transformed_request(**kwargs)
    assert report["elapsed_seconds"] == 2.0
    assert [timeout for _, _, timeout in state["http_calls"]] == [4.5, 4.0]


def test_fake_elapsed_cost_starts_before_request_validation(tmp_path, monkeypatch):
    kwargs, state, _, _ = _harness(tmp_path)
    original_validate = diagnostic._validate_request

    def costed_validation(request):
        result = original_validate(request)
        state["time"] += 0.25
        return result

    monkeypatch.setattr(diagnostic, "_validate_request", costed_validation)
    report = diagnostic.diagnose_transformed_request(**kwargs)
    assert report["elapsed_seconds"] == 0.25
    assert state["http_calls"][0][2] == 4.75


@pytest.mark.parametrize("boundary,expected_http", [
    ("before_first_http", 0), ("before_second_http", 1),
    ("before_second_identity", 2),
])
def test_deadline_is_rechecked_immediately_before_each_later_callback(
        tmp_path, monkeypatch, boundary, expected_http):
    kwargs, state, _, _ = _harness(tmp_path)
    if boundary == "before_second_http":
        original_render = diagnostic._rendered_template

        def slow_render(*args):
            rendered = original_render(*args)
            state["time"] = 105.1
            return rendered

        monkeypatch.setattr(diagnostic, "_rendered_template", slow_render)
    else:
        original_digest = diagnostic._digest
        calls = {"matching": 0}
        target = "_debug_render_only" if boundary == "before_first_http" else "parse_special"

        def slow_digest(value):
            result = original_digest(value)
            if type(value) is dict and target in value:
                calls["matching"] += 1
                if calls["matching"] == 2:
                    state["time"] = 105.1
            return result

        monkeypatch.setattr(diagnostic, "_digest", slow_digest)
    with pytest.raises(diagnostic.DiagnosticError, match="diagnostic_deadline_exceeded"):
        diagnostic.diagnose_transformed_request(**kwargs)
    assert len(state["http_calls"]) == expected_http
    assert state["identity_calls"] == 1


@pytest.mark.parametrize("change", [
    lambda request: request.update(model="other"),
    lambda request: request.update(timeout=21.0),
    lambda request: request.update(max_tokens=257),
    lambda request: request.update(response_format={"type": "json_object"}),
    lambda request: request.update(stream=True),
    lambda request: request.pop("timeout"),
    lambda request: request["messages"][0].update(content="  You are the Left Brain Planner for a dual-brain character system."),
    lambda request: request["messages"][1].update(content="bare input"),
])
def test_request_drift_rejected_before_callbacks(tmp_path, change):
    kwargs, state, _, _ = _harness(tmp_path)
    change(kwargs["request"])
    with pytest.raises(diagnostic.DiagnosticError):
        diagnostic.diagnose_transformed_request(**kwargs)
    assert state["identity_calls"] == 0
    assert state["http_calls"] == []


@pytest.mark.parametrize("change", [
    lambda binding: replace(binding, daemon_port=11434),
    lambda binding: replace(binding, base_url="http://localhost:11455/v1"),
    lambda binding: replace(binding, runner_raw_generation=(102, 999, 1001, 13)),
])
def test_nonprivate_or_drifted_binding_rejected_before_callbacks(tmp_path, change):
    kwargs, state, _, _ = _harness(tmp_path)
    kwargs["binding"] = change(kwargs["binding"])
    with pytest.raises(diagnostic.DiagnosticError):
        diagnostic.diagnose_transformed_request(**kwargs)
    assert state["identity_calls"] == 0
    assert state["http_calls"] == []


@pytest.mark.parametrize("field,value", [
    ("daemon_raw_generation", [101, 1, 9999, 12]),
    ("daemon_raw_generation", [101, True, 1000, 12]),
    ("runner_argv_sha256", "0" * 64),
    ("template_sha256", "0" * 64),
    ("manifest_sha256", "0" * 64),
    ("runner_url", "http://127.0.0.1:11434/tokenize"),
])
def test_structured_identity_drift_rejected_before_http(tmp_path, field, value):
    kwargs, state, _, _ = _harness(tmp_path)
    state["identity_mutation"] = (field, value)
    with pytest.raises(diagnostic.DiagnosticError):
        diagnostic.diagnose_transformed_request(**kwargs)
    assert state["identity_calls"] == 1
    assert state["http_calls"] == []


@pytest.mark.parametrize("field,value", [
    ("requested_url", "http://127.0.0.1:11434/v1/chat/completions"),
    ("effective_url", "http://127.0.0.1:11434/v1/chat/completions"),
    ("proxy_used", True), ("redirected", True),
    ("completion_generated", True), ("status", 302),
    ("body", b"x" * (2 * 1024 * 1024 + 1)),
], ids=["requested-url", "effective-url", "proxy", "redirect", "completion",
        "status", "oversize-body"])
def test_transport_observation_fails_closed(tmp_path, field, value):
    kwargs, state, _, _ = _harness(tmp_path)
    state["http_mutation"] = lambda result: result.update({field: value})
    with pytest.raises(diagnostic.DiagnosticError):
        diagnostic.diagnose_transformed_request(**kwargs)
    assert state["identity_calls"] == 1
    assert len(state["http_calls"]) == 1


@pytest.mark.parametrize("mutation", [
    lambda body: body["choices"][0]["message"].update(content="generated"),
    lambda body: body["usage"].update(completion_tokens=1),
    lambda body: body.update(model="wrong"),
    lambda body: body["_debug_info"].update(rendered_template="<|im_start|>system\nwrong"),
    lambda body: body.pop("_debug_info"),
])
def test_render_shape_or_branch_fails_closed(tmp_path, mutation):
    kwargs, state, _, _ = _harness(tmp_path)
    state["render_mutation"] = mutation
    with pytest.raises(diagnostic.DiagnosticError):
        diagnostic.diagnose_transformed_request(**kwargs)
    assert len(state["http_calls"]) == 1


@pytest.mark.parametrize("tokens", [[], [True], [-1], ["1"], None])
def test_tokenizer_shape_fails_closed(tmp_path, tokens):
    kwargs, state, _, _ = _harness(tmp_path)
    state["token_mutation"] = lambda body: body.update(tokens=tokens)
    with pytest.raises(diagnostic.DiagnosticError):
        diagnostic.diagnose_transformed_request(**kwargs)
    assert len(state["http_calls"]) == 2


def test_request_mutation_and_timeout_keep_error_raw_free(tmp_path):
    kwargs, state, _, _ = _harness(tmp_path)
    original_identity = kwargs["identity_check"]

    def mutate_request(binding, deadline):
        result = original_identity(binding, deadline)
        kwargs["request"]["messages"][1]["content"] = CANARY + " changed"
        return result

    kwargs["identity_check"] = mutate_request
    with pytest.raises(diagnostic.DiagnosticError) as caught:
        diagnostic.diagnose_transformed_request(**kwargs)
    assert CANARY not in str(caught.value)
    assert caught.value.__context__ is None
    assert state["http_calls"] == []

    kwargs, state, _, _ = _harness(tmp_path / "next")
    original_identity = kwargs["identity_check"]

    def overrun(binding, deadline):
        result = original_identity(binding, deadline)
        state["time"] = 106.0
        return result

    kwargs["identity_check"] = overrun
    with pytest.raises(diagnostic.DiagnosticError) as caught:
        diagnostic.diagnose_transformed_request(**kwargs)
    assert CANARY not in str(caught.value)
    assert caught.value.__context__ is None
    assert state["http_calls"] == []


def test_second_identity_change_and_backward_clock_fail_closed(tmp_path):
    kwargs, state, _, _ = _harness(tmp_path)
    state["identity_second_mutation"] = ("runner_raw_generation", [102, 101, 9999, 13])
    with pytest.raises(diagnostic.DiagnosticError):
        diagnostic.diagnose_transformed_request(**kwargs)
    assert state["identity_calls"] == 2
    assert len(state["http_calls"]) == 2

    kwargs, state, _, _ = _harness(tmp_path / "backward")
    original_identity = kwargs["identity_check"]

    def backwards(binding, deadline):
        result = original_identity(binding, deadline)
        state["time"] = 99.0
        return result

    kwargs["identity_check"] = backwards
    with pytest.raises(diagnostic.DiagnosticError, match="diagnostic_clock_invalid"):
        diagnostic.diagnose_transformed_request(**kwargs)
    assert state["http_calls"] == []


def test_callback_exception_and_wire_mutation_do_not_leak_raw(tmp_path):
    kwargs, state, _, _ = _harness(tmp_path)

    def raise_canary(url, payload, timeout_seconds):
        raise RuntimeError(CANARY)

    kwargs["http_post"] = raise_canary
    with pytest.raises(diagnostic.DiagnosticError) as caught:
        diagnostic.diagnose_transformed_request(**kwargs)
    assert CANARY not in str(caught.value)
    assert caught.value.__context__ is None

    kwargs, state, _, _ = _harness(tmp_path / "deep-json")
    kwargs["http_post"] = lambda url, payload, timeout_seconds: {
        "requested_url": url, "effective_url": url, "proxy_used": False,
        "redirected": False, "completion_generated": False, "status": 200,
        "body": b"[" * 1500 + b"0" + b"]" * 1500,
    }
    with pytest.raises(diagnostic.DiagnosticError, match="diagnostic_response_invalid") as caught:
        diagnostic.diagnose_transformed_request(**kwargs)
    assert caught.value.__context__ is None

    kwargs, state, _, _ = _harness(tmp_path / "bad-json")
    kwargs["http_post"] = lambda url, payload, timeout_seconds: {
        "requested_url": url, "effective_url": url, "proxy_used": False,
        "redirected": False, "completion_generated": False, "status": 200,
        "body": ("{\"raw\":\"" + CANARY).encode(),
    }
    with pytest.raises(diagnostic.DiagnosticError) as caught:
        diagnostic.diagnose_transformed_request(**kwargs)
    assert CANARY not in str(caught.value)
    assert caught.value.__context__ is None

    kwargs, state, _, _ = _harness(tmp_path / "mutated")
    original_post = kwargs["http_post"]

    def mutate_wire(url, payload, timeout_seconds):
        payload["messages"][1]["content"] = CANARY + " changed"
        return original_post(url, payload, timeout_seconds)

    kwargs["http_post"] = mutate_wire
    with pytest.raises(diagnostic.DiagnosticError, match="diagnostic_request_mutated"):
        diagnostic.diagnose_transformed_request(**kwargs)
    assert len(state["http_calls"]) == 1

@pytest.mark.parametrize("clock_value", [float("nan"), float("inf"), -1.0])
def test_bad_clock_rejected_before_callbacks(tmp_path, clock_value):
    kwargs, state, _, _ = _harness(tmp_path)
    kwargs["clock"] = lambda: clock_value
    with pytest.raises(diagnostic.DiagnosticError):
        diagnostic.diagnose_transformed_request(**kwargs)
    assert state["identity_calls"] == 0
    assert state["http_calls"] == []
