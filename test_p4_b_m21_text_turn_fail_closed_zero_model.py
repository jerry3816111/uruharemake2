"""Isolated B text-turn failures: no model, service, Safari or production DB."""

import json
from types import SimpleNamespace

import pytest

import uruha_brain_mac as brain_runtime
import uruha_web_ui as web
from test_personhood_loop_v2_13 import _IsolatedContractBrain
from test_p4_product_turn_compute_receipt import _FakeRuntime, _private_web_log
from uruha_compute_ledger import ComputeLedger
from uruha_p4_b_private_endpoint_binding import PrivateEndpointBindingError
from uruha_p4_b_resource_gate import P4BResourceGate, P4BResourceGateError


INPUT = "I have several conflicting goals and need to reason through them."


class _FailingCompletion:
    def __init__(self, error):
        self.error = error
        self.calls = 0

    def create(self, **_kwargs):
        self.calls += 1
        raise self.error


def _contract_brain(monkeypatch, error, *, private_mode=True, gate=True):
    brain = _IsolatedContractBrain()
    original_literal_candidate = brain_runtime.uapm.build_literal_topic_projection_candidate_m29
    monkeypatch.setattr(
        brain_runtime.uapm, "build_literal_topic_projection_candidate_m29",
        lambda *args: {**original_literal_candidate(*args), "projection_required": False},
    )
    resource_gate = P4BResourceGate() if gate else None
    ledger = ComputeLedger(p4_b_resource_gate=resource_gate)
    completion = _FailingCompletion(error)
    brain.compute_ledger = ledger
    left_kwargs = {"compute_ledger": ledger}
    if private_mode:
        left_kwargs["p4_b_private_mode"] = True
    brain.left_brain = brain_runtime.LeftBrain(
        SimpleNamespace(chat=SimpleNamespace(completions=completion)),
        **left_kwargs,
    )
    monkeypatch.setattr(brain.left_brain, "_native_semantic_authorizer_m31",
                        lambda *_args: pytest.fail("unexpected_native_semantic_provider"))
    monkeypatch.setattr(brain.left_brain, "_rule_based_plan", lambda *_args: None)
    return brain, ledger, completion


@pytest.mark.parametrize("error", [
    P4BResourceGateError("prompt_upper_bound_unavailable"),
    PrivateEndpointBindingError("synthetic_private_identity_drift"),
])
def test_private_m21_error_propagates_before_reply_or_episode(monkeypatch, capsys, error):
    brain, _ledger, completion = _contract_brain(monkeypatch, error)
    with pytest.raises(type(error), match=str(error)):
        brain.run_turn_debug(INPUT)
    assert completion.calls == 1
    assert brain.memory.saved_episodes == []
    assert brain.runtime.last_reply in (None, "")
    assert str(error) not in capsys.readouterr().out


@pytest.mark.parametrize("replacement", [None, P4BResourceGate()])
def test_private_mode_survives_gate_drop_or_swap(monkeypatch, replacement):
    error = PrivateEndpointBindingError("synthetic_private_identity_drift")
    brain, ledger, _completion = _contract_brain(monkeypatch, error)
    ledger.p4_b_resource_gate = replacement
    with pytest.raises(PrivateEndpointBindingError, match="synthetic_private_identity_drift"):
        brain.run_turn_debug(INPUT)
    assert brain.memory.saved_episodes == []


def test_ordinary_m21_transport_error_still_falls_back(monkeypatch):
    brain, _ledger, _completion = _contract_brain(
        monkeypatch, RuntimeError("synthetic_transport_error"),
        private_mode=False, gate=False,
    )
    result = brain.run_turn_debug(INPUT)
    assert result["logic"]["bounded_slow_path_m21"]["status"] == "error_fallback"
    assert result["reply"]
    assert len(brain.memory.saved_episodes) == 1


def test_gate_bearing_planner_without_private_constructor_flag_rethrows(monkeypatch):
    completion = _FailingCompletion(P4BResourceGateError("synthetic_gate_denial"))
    ledger = ComputeLedger(p4_b_resource_gate=P4BResourceGate())
    left = brain_runtime.LeftBrain(
        SimpleNamespace(chat=SimpleNamespace(completions=completion)),
        compute_ledger=ledger,
    )
    monkeypatch.setattr(left, "_rule_based_plan", lambda *_args: None)
    memory = {
        "working_memory_summary": "none", "procedural_guidance_summary": "none",
        "episodes": "none", "wisdom": "none", "profile": "none",
        "recent_dialogue": "none",
    }
    with pytest.raises(P4BResourceGateError, match="synthetic_gate_denial"):
        left.think(INPUT, memory, {"mood": 0, "trust": 50}, force_general_planner=True)
    assert completion.calls == 1


def test_private_m21_failure_reaches_private_web_failure_receipt(monkeypatch, tmp_path):
    log_dir = _private_web_log(monkeypatch, tmp_path)
    error = P4BResourceGateError("prompt_upper_bound_unavailable")
    brain, ledger, _completion = _contract_brain(monkeypatch, error)
    runtime = _FakeRuntime(ledger, [])
    runtime._brain = brain
    monkeypatch.setattr(web, "RUNTIME", runtime)
    with pytest.raises(P4BResourceGateError, match="prompt_upper_bound_unavailable"):
        web._run_turn(INPUT, auto_tts=False)
    rows = [json.loads(line) for line in
            (log_dir / "compute_failures.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    receipt = rows[0]
    assert receipt["status"] == "terminal_error"
    assert receipt["terminal_error_type"] == "P4BResourceGateError"
    assert receipt["snapshot"]["summary"]["generative_call_count"] == 0
    # The existing writer records that flag only in the in-memory return,
    # after serializing the file; the private 0600 file is the observable fact.
    assert INPUT not in json.dumps(receipt, ensure_ascii=False)
    assert (log_dir / "compute_failures.jsonl").stat().st_mode & 0o777 == 0o600
    assert not (log_dir / "conversation.jsonl").exists()
    assert brain.memory.saved_episodes == []


def test_private_web_failure_without_private_log_does_not_claim_written_receipt(
        monkeypatch, tmp_path):
    log_dir = _private_web_log(monkeypatch, tmp_path)
    log_dir.chmod(0o755)
    error = P4BResourceGateError("prompt_upper_bound_unavailable")
    brain, ledger, _completion = _contract_brain(monkeypatch, error)
    runtime = _FakeRuntime(ledger, [])
    runtime._brain = brain
    monkeypatch.setattr(web, "RUNTIME", runtime)
    with pytest.raises(P4BResourceGateError, match="prompt_upper_bound_unavailable"):
        web._run_turn(INPUT, auto_tts=False)
    assert not (log_dir / "compute_failures.jsonl").exists()
    assert not (log_dir / "conversation.jsonl").exists()
    assert brain.memory.saved_episodes == []


class _SubmissionRuntime:
    def __init__(self):
        self.finishes = []
        self.begins = 0

    def _admission_enabled(self):
        return True

    def begin_human_turn_with_token(self, *, source):
        self.begins += 1
        return 1.0, "a" * 32

    def finish_human_turn(self, **kwargs):
        self.finishes.append(kwargs)


def _submission_setup(monkeypatch, *, private=True):
    runtime = _SubmissionRuntime()
    monkeypatch.setattr(web, "RUNTIME", runtime)
    monkeypatch.setattr(web, "_P4_B_PRIVATE_BOOT_STATE", object() if private else None)
    monkeypatch.setattr(web, "_exact_input_surface_arm", lambda: "")
    monkeypatch.setattr(web, "_status_markdown", lambda: "synthetic status")
    return runtime


def test_private_browser_failure_never_adds_assistant_and_restores_input(monkeypatch):
    runtime = _submission_setup(monkeypatch)
    original = [{"role": "user", "content": "old"},
                {"role": "assistant", "content": "前の返事。"}]
    message = "  newest input  "
    monkeypatch.setattr(web, "_run_turn", lambda *_args, **_kwargs: (
        (_ for _ in ()).throw(RuntimeError("secret_private_error_731"))
    ))
    updates = list(web.submit_text_browser_bound(
        message, original, False, expected_session_id="isolated-session",
    ))
    assert all(len(update) == 14 for update in updates)
    assert all([row for row in update[0] if row["role"] == "assistant"]
               == [original[1]] for update in updates)
    assert updates[0][0][-1] == {"role": "user", "content": message.strip()}
    assert updates[-1][0] == original
    assert updates[-1][1] == original
    assert updates[-1][2] == message
    assert "思考中。" not in updates[-1][6]
    assert "等待本輪狀態完成。" not in updates[-1][7]
    assert "本輪處理未完成" in updates[-1][9]
    assert "secret_private_error_731" not in str(updates)
    assert runtime.finishes == [{"admission_token": "a" * 32, "terminal_status": "error"}]
    assert runtime.begins == 1


def test_ordinary_browser_failure_still_raises_after_pending(monkeypatch):
    runtime = _submission_setup(monkeypatch, private=False)
    monkeypatch.setattr(web, "_run_turn", lambda *_args, **_kwargs: (
        (_ for _ in ()).throw(RuntimeError("ordinary_failure"))
    ))
    stream = web.submit_text_browser_bound("ordinary input", [], False,
                                           expected_session_id="isolated-session")
    pending = next(stream)
    assert pending[0][-1] == {"role": "assistant", "content": "..."}
    with pytest.raises(RuntimeError, match="ordinary_failure"):
        next(stream)
    assert runtime.finishes == [{"admission_token": "a" * 32, "terminal_status": "error"}]


def test_private_browser_success_appends_one_real_assistant_after_user(monkeypatch):
    runtime = _submission_setup(monkeypatch)
    original = [{"role": "assistant", "content": "前の返事。"}]
    reply = "うん、聞いてるよ。"
    result = {
        "reply": reply,
        "debug": {},
        "audio_path": None,
        "cognition_trace": {"runtime_trace": {"blackboard": []}},
        "memory_snapshot": {},
        "flow_html": "fake flow",
        "state_html": "fake state",
    }
    monkeypatch.setattr(web, "_run_turn", lambda *_args, **_kwargs: result)
    monkeypatch.setattr(web, "_finalize_surface_delivery", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(web, "_append_conversation_log", lambda *_args, **_kwargs: {
        "turn_index": 1, "session_id": "isolated-session",
    })
    monkeypatch.setattr(web, "_annotation_context_markdown", lambda _record: "fake annotation")
    monkeypatch.setattr(web, "_client_cognition_payload_m24", lambda _value: {})
    monkeypatch.setattr(web, "_client_memory_payload_m24", lambda _value: {})
    monkeypatch.setattr(web, "_client_turn_record_m24", lambda *_args: {
        "turn_index": 1, "session_id": "isolated-session",
    })
    monkeypatch.setattr(web, "_mint_browser_graph_receipt", lambda _record, _session: "fake-receipt")
    updates = list(web.submit_text_browser_bound(
        "newest input", original, False, expected_session_id="isolated-session",
    ))
    assert all(len(update) == 14 for update in updates)
    assert [row for row in updates[0][0] if row["role"] == "assistant"] == original
    assert updates[-1][0] == [
        original[0], {"role": "user", "content": "newest input"},
        {"role": "assistant", "content": reply},
    ]
    assert updates[-1][13] == "fake-receipt"
    assert runtime.finishes == [{"admission_token": "a" * 32, "terminal_status": "delivered"}]


def test_private_plus_exact_input_without_permit_keeps_exact_rejection(monkeypatch):
    runtime = _submission_setup(monkeypatch)
    import uruha_source_event_exact_input_capability_p4 as cap

    monkeypatch.setattr(web, "_exact_input_surface_arm", lambda: "on")
    monkeypatch.setattr(cap, "claim_exact_input_permit", lambda *_args: (
        (_ for _ in ()).throw(cap.ExactInputCapabilityError(
            "missing_permit", pre_turn_safe=True,
        ))
    ))
    monkeypatch.setattr(cap, "abandon_unreserved_exact_input_claim", lambda _claim: False)
    monkeypatch.setattr(web, "_run_turn", lambda *_args, **_kwargs: pytest.fail("unexpected_turn"))
    updates = list(web.submit_text_browser_bound(
        "unpermitted", [], False, expected_session_id="isolated-session",
    ))
    assert len(updates) == 1 and len(updates[0]) == 14
    assert updates[0][0] == []
    assert runtime.begins == 0 and runtime.finishes == []
