"""No-provider contracts for the B-only product Web and inner ledger seam.

These do not authorize a B Send, establish token parity, or exercise Safari.
"""

import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

import uruha_compute_ledger as ucl
import uruha_compact_planner_p2 as compact
import uruha_web_ui as web
from uruha_compact_planner_p2 import _REQUIRED_JSON_SCHEMA_FORMAT
from uruha_p4_b_resource_gate import P4BResourceGate, P4BResourceGateError


@pytest.mark.parametrize("intent", [
    {"URUHA_P4_B_PRIVATE_CHILD": "0"},
    {"URUHA_P4_B_RUN_ID": "missing-marker"},
    {"uruha_p4_b_private_child": "1"},
])
def test_bad_b_intent_rejected_before_fixed_entry_imports_web_or_creates_logs(
        tmp_path, intent):
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("URUHA_P4_B_")}
    env.update(intent)
    env["URUHA_WEB_LOG_JSONL_PATH"] = str(tmp_path / "web_logs" / "conversation.jsonl")
    env["URUHA_WEB_LOG_TXT_PATH"] = str(tmp_path / "web_logs" / "conversation.txt")
    code = (
        "import importlib,json,sys\n"
        "try:\n"
        " importlib.import_module('uruha_web_ui_product_p4_preference_fallback')\n"
        "except Exception as exc:\n"
        " print(json.dumps({'error':type(exc).__name__,"
        "'web_loaded':'uruha_web_ui' in sys.modules}))\n"
        "else:\n"
        " print(json.dumps({'error':None,"
        "'web_loaded':'uruha_web_ui' in sys.modules}))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=Path(__file__).resolve().parent,
        env=env, text=True, capture_output=True, timeout=15, check=True,
    )
    observed = json.loads(result.stdout.strip().splitlines()[-1])
    assert observed["error"] is not None
    assert observed["web_loaded"] is False
    assert not (tmp_path / "web_logs").exists()


def test_web_runtime_uses_same_closed_gate_ledger_and_private_constructor(monkeypatch):
    ledger = ucl.ComputeLedger(p4_b_resource_gate=P4BResourceGate())
    binding = object()
    state = SimpleNamespace(
        compute_ledger=ledger, resource_gate=ledger.p4_b_resource_gate,
        binding=binding, run_id="test-run",
    )
    calls = []
    monkeypatch.setattr(web, "_P4_B_PRIVATE_BOOT_STATE", state)
    monkeypatch.setattr(web, "get_private_child_boot_state", lambda: state)
    monkeypatch.setattr(web, "WEB_COMPUTE_LEDGER_ENABLED", True)
    monkeypatch.setattr(web, "WEB_ACTIVE_DB_RECEIPT_PATH", "")
    monkeypatch.setattr(web, "WEB_TURN_ADMISSION_JOURNAL_PATH", "")
    monkeypatch.setattr(web.RuntimeManager, "_idle_consolidation_loop", lambda self: None)
    monkeypatch.setattr(web, "UruhaBrainV4_Mac", lambda **kwargs: calls.append(kwargs) or object())
    runtime = web.RuntimeManager()
    runtime.get_brain()
    assert runtime._compute_ledger is state.compute_ledger
    assert calls == [{
        "compute_ledger": ledger,
        "p4_b_private_mode": True,
        "p4_b_private_binding": binding,
        "p4_b_run_id": "test-run",
    }]
    assert ledger.p4_b_resource_gate.snapshot()["attempted_provider_calls"] == 0
    assert ledger.p4_b_resource_gate._prompt_token_upper_bound is None


def test_web_b_intent_rejects_disabled_ledger_before_runtime_thread(monkeypatch):
    ledger = ucl.ComputeLedger(p4_b_resource_gate=P4BResourceGate())
    monkeypatch.setattr(web, "_P4_B_PRIVATE_BOOT_STATE", SimpleNamespace(
        compute_ledger=ledger, resource_gate=ledger.p4_b_resource_gate,
    ))
    monkeypatch.setattr(web, "get_private_child_boot_state", lambda: web._P4_B_PRIVATE_BOOT_STATE)
    monkeypatch.setattr(web, "WEB_COMPUTE_LEDGER_ENABLED", False)
    with pytest.raises(RuntimeError, match="ledger_disabled"):
        web.RuntimeManager()


def test_web_refuses_boot_state_drift_before_runtime_side_effects(monkeypatch):
    ledger = ucl.ComputeLedger(p4_b_resource_gate=P4BResourceGate())
    state = SimpleNamespace(compute_ledger=ledger, resource_gate=ledger.p4_b_resource_gate)
    monkeypatch.setattr(web, "_P4_B_PRIVATE_BOOT_STATE", state)
    monkeypatch.setattr(web, "get_private_child_boot_state", lambda: None)
    with pytest.raises(RuntimeError, match="boot_state_changed"):
        web.RuntimeManager()


def _fake_client(ledger, events):
    class Completion:
        def create(self, **_kwargs):
            events.append("provider")
            return SimpleNamespace(usage=SimpleNamespace(
                prompt_tokens=1, completion_tokens=1, total_tokens=2,
            ))

    client = SimpleNamespace(chat=SimpleNamespace(completions=Completion()))
    return ucl.instrument_openai_client(client, ledger)


def _valid_m21_request():
    return {
        "model": "qwen2.5:7b",
        "messages": [
            {"role": "system", "content": "You are the Left Brain Planner for a dual-brain character system."},
            {"role": "user", "content": "User Input: isolated fake"},
        ],
        "temperature": 0.1,
        "timeout": 20.0,
        "max_tokens": 256,
        "response_format": _REQUIRED_JSON_SCHEMA_FORMAT,
    }


def test_private_identity_rechecked_before_gate_and_fake_provider(monkeypatch):
    boot = importlib.import_module("uruha_p4_b_private_child_bootstrap")
    events = []
    gate = P4BResourceGate(prompt_token_upper_bound=lambda _request: 1)
    ledger = ucl.ComputeLedger(p4_b_resource_gate=gate)
    state = SimpleNamespace(compute_ledger=ledger, resource_gate=gate)
    monkeypatch.setattr(boot, "get_private_child_boot_state", lambda: state)
    monkeypatch.setattr(boot, "revalidate_private_child_before_create", lambda _state: events.append("identity"))
    original_admit = gate.admit_openai
    monkeypatch.setattr(gate, "admit_openai", lambda stage, request: (
        events.append("gate"), original_admit(stage, request)
    ))
    with ledger.stage("leftbrain_general_plan"):
        _fake_client(ledger, events).chat.completions.create(**_valid_m21_request())
    assert events == ["identity", "gate", "identity", "provider"]
    assert gate.snapshot()["actual_total_tokens"] == 2
    assert gate.snapshot()["terminal_reason"] == ""
    assert ledger.snapshot()["call_count"] == 1


def test_private_identity_drift_or_bare_ledger_never_reaches_provider(monkeypatch):
    boot = importlib.import_module("uruha_p4_b_private_child_bootstrap")
    events = []
    gate = P4BResourceGate()
    ledger = ucl.ComputeLedger(p4_b_resource_gate=gate)
    state = SimpleNamespace(compute_ledger=ledger, resource_gate=gate)
    monkeypatch.setattr(boot, "get_private_child_boot_state", lambda: state)

    def drift(_state):
        events.append("identity")
        raise RuntimeError("private_identity_drift")

    monkeypatch.setattr(boot, "revalidate_private_child_before_create", drift)
    with pytest.raises(RuntimeError, match="private_identity_drift"):
        _fake_client(ledger, events).chat.completions.create(model="fake")
    assert events == ["identity"]
    assert gate.snapshot()["attempted_provider_calls"] == 0
    assert gate.snapshot()["terminal_reason"] == ""
    assert ledger.snapshot()["call_count"] == 0
    bare = ucl.ComputeLedger()
    monkeypatch.setattr(boot, "get_private_child_boot_state", lambda: None)
    monkeypatch.setenv("URUHA_P4_B_PRIVATE_CHILD", "1")
    with pytest.raises(RuntimeError):
        _fake_client(bare, events).chat.completions.create(model="fake")
    assert events == ["identity"]


def test_gate_replacement_or_drift_during_admission_blocks_fake_provider(monkeypatch):
    boot = importlib.import_module("uruha_p4_b_private_child_bootstrap")
    events = []
    gate = P4BResourceGate()
    ledger = ucl.ComputeLedger(p4_b_resource_gate=gate)
    state = SimpleNamespace(compute_ledger=ledger, resource_gate=gate)
    monkeypatch.setattr(boot, "get_private_child_boot_state", lambda: state)
    monkeypatch.setattr(boot, "revalidate_private_child_before_create", lambda _state: events.append("identity"))
    ledger.p4_b_resource_gate = P4BResourceGate()
    with pytest.raises(RuntimeError, match="ledger_mismatch"):
        _fake_client(ledger, events).chat.completions.create(model="fake")
    assert events == []

    ledger.p4_b_resource_gate = gate
    def admission(_stage, _request):
        events.append("gate")
    monkeypatch.setattr(gate, "admit_openai", admission)
    def identity(_state):
        events.append("identity")
        if events.count("identity") == 2:
            raise RuntimeError("receipt_revoked_after_admission")
    monkeypatch.setattr(boot, "revalidate_private_child_before_create", identity)
    with pytest.raises(RuntimeError, match="receipt_revoked_after_admission"):
        _fake_client(ledger, events).chat.completions.create(model="fake")
    assert events == ["identity", "gate", "identity"]


def test_post_admission_identity_failure_is_gate_terminal_without_provider_usage(monkeypatch):
    boot = importlib.import_module("uruha_p4_b_private_child_bootstrap")
    events = []
    gate = P4BResourceGate(prompt_token_upper_bound=lambda _request: 1)
    ledger = ucl.ComputeLedger(p4_b_resource_gate=gate)
    state = SimpleNamespace(compute_ledger=ledger, resource_gate=gate)
    monkeypatch.setattr(boot, "get_private_child_boot_state", lambda: state)

    def identity(_state):
        events.append("identity")
        if events.count("identity") == 2:
            raise RuntimeError("synthetic_second_revalidation_failure")

    monkeypatch.setattr(boot, "revalidate_private_child_before_create", identity)
    client = _fake_client(ledger, events)
    with ledger.stage("leftbrain_general_plan"):
        with pytest.raises(RuntimeError, match="synthetic_second_revalidation_failure"):
            client.chat.completions.create(**_valid_m21_request())
    assert events == ["identity", "identity"]
    assert gate.snapshot() == {
        "schema": "uruha_p4_b_resource_gate_mechanical_v1",
        "attempted_provider_calls": 1,
        "denied_attempt_count": 0,
        "admitted_prompt_upper_bound": 1,
        "actual_total_tokens": None,
        "terminal_reason": "pre_provider_revalidation_failed",
        "contains_raw_prompt_or_reply": False,
    }
    assert ledger.snapshot()["call_count"] == 0
    with ledger.stage("leftbrain_general_plan"):
        with pytest.raises(P4BResourceGateError, match="pre_provider_revalidation_failed"):
            client.chat.completions.create(**_valid_m21_request())
    assert events == ["identity", "identity", "identity"]
    assert gate.snapshot()["denied_attempt_count"] == 1
    assert gate.snapshot()["admitted_prompt_upper_bound"] == 1
    assert gate.snapshot()["actual_total_tokens"] is None
    assert ledger.snapshot()["call_count"] == 0


def test_compact_transformation_reaches_post_admission_abort_without_provider(monkeypatch):
    boot = importlib.import_module("uruha_p4_b_private_child_bootstrap")
    monkeypatch.setenv("URUHA_P4_COMPACT_JSON_SCHEMA", "1")
    events = []
    gate = P4BResourceGate(prompt_token_upper_bound=lambda _request: 1)
    ledger = ucl.ComputeLedger(p4_b_resource_gate=gate)
    state = SimpleNamespace(compute_ledger=ledger, resource_gate=gate)
    monkeypatch.setattr(boot, "get_private_child_boot_state", lambda: state)

    def identity(_state):
        events.append("identity")
        if events.count("identity") == 2:
            raise RuntimeError("synthetic_second_revalidation_failure")

    monkeypatch.setattr(boot, "revalidate_private_child_before_create", identity)
    original = _valid_m21_request()
    original["messages"][0]["content"] += "\n[Output JSON schema]old verbose fields"
    del original["max_tokens"]
    del original["response_format"]
    outer = compact._Proxy(_fake_client(ledger, events))
    audit = {}
    token = compact._CALL.set(audit)
    try:
        with ledger.stage("leftbrain_general_plan"):
            with pytest.raises(RuntimeError, match="synthetic_second_revalidation_failure"):
                outer.chat.completions.create(**original)
    finally:
        compact._CALL.reset(token)
    assert audit["attempted"] is True
    assert audit["completed"] is False
    assert events == ["identity", "identity"]
    assert gate.snapshot()["admitted_prompt_upper_bound"] == 1
    assert gate.snapshot()["terminal_reason"] == "pre_provider_revalidation_failed"
    assert gate.snapshot()["actual_total_tokens"] is None
    assert ledger.snapshot()["call_count"] == 0


def test_pre_provider_abort_cannot_fabricate_terminal_without_admission():
    gate = P4BResourceGate(prompt_token_upper_bound=lambda _request: 1)
    gate.record_pre_provider_revalidation_failure()
    assert gate.snapshot()["attempted_provider_calls"] == 0
    assert gate.snapshot()["terminal_reason"] == ""


def test_gate_denial_is_not_reclassified_as_post_admission_failure(monkeypatch):
    boot = importlib.import_module("uruha_p4_b_private_child_bootstrap")
    events = []
    gate = P4BResourceGate()
    ledger = ucl.ComputeLedger(p4_b_resource_gate=gate)
    state = SimpleNamespace(compute_ledger=ledger, resource_gate=gate)
    monkeypatch.setattr(boot, "get_private_child_boot_state", lambda: state)
    monkeypatch.setattr(boot, "revalidate_private_child_before_create",
                        lambda _state: events.append("identity"))
    with ledger.stage("leftbrain_general_plan"):
        with pytest.raises(P4BResourceGateError, match="prompt_upper_bound_unavailable"):
            _fake_client(ledger, events).chat.completions.create(**_valid_m21_request())
    assert events == ["identity"]
    assert gate.snapshot()["attempted_provider_calls"] == 0
    assert gate.snapshot()["terminal_reason"] == "prompt_upper_bound_unavailable"
    assert ledger.snapshot()["call_count"] == 0


def test_provider_failure_keeps_provider_error_and_physical_ledger_call(monkeypatch):
    boot = importlib.import_module("uruha_p4_b_private_child_bootstrap")
    events = []
    gate = P4BResourceGate(prompt_token_upper_bound=lambda _request: 1)
    ledger = ucl.ComputeLedger(p4_b_resource_gate=gate)
    state = SimpleNamespace(compute_ledger=ledger, resource_gate=gate)
    monkeypatch.setattr(boot, "get_private_child_boot_state", lambda: state)
    monkeypatch.setattr(boot, "revalidate_private_child_before_create",
                        lambda _state: events.append("identity"))

    class FailingCompletion:
        def create(self, **_kwargs):
            events.append("provider")
            raise RuntimeError("synthetic_provider_failure")

    raw = SimpleNamespace(chat=SimpleNamespace(completions=FailingCompletion()))
    client = ucl.instrument_openai_client(raw, ledger)
    with ledger.stage("leftbrain_general_plan"):
        with pytest.raises(RuntimeError, match="synthetic_provider_failure"):
            client.chat.completions.create(**_valid_m21_request())
    assert events == ["identity", "identity", "provider"]
    assert gate.snapshot()["terminal_reason"] == "provider_error_or_missing_usage"
    assert gate.snapshot()["actual_total_tokens"] is None
    assert ledger.snapshot()["call_count"] == 1
    assert ledger.snapshot()["calls"][0]["error_type"] == "RuntimeError"
