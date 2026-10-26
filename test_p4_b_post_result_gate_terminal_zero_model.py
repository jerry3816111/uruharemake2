"""Fake post-provider B terminal through compact M21, Brain and Web.

No real model, service, Safari or production memory database is used.
"""

import json
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

import uruha_brain_mac as brain_runtime
import uruha_compute_ledger as ucl
import uruha_compact_planner_p2 as compact
import uruha_web_ui as web
from test_personhood_loop_v2_13 import _IsolatedContractBrain
from test_p4_product_turn_compute_receipt import _FakeRuntime, _private_web_log
from uruha_p4_b_resource_gate import P4BResourceGate, P4BResourceGateError


INPUT = "I have several conflicting goals and need to reason through them."


class _FakeMissingUsageCompletion:
    def __init__(self):
        self.calls = 0
        self.last_request = None

    def create(self, **kwargs):
        self.calls += 1
        self.last_request = kwargs
        payload = {"plans": [
            {"scene": "casual", "core_message_jp": text, "response_mode": "direct_answer"}
            for text in ("一つずつ整理しよ。", "急がなくていい。", "先に大事な方を見よ。")
        ]}
        return SimpleNamespace(
            choices=[SimpleNamespace(
                message=SimpleNamespace(content=json.dumps(payload, ensure_ascii=False)),
                finish_reason="stop",
            )],
            usage=None,
        )


@contextmanager
def _compact_call():
    token = compact._CALL.set({})
    try:
        yield
    finally:
        compact._CALL.reset(token)


def _isolated_b_brain(monkeypatch):
    monkeypatch.setenv("URUHA_P4_COMPACT_JSON_SCHEMA", "1")
    monkeypatch.setattr(brain_runtime, "LEFT_BRAIN_SLOW_PATH_BUDGET_SECONDS", 20.0)
    brain = _IsolatedContractBrain()
    original_literal_candidate = brain_runtime.uapm.build_literal_topic_projection_candidate_m29
    monkeypatch.setattr(
        brain_runtime.uapm, "build_literal_topic_projection_candidate_m29",
        lambda *args: {**original_literal_candidate(*args), "projection_required": False},
    )
    gate = P4BResourceGate(prompt_token_upper_bound=lambda _request: 1200)
    ledger = ucl.ComputeLedger(p4_b_resource_gate=gate)
    provider = _FakeMissingUsageCompletion()
    raw = SimpleNamespace(chat=SimpleNamespace(completions=provider))
    brain.compute_ledger = ledger
    brain.left_brain = brain_runtime.LeftBrain(
        compact._Proxy(ucl.instrument_openai_client(raw, ledger)),
        compute_ledger=ledger,
        p4_b_private_mode=True,
    )
    monkeypatch.setattr(brain.left_brain, "_native_semantic_authorizer_m31",
                        lambda *_args: pytest.fail("unexpected_native_semantic_provider"))
    monkeypatch.setattr(brain.left_brain, "_rule_based_plan", lambda *_args: None)
    return brain, ledger, gate, provider


def test_missing_usage_fails_closed_after_one_fake_compact_provider_call(monkeypatch):
    brain, ledger, gate, provider = _isolated_b_brain(monkeypatch)
    with pytest.raises(P4BResourceGateError, match="missing_provider_usage"):
        with _compact_call():
            brain.run_turn_debug(INPUT)
    assert provider.calls == 1
    assert provider.last_request["max_tokens"] == 256
    assert provider.last_request["response_format"]["type"] == "json_schema"
    assert gate.snapshot()["terminal_reason"] == "missing_provider_usage"
    assert gate.snapshot()["actual_total_tokens"] is None
    snapshot = ledger.snapshot()
    assert snapshot["call_count"] == 1
    assert snapshot["summary"]["generative_call_count"] == 1
    assert snapshot["summary"]["generative_token_accounting_complete"] is False
    assert brain.memory.saved_episodes == []
    assert brain.runtime.last_reply in (None, "")


def test_missing_usage_web_failure_receipt_records_physical_call_without_reply(
        monkeypatch, tmp_path):
    log_dir = _private_web_log(monkeypatch, tmp_path)
    brain, ledger, gate, provider = _isolated_b_brain(monkeypatch)
    runtime = _FakeRuntime(ledger, [])
    runtime._brain = brain
    monkeypatch.setattr(web, "RUNTIME", runtime)
    with pytest.raises(P4BResourceGateError, match="missing_provider_usage"):
        with _compact_call():
            web._run_turn(INPUT, auto_tts=False)
    assert provider.calls == 1
    assert gate.snapshot()["terminal_reason"] == "missing_provider_usage"
    path = log_dir / "compute_failures.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    receipt = rows[0]
    assert receipt["status"] == "terminal_error"
    assert receipt["terminal_error_type"] == "P4BResourceGateError"
    assert receipt["snapshot"]["summary"]["generative_call_count"] == 1
    assert receipt["snapshot"]["summary"]["generative_token_accounting_complete"] is False
    assert INPUT not in json.dumps(receipt, ensure_ascii=False)
    assert path.stat().st_mode & 0o777 == 0o600
    assert not (log_dir / "conversation.jsonl").exists()
    assert brain.memory.saved_episodes == []


def test_actual_compact_m21_single_newline_prefix_is_admitted_unchanged(monkeypatch):
    brain, ledger, gate, provider = _isolated_b_brain(monkeypatch)
    observed = {}
    original_admit = gate.admit_openai

    def admit(stage, request):
        observed["stage"] = stage
        observed["system"] = request["messages"][0]["content"]
        observed["format_type"] = request["response_format"]["type"]
        return original_admit(stage, request)

    monkeypatch.setattr(gate, "admit_openai", admit)
    with pytest.raises(P4BResourceGateError, match="missing_provider_usage"):
        with _compact_call():
            brain.run_turn_debug(INPUT)
    assert observed["stage"] == "leftbrain_general_plan"
    assert observed["system"].startswith(
        "\nYou are the Left Brain Planner for a dual-brain character system."
    )
    assert observed["format_type"] == "json_schema"
    assert provider.calls == 1
    assert provider.last_request["messages"][0]["content"] == observed["system"]
    assert ledger.snapshot()["call_count"] == 1
    assert gate.snapshot()["terminal_reason"] == "missing_provider_usage"
    assert brain.memory.saved_episodes == []
