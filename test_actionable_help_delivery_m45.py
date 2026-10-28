from copy import deepcopy
import json
import subprocess
import sys

from uruha_actionable_help_delivery_m45 import (
    LABEL, REVIEW_KEYS, PLAN_SCHEMA, REVIEW_SCHEMA, CLARIFY, UNAVAILABLE,
    source_packet, deliver_action, inspect_action_delivery, mark_current_delivery,
    materialize_trace_m45, digest,
)
from uruha_actionable_help_eval_m45 import fixture, evaluate_cases
from uruha_memory_observatory import collect_cognitive_graph
from uruha_m45_memory_observatory import render_memory_observatory_m45


def help_logic():
    return {"desired_response_policy_m18": "solve_regulation",
            "desired_response_decision_m18": {"prediction_id": "dev-one"},
            "semantic_route_m22": {"selected_type": "explicit_correction"}}


def fake_calls(proposal, checks=None):
    def call(system, payload, schema, deadline, metrics):
        metrics["model_calls_attempted"] += 1
        metrics["model_calls_completed"] += 1
        if schema is PLAN_SCHEMA:
            assert "user_sources" in payload and "candidate_jp" not in payload
            return {key: proposal.get(key) for key in ("status", "instruction_jp")}
        assert schema is REVIEW_SCHEMA
        assert "candidate_jp" not in payload  # reviewer doesn't see draft/praise
        assert payload["instruction_jp"] == proposal["instruction_jp"]
        return {**{key: proposal.get(key) for key in
                   ("source_id", "source_span", "object_jp", "verb_jp", "completion_jp")},
                "checks": deepcopy(checks if checks is not None else {k: True for k in REVIEW_KEYS})}
    return call


def test_source_packet_never_uses_assistant_or_unlinked_history():
    memory = {"recent_turns": [{"user": "first", "reply": "secret one"},
                               {"user": "second", "reply": "invented fact"}]}
    for feedback in ({}, {"status": "supported", "feedback_linked_to_previous_prediction": True}):
        assert len(source_packet("now", memory, feedback, 3)) == 1
    sources = source_packet("now", memory, {"status": "contradicted",
        "feedback_linked_to_previous_prediction": True, "explicit_target_policy": "solve_regulation"}, 3)
    assert [s["text"] for s in sources] == ["now", "second"]
    assert "invented" not in json.dumps(sources)


def test_source_id_repair_requires_unique_exact_quote_in_allowed_user_evidence():
    from uruha_actionable_help_delivery_m45 import resolve_source_binding
    sources = [{"id": "current:2", "kind": "current_user", "text": "Give me a step."},
               {"id": "prior:1", "kind": "linked_previous_user", "text": "The drawer is cluttered."}]
    proposal = {"source_id": "current:2", "source_span": "drawer"}
    fixed, reason = resolve_source_binding(proposal, sources)
    assert fixed["source_id"] == "prior:1" and proposal["source_id"] == "current:2"
    assert reason == "unique_exact_span_source_rebound"
    for bad in ({"source_id": "invented", "source_span": "drawer"},
                {"source_id": "current:2", "source_span": "bookcase"}):
        assert resolve_source_binding(bad, sources)[0] == bad
    ambiguous = sources + [{"id": "prior:0", "kind": "linked_previous_user", "text": "another drawer"}]
    assert resolve_source_binding(proposal, ambiguous)[0] == proposal


def test_concrete_action_has_source_object_verb_and_stopping_condition():
    p, sources, review = fixture()
    final, trace = deliver_action(sources[0]["text"], "まず一個決めよ。", help_logic(), sources, fake_calls(p))
    assert final == p["instruction_jp"]
    assert trace["delivered"] and trace["model_calls_completed"] == 2
    assert trace["evidence"]["source_id"] == "current:1"
    assert trace["action"]["completion_jp"] == p["completion_jp"]
    assert sources[0]["text"] not in json.dumps(trace, ensure_ascii=False)
    assert not trace["human_validated"]


def test_independent_review_is_required_even_for_keyword_compliant_action():
    p, sources, review = fixture("empty_promise")
    assert not inspect_action_delivery(p, sources, review)["delivered"]
    final, trace = deliver_action(sources[0]["text"], p["instruction_jp"], help_logic(), sources, fake_calls(p, review["checks"]))
    assert not trace["delivered"] and final == UNAVAILABLE
    assert trace["model_calls_completed"] == 2


def test_missing_information_is_not_help_success_and_uses_only_one_call():
    p, sources, _ = fixture("needs_context")
    final, trace = deliver_action("Give me one step.", "まず一個決めよ。", help_logic(), sources, fake_calls(p))
    assert final == CLARIFY and not trace["delivered"]
    assert trace["status"] == "awaiting_context" and trace["model_calls_attempted"] == 1


def test_invalid_extracted_source_is_rejected_and_nonjapanese_skips_review():
    for variant in ("missing_source", "invented_span", "assistant_as_source", "english_surface", "empty_completion"):
        p, sources, _ = fixture(variant)
        _, trace = deliver_action(sources[0]["text"], "まず一個。", help_logic(), sources, fake_calls(p))
        assert not trace["delivered"], variant
        assert trace["model_calls_attempted"] == (1 if variant == "english_surface" else 2), variant


def test_protected_nonhelp_and_acknowledgement_are_unchanged_and_zero_call():
    def forbidden(*args):
        raise AssertionError("Must not call a model")
    plans = [dict(help_logic(), semantic_route_m22={"selected_type": "safety_sensitive"}),
             dict(help_logic(), semantic_route_m22={"selected_type": "factual_or_memory"}),
             dict(help_logic(), desired_response_policy_m18="listen_presence"),
             dict(help_logic(), supported_feedback_closure_m43={"authoritative": True})]
    for plan in plans:
        text, trace = deliver_action("input", "元の回覆。", plan, [], forbidden)
        assert text == "元の回覆。" and trace["status"] == "not_applicable"
        assert trace["model_calls_attempted"] == 0


def test_transport_failure_is_explicit_not_zero_latency_success():
    def failing(system, payload, schema, deadline, metrics):
        metrics["model_calls_attempted"] += 1
        raise TimeoutError("do not persist this raw message")
    final, trace = deliver_action("input", "まず一個。", help_logic(), source_packet("input"), failing)
    assert final == UNAVAILABLE and not trace["delivered"]
    assert trace["reason"] == "TimeoutError" and not trace["token_accounting_complete"]
    assert "raw message" not in json.dumps(trace)


def test_oversized_source_and_exhausted_budget_fail_without_model_call():
    import uruha_actionable_help_delivery_m45 as module
    def forbidden(*args):
        raise AssertionError("No model call expected")
    _, trace = deliver_action("a" * 2001, "まず一個。", help_logic(), source_packet("a" * 2001), forbidden)
    assert trace["status"] == "withheld_source_budget" and trace["model_calls_attempted"] == 0
    try:
        module._native_json("", {}, PLAN_SCHEMA, -1, {})
    except TimeoutError:
        pass
    else:
        raise AssertionError("Exhausted budget must stop before transport")


def test_malformed_delivery_record_does_not_break_loading_or_keep_raw_text():
    import uruha_actionable_help_delivery_m45 as module
    assert module._clean_record({"prediction_id": "x", "delivered": False, "turn_index": "wrong"}) is None
    clean = module._clean_record({"prediction_id": "x", "delivered": True, "turn_index": 1, "raw_text": "private"})
    assert "private" not in json.dumps(clean)


def test_valid_existing_action_can_be_preserved():
    p, sources, _ = fixture()
    final, trace = deliver_action(sources[0]["text"], p["instruction_jp"], help_logic(), sources, fake_calls(p))
    assert not trace["changed"] and trace["delivered"]


def test_verb_inflection_is_not_confused_with_missing_action_but_review_still_required():
    p, sources, _ = fixture()
    p["instruction_jp"] = p["instruction_jp"].replace("書き出してみよ", "書き出せ")
    p["verb_jp"] = "書き出す"
    _, trace = deliver_action(sources[0]["text"], "まず一個。", help_logic(), sources, fake_calls(p))
    assert trace["delivered"] and trace["model_calls_completed"] == 2
    p["verb_jp"] = "調べる"
    _, trace = deliver_action(sources[0]["text"], "まず一個。", help_logic(), sources, fake_calls(p))
    assert not trace["delivered"] and trace["model_calls_completed"] == 2


def test_reviewer_cannot_rewrite_utterance_or_turn_useless_work_into_success():
    p, sources, _ = fixture()
    checks = {key: True for key in REVIEW_KEYS}
    checks["advances_user_task"] = False
    final, trace = deliver_action(sources[0]["text"], "まず一個。", help_logic(), sources, fake_calls(p, checks))
    assert final == UNAVAILABLE and not trace["delivered"]
    assert "review_advances_user_task_not_passed" in trace["violations"]
    assert trace["review_candidate_digest"] == digest(p["instruction_jp"])


def test_action_record_only_changes_matching_pending_not_history_or_outcome():
    from uruha_adaptive_person_model import empty_model
    state = empty_model()
    state["pending_prediction"] = {"prediction_id": "dev-one", "turn_index": 2}
    state["outcome_calibration_ledger_m27"] = [
        {"prediction_id": "old", "result_status": "supported", "eligible_for_implicit_calibration": True},
        {"prediction_id": "dev-one", "result_status": "pending", "eligible_for_implicit_calibration": True}]
    logic = help_logic()
    logic[LABEL] = {"status": "awaiting_context", "delivered": False, "final_reply_digest": digest(CLARIFY)}
    original = deepcopy(state)
    changed, applied = mark_current_delivery(state, logic, 2)
    assert applied and state == original
    assert changed["outcome_calibration_ledger_m27"][0] == original["outcome_calibration_ledger_m27"][0]
    assert not changed["outcome_calibration_ledger_m27"][1]["eligible_for_implicit_calibration"]
    unchanged, applied = mark_current_delivery(state, logic, 9)
    assert not applied and unchanged == state


def test_graph_payload_matches_same_cycle_and_is_connected_once():
    p, sources, _ = fixture()
    _, trace = deliver_action(sources[0]["text"], "まず一個。", help_logic(), sources, fake_calls(p))
    result = {"logic": {LABEL: trace}, "runtime_trace": {"cycle_index": 1, "blackboard": [
        {"stage": "speak", "label": "utterance", "payload": {"reply": p["instruction_jp"]}}]},
        "runtime_state": {"recent_turn_traces": [{"cycle_index": 1}]}}
    materialize_trace_m45(result)
    materialize_trace_m45(result)
    graph = collect_cognitive_graph(result)
    nodes = [n for n in graph["nodes"] if n.get("label") == LABEL]
    assert len(nodes) == 1
    assert any(e["source"] == nodes[0]["id"] or e["target"] == nodes[0]["id"] for e in graph["edges"])
    assert result["runtime_state"]["recent_turn_traces"][-1][LABEL] == trace
    assert "已給出可做的步驟" in render_memory_observatory_m45(result)


def test_evaluator_smoke_is_development_not_formal_reserve():
    result = evaluate_cases([{"id": "dev-a", "variant": "concrete", "expected_delivered": True},
                             {"id": "dev-b", "variant": "empty_promise", "expected_delivered": False}])
    assert result["status"] == "PASS" and result["model_calls"] == 0


def test_runtime_boundary_precedes_episode_save_and_missing_action_cannot_gain_credit(tmp_path):
    program = r'''
import json,sys
import uruha_web_ui_m45
import uruha_actionable_help_delivery_m45 as m
import uruha_adaptive_person_model as a
import uruha_semantic_persona_surface_m39 as s
from test_personhood_loop_v2_13 import _IsolatedContractBrain,_FakeRightBrain
from test_actionable_help_delivery_m45 import fake_calls
from uruha_actionable_help_eval_m45 import fixture
assert not m.install_m45_action_delivery()
class FakeRight(_FakeRightBrain):
    def enforce_user_visible_japanese(self, reply, logic, user_input='', **kwargs):
        final,audit=s.verify_and_repair_surface_m39(user_input,reply,logic)
        logic['semantic_persona_surface_verifier_m39']=audit
        return final
b=_IsolatedContractBrain(); b.right_brain=FakeRight()
p,_,_=fixture(); m._native_json=fake_calls(p)
r=b.run_turn_debug('I am drafting a notice for the reading club. Give me one practical step.')
assert r['logic'][m.LABEL]['delivered'], (r['reply'],r['logic'][m.LABEL])
assert b.memory.saved_episodes[-1]['reply']==r['reply']==p['instruction_jp']
for view in (r['runtime_trace'],r['runtime_state']['recent_turn_traces'][-1]):
    assert view[m.LABEL]==r['logic'][m.LABEL]
p['status']='needs_context'; m._native_json=fake_calls(p)
r=b.run_turn_debug('You misunderstood; give me one practical step I can take now.')
assert r['logic'][m.LABEL]['status']=='awaiting_context',r['logic'][m.LABEL]
assert not r['logic']['semantic_persona_surface_verifier_m39']['policy_act_match_after']
assert b.runtime.adaptive_person_model[m.STORE]['delivered'] is False
a.save_model(sys.argv[1],b.runtime.adaptive_person_model)
loaded,_=a.load_model(sys.argv[1]); assert loaded[m.STORE]==b.runtime.adaptive_person_model[m.STORE]
state,feedback=a.observe_next_turn(loaded,'Yes, exactly.',3)
assert feedback['status']=='uncertain',feedback
assert feedback[m.OUTCOME_LABEL]['outcome']=='not_scored_action_not_delivered'
assert not feedback['atom_changes']
print('2 runtime turns use fake local generation/review; episode, graph, disk and non-credit contracts passed')
'''
    result = subprocess.run([sys.executable, "-c", program, str(tmp_path / "adaptive.json")], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
