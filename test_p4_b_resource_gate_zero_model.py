"""Pre-send B gate contracts; no real provider, Web, Safari, or private DB."""

from concurrent.futures import ThreadPoolExecutor
import json
from types import SimpleNamespace

import pytest

import uruha_compute_ledger as ucl
import uruha_compact_planner_p2 as compact
from uruha_compact_planner_p2 import _REQUIRED_JSON_SCHEMA_FORMAT
from uruha_p4_b_resource_gate import P4BResourceGate, P4BResourceGateError


class _Completions:
    def __init__(self, *, usage=True, usage_values=(100, 40, 140)):
        self.calls = 0
        self.usage = usage
        self.usage_values = usage_values
        self.last_request = None

    def create(self, **kwargs):
        self.calls += 1
        self.last_request = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="{}"))],
            usage=(SimpleNamespace(prompt_tokens=self.usage_values[0],
                                   completion_tokens=self.usage_values[1],
                                   total_tokens=self.usage_values[2])
                   if self.usage else None),
        )


def _client(ledger, *, usage=True, usage_values=(100, 40, 140)):
    completions = _Completions(usage=usage, usage_values=usage_values)
    raw = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return ucl.instrument_openai_client(raw, ledger), completions


def _m21_request():
    return {
        "model": "qwen2.5:7b",
        "messages": [{"role": "system", "content": "You are the Left Brain Planner for a dual-brain character system. Private constraints"},
                     {"role": "user", "content": "User Input: private user"}],
        "temperature": 0.1,
        "timeout": 20.0,
        "max_tokens": 256,
        "response_format": _REQUIRED_JSON_SCHEMA_FORMAT,
    }


def test_only_first_m21_attempt_reaches_provider_and_gate_is_atomic():
    gate = P4BResourceGate(prompt_token_upper_bound=lambda request: 1200)
    ledger = ucl.ComputeLedger(p4_b_resource_gate=gate)
    client, target = _client(ledger)
    with ledger.stage("leftbrain_general_plan"):
        client.chat.completions.create(**_m21_request())
        with pytest.raises(P4BResourceGateError, match="extra_generation_attempt"):
            client.chat.completions.create(**_m21_request())
    assert target.calls == 1
    assert ledger.snapshot()["summary"]["generative_call_count"] == 1
    assert gate.snapshot()["attempted_provider_calls"] == 1
    assert gate.snapshot()["denied_attempt_count"] == 1


@pytest.mark.parametrize("stage", ["leftbrain_literal_topic_projection_m29", "unscoped"])
def test_other_stage_is_denied_before_provider_and_poisoned(stage):
    gate = P4BResourceGate(prompt_token_upper_bound=lambda request: 1200)
    ledger = ucl.ComputeLedger(p4_b_resource_gate=gate)
    client, target = _client(ledger)
    with ledger.stage(stage):
        with pytest.raises(P4BResourceGateError, match="unexpected_generation_stage"):
            client.chat.completions.create(**_m21_request())
    with ledger.stage("leftbrain_general_plan"):
        with pytest.raises(P4BResourceGateError):
            client.chat.completions.create(**_m21_request())
    assert target.calls == 0


@pytest.mark.parametrize("bound,reason", [
    (None, "prompt_upper_bound_unavailable"),
    (1745, "token_budget_exceeded"),
    (-1, "prompt_upper_bound_unavailable"),
    (True, "prompt_upper_bound_unavailable"),
])
def test_unproved_or_over_budget_prompt_is_denied_before_provider(bound, reason):
    gate = P4BResourceGate(prompt_token_upper_bound=(None if bound is None else lambda request: bound))
    ledger = ucl.ComputeLedger(p4_b_resource_gate=gate)
    client, target = _client(ledger)
    with ledger.stage("leftbrain_general_plan"):
        with pytest.raises(P4BResourceGateError, match=reason):
            client.chat.completions.create(**_m21_request())
    assert target.calls == 0


@pytest.mark.parametrize("field,value", [
    ("model", "qwen2.5:3b"),
    ("max_tokens", 257),
    ("temperature", 0.2),
    ("response_format", {"type": "json_object"}),
])
def test_request_drift_is_denied_before_provider(field, value):
    gate = P4BResourceGate(prompt_token_upper_bound=lambda request: 1200)
    ledger = ucl.ComputeLedger(p4_b_resource_gate=gate)
    client, target = _client(ledger)
    request = _m21_request()
    request[field] = value
    with ledger.stage("leftbrain_general_plan"):
        with pytest.raises(P4BResourceGateError, match="m21_request_drift"):
            client.chat.completions.create(**request)
    assert target.calls == 0


@pytest.mark.parametrize("extra,value", [
    ("stream", True),
    ("n", 4),
    ("tools", [{"type": "function"}]),
    ("max_completion_tokens", 1024),
])
def test_extra_generation_kwargs_are_denied_before_provider(extra, value):
    gate = P4BResourceGate(prompt_token_upper_bound=lambda request: 1200)
    ledger = ucl.ComputeLedger(p4_b_resource_gate=gate)
    client, target = _client(ledger)
    request = _m21_request()
    request[extra] = value
    with ledger.stage("leftbrain_general_plan"):
        with pytest.raises(P4BResourceGateError, match="m21_request_drift"):
            client.chat.completions.create(**request)
    assert target.calls == 0


@pytest.mark.parametrize("messages", [
    [{"role": "user", "content": "User Input: private user"}],
    [{"role": "system", "content": "private system"}, {"role": "user", "content": "User Input: private user"}],
    [{"role": "system", "content": "You are the Left Brain Planner for a dual-brain character system."},
     {"role": "tool", "content": "User Input: private user"}],
    [{"role": "system", "content": "You are the Left Brain Planner for a dual-brain character system."},
     {"role": "user", "content": "private user"}],
])
def test_non_m21_message_shape_is_denied(messages):
    gate = P4BResourceGate(prompt_token_upper_bound=lambda request: 1200)
    ledger = ucl.ComputeLedger(p4_b_resource_gate=gate)
    client, target = _client(ledger)
    request = _m21_request()
    request["messages"] = messages
    with ledger.stage("leftbrain_general_plan"):
        with pytest.raises(P4BResourceGateError, match="m21_request_drift"):
            client.chat.completions.create(**request)
    assert target.calls == 0


@pytest.mark.parametrize("timeout", [0, 20.1, float("inf"), "20"])
def test_planner_timeout_shape_drift_is_denied(timeout):
    gate = P4BResourceGate(prompt_token_upper_bound=lambda request: 1200)
    ledger = ucl.ComputeLedger(p4_b_resource_gate=gate)
    client, target = _client(ledger)
    request = _m21_request()
    request["timeout"] = timeout
    with ledger.stage("leftbrain_general_plan"):
        with pytest.raises(P4BResourceGateError, match="m21_request_drift"):
            client.chat.completions.create(**request)
    assert target.calls == 0


def test_missing_usage_marks_terminal_even_after_first_provider_return():
    gate = P4BResourceGate(prompt_token_upper_bound=lambda request: 1200)
    ledger = ucl.ComputeLedger(p4_b_resource_gate=gate)
    client, target = _client(ledger, usage=False)
    with ledger.stage("leftbrain_general_plan"):
        with pytest.raises(P4BResourceGateError, match="missing_provider_usage"):
            client.chat.completions.create(**_m21_request())
    assert target.calls == 1
    assert gate.snapshot()["terminal_reason"] == "missing_provider_usage"
    assert gate.snapshot()["actual_total_tokens"] is None
    assert ledger.snapshot()["call_count"] == 1
    assert ledger.snapshot()["summary"]["generative_token_accounting_complete"] is False


@pytest.mark.parametrize("usage_values,reason", [
    ((1201, 40, 1241), "actual_prompt_exceeded_upper_bound"),
    ((100, 257, 357), "actual_completion_exceeded_output_cap"),
    ((1200, 801, 2001), "actual_completion_exceeded_output_cap"),
])
def test_posthoc_usage_drift_is_terminal(usage_values, reason):
    gate = P4BResourceGate(prompt_token_upper_bound=lambda request: 1200)
    ledger = ucl.ComputeLedger(p4_b_resource_gate=gate)
    client, target = _client(ledger, usage_values=usage_values)
    with ledger.stage("leftbrain_general_plan"):
        with pytest.raises(P4BResourceGateError, match=reason):
            client.chat.completions.create(**_m21_request())
    assert target.calls == 1
    assert gate.snapshot()["terminal_reason"] == reason
    assert gate.snapshot()["actual_total_tokens"] == usage_values[2]
    assert ledger.snapshot()["call_count"] == 1
    assert ledger.snapshot()["calls"][0]["response"]["total_tokens"] == usage_values[2]


def test_non_b_missing_usage_still_returns_without_gate():
    ledger = ucl.ComputeLedger()
    client, target = _client(ledger, usage=False)
    with ledger.stage("leftbrain_general_plan"):
        response = client.chat.completions.create(**_m21_request())
    assert response is not None
    assert target.calls == 1
    assert ledger.snapshot()["call_count"] == 1
    assert ledger.snapshot()["summary"]["generative_token_accounting_complete"] is False


def test_token_counter_cannot_mutate_real_transformed_request():
    def mutating_counter(request):
        request["messages"][1]["content"] = "tampered"
        request["response_format"]["type"] = "json_object"
        return 1200

    gate = P4BResourceGate(prompt_token_upper_bound=mutating_counter)
    ledger = ucl.ComputeLedger(p4_b_resource_gate=gate)
    client, target = _client(ledger)
    request = _m21_request()
    with ledger.stage("leftbrain_general_plan"):
        client.chat.completions.create(**request)
    assert target.last_request["messages"][1]["content"] == "User Input: private user"
    assert target.last_request["response_format"]["type"] == "json_schema"


def test_native_and_local_generation_are_denied_before_their_model_entry(monkeypatch):
    from uruha_brain_mac import LeftBrain, RightBrain

    gate = P4BResourceGate(prompt_token_upper_bound=lambda request: 1200)
    ledger = ucl.ComputeLedger(p4_b_resource_gate=gate)
    left = LeftBrain.__new__(LeftBrain)
    left.compute_ledger = ledger
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: pytest.fail("native_provider_called"))
    with pytest.raises(P4BResourceGateError, match="unexpected_generation_backend"):
        left._native_semantic_authorizer_m31("private prompt")

    other_gate = P4BResourceGate(prompt_token_upper_bound=lambda request: 1200)
    right = RightBrain.__new__(RightBrain)
    right.compute_ledger = ucl.ComputeLedger(p4_b_resource_gate=other_gate)
    with pytest.raises(P4BResourceGateError, match="unexpected_generation_backend"):
        right._generate_model_text([{"role": "user", "content": "private"}], {})


def test_default_ledger_is_unchanged_without_opt_in():
    ledger = ucl.ComputeLedger()
    client, target = _client(ledger)
    with ledger.stage("leftbrain_literal_topic_projection_m29"):
        client.chat.completions.create(**_m21_request())
        client.chat.completions.create(**_m21_request())
    assert target.calls == 2


def test_parallel_attempts_cannot_both_enter_provider():
    gate = P4BResourceGate(prompt_token_upper_bound=lambda request: 1200)
    ledger = ucl.ComputeLedger(p4_b_resource_gate=gate)
    client, target = _client(ledger)

    def attempt(_):
        with ledger.stage("leftbrain_general_plan"):
            try:
                client.chat.completions.create(**_m21_request())
            except P4BResourceGateError:
                return "denied"
            return "sent"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, range(2)))
    assert sorted(outcomes) == ["denied", "sent"]
    assert target.calls == 1


@pytest.mark.parametrize("extra", [None, "stream"])
def test_p2_compact_outer_proxy_reaches_inner_gate_after_transform(monkeypatch, extra):
    class CompactCompletions(_Completions):
        def create(self, **kwargs):
            result = super().create(**kwargs)
            result.choices[0].message.content = json.dumps({"plans": [
                {"scene": "casual", "core_message_jp": text,
                 "response_mode": "direct_answer"}
                for text in ("うん。", "そっか。", "それでいこう。")
            ]}, ensure_ascii=False)
            result.choices[0].finish_reason = "stop"
            return result

    monkeypatch.setenv("URUHA_P4_COMPACT_JSON_SCHEMA", "1")
    gate = P4BResourceGate(prompt_token_upper_bound=lambda request: 1200)
    ledger = ucl.ComputeLedger(p4_b_resource_gate=gate)
    completions = CompactCompletions()
    raw = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    outer = compact._Proxy(ucl.instrument_openai_client(raw, ledger))
    original = _m21_request()
    original["messages"][0]["content"] += "\n[Output JSON schema]old verbose fields"
    del original["max_tokens"]
    del original["response_format"]
    if extra is not None:
        original[extra] = True
    token = compact._CALL.set({})
    try:
        with ledger.stage("leftbrain_general_plan"):
            if extra is not None:
                with pytest.raises(P4BResourceGateError, match="m21_request_drift"):
                    outer.chat.completions.create(**original)
                assert completions.calls == 0
            else:
                response = outer.chat.completions.create(**original)
                assert "candidate_plans" in response.choices[0].message.content
                assert completions.calls == 1
                assert completions.last_request["max_tokens"] == 256
                assert completions.last_request["response_format"] == compact._REQUIRED_JSON_SCHEMA_FORMAT
                assert ledger.snapshot()["summary"]["generative_call_count"] == 1
                assert gate.snapshot()["attempted_provider_calls"] == 1
    finally:
        compact._CALL.reset(token)
