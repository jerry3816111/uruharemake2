"""Development contracts; separate from the one frozen formal reserve run."""
from copy import deepcopy
import json
import subprocess
import sys

from uruha_executed_action_receipt_m44 import (
    LABEL, OUTCOME_LABEL, STORE, register_executed_action_m44,
    observe_executed_action_m44, normalise_model_m44, materialize_trace_m44,
)
from uruha_executed_action_receipt_eval_m44 import fixture, evaluate_cases
from uruha_memory_observatory import collect_cognitive_graph
from uruha_m44_memory_observatory import render_memory_observatory_m44


def test_record_only_actual_action_without_rewriting_source_state():
    args = fixture()
    original = deepcopy(args)
    result, trace = register_executed_action_m44(*args)
    assert args == original
    assert trace["status"] == "registered_for_next_user_turn", trace
    assert result["pending_prediction"]["prediction_id"] == trace["prediction_id"]
    assert result[STORE][0]["outcome"] == "pending"
    assert result["trigger_policy_relations_m37"] == args[0]["trigger_policy_relations_m37"]
    assert result["revision_count"] == args[0]["revision_count"]
    assert not trace["eligible_for_implicit_calibration"]
    for value in args[2:4]:
        assert value not in json.dumps([result, trace], ensure_ascii=False)


def test_missing_or_conflicting_evidence_never_registers():
    for variant in ["inactive_relation", "unverified_relation", "expired_relation", "reply_digest",
                    "input_digest", "m39_policy", "decision_policy", "branch_policy", "unresolved",
                    "protected", "factual", "no_suppression", "current_ack", "existing_pending",
                    "resolved_ledger", "stale_cycle", "empty_reply", "not_performed", "no_relation"]:
        args = fixture(variant=variant)
        result, trace = register_executed_action_m44(*args)
        assert trace["status"] == "not_registered", (variant, trace)
        assert result == args[0], variant


def test_idempotency_and_resolved_ledger_never_reset():
    args = fixture()
    first, trace = register_executed_action_m44(*args)
    second, again = register_executed_action_m44(first, *args[1:])
    assert first == second and again["reason"] == "existing_pending_preserved"
    resolved, feedback = observe_executed_action_m44(first, "Yes, exactly.", 4)
    assert feedback["status"] == "supported"
    final, audit = register_executed_action_m44(resolved, *args[1:])
    assert final == resolved and audit["reason"] == "existing_prediction_ledger_entry_preserved"


def test_next_outcomes_are_real_original_observations_not_receipt_credit():
    state, _ = register_executed_action_m44(*fixture())
    examples = [("Yes, exactly.", "supported"),
                ("You misunderstood; give me one practical step I can take now.", "contradicted"),
                ("The package arrives tomorrow.", "uncertain")]
    for text, expected in examples:
        new, trace = observe_executed_action_m44(state, text, 4)
        assert trace["status"] == expected, trace
        assert trace[OUTCOME_LABEL]["outcome"] == expected
        assert new[STORE][0]["outcome"] == expected
        row = next(r for r in new["outcome_calibration_ledger_m27"] if r["prediction_id"] == state["pending_prediction"]["prediction_id"])
        assert row["result_status"] == expected and not row["eligible_for_implicit_calibration"]
        assert text not in json.dumps(new, ensure_ascii=False)
        assert state[STORE][0]["outcome"] == "pending"


def test_late_or_restarted_cycle_cannot_claim_support():
    state, _ = register_executed_action_m44(*fixture())
    for turn in [1, 3, 5, 10]:
        new, trace = observe_executed_action_m44(state, "Yes, exactly.", turn)
        assert trace["status"] == "uncertain"
        assert trace[OUTCOME_LABEL]["outcome"] == "expired"
        assert not trace[OUTCOME_LABEL]["linked"]


def test_typed_persistence_field_retains_only_bounded_receipts():
    state, _ = register_executed_action_m44(*fixture())
    state[STORE][0]["raw_text"] = "private transcript must not survive"
    state[STORE].append({"schema": "invalid", "raw_text": "private"})
    clean = normalise_model_m44(state)
    assert len(clean[STORE]) == 1
    assert "private transcript" not in json.dumps(clean)
    assert clean[STORE][0]["prediction_id"] == state[STORE][0]["prediction_id"]


def test_graph_and_same_cycle_payload_are_actual_and_connected_once():
    _, trace = register_executed_action_m44(*fixture())
    result = {"logic": {LABEL: trace}, "runtime_trace": {"cycle_index": 3, "blackboard": [
        {"label": "utterance", "stage": "speak", "payload": {"reply": "今はここにいる。"}}]},
        "runtime_state": {"recent_turn_traces": [{"cycle_index": 3}]}}
    materialize_trace_m44(result)
    materialize_trace_m44(result)
    graph = collect_cognitive_graph(result)
    nodes = [n for n in graph["nodes"] if n.get("label") == LABEL]
    assert len(nodes) == 1
    assert any(e["source"] == nodes[0]["id"] or e["target"] == nodes[0]["id"] for e in graph["edges"])
    assert result["runtime_state"]["recent_turn_traces"][-1][LABEL] == trace
    assert "已留下可驗證紀錄" in render_memory_observatory_m44(result)


def test_evaluator_development_smoke_not_formal_reserve():
    cases = [{"id": "dev-pass", "policy": "share_arousal", "variant": "valid", "next_outcome": "supported", "expected_registration": True},
             {"id": "dev-no", "policy": "share_arousal", "variant": "protected", "next_outcome": None, "expected_registration": False}]
    result = evaluate_cases(cases)
    assert result["status"] == "PASS", result


def test_installed_runtime_chain_and_disk_roundtrip(tmp_path):
    program = r'''
import json,sys
import uruha_web_ui_m44
import uruha_adaptive_person_model as a
from uruha_executed_action_receipt_m44 import LABEL,OUTCOME_LABEL,STORE,install_m44_executed_action_receipts
from test_personhood_loop_v2_13 import _IsolatedContractBrain,_FakeRightBrain
import uruha_semantic_persona_surface_m39 as surface
assert not install_m44_executed_action_receipts()
class _LiteralSuppressionFixture(_IsolatedContractBrain):
    # Fake generation does not independently enter M32's actual Web route.
    # Inject only the observed post-plan missing-pending condition for turn 3;
    # do not present this contract as a fresh model-generated end-to-end result.
    def cognitive_tick(self,event):
        tick=super().cognitive_tick(event)
        if self.runtime.cycle_index==3:
            pid=tick['logic']['desired_response_decision_m18']['prediction_id']
            self.runtime.adaptive_person_model['pending_prediction']=None
            self.runtime.adaptive_person_model['outcome_calibration_ledger_m27']=[
                r for r in self.runtime.adaptive_person_model['outcome_calibration_ledger_m27'] if r['prediction_id']!=pid]
            tick['logic'].setdefault('semantic_commit_repair_m32',{})['suppresses_new_pending_prediction']=True
        return tick
class _VerifiedFakeRight(_FakeRightBrain):
    def enforce_user_visible_japanese(self,reply,logic,user_input='',**kwargs):
        final,audit=surface.verify_and_repair_surface_m39(user_input,reply,logic)
        logic['semantic_persona_surface_verifier_m39']=audit
        return final
b=_LiteralSuppressionFixture()
b.right_brain=_VerifiedFakeRight()
rows=[b.run_turn_debug(t) for t in [
    'When the report gets stuck, stay with me instead of giving advice.',
    "Yes, that's exactly right.", 'The report has stalled again.', 'その通り、ありがとう。']]
r=rows[2]
assert r['logic'][LABEL]['status']=='registered_for_next_user_turn', (r['logic'][LABEL],r['reply'],r['logic'].get('semantic_persona_surface_verifier_m39'))
assert rows[3]['reply']=='ん、伝わってたならよかった。',rows[3]['reply']
assert rows[3]['logic'][OUTCOME_LABEL]['outcome']=='supported'
for r in rows:
    for v in [r['runtime_trace'],r['runtime_state']['recent_turn_traces'][-1]]:
        assert next(x for x in v['blackboard'] if x['label']==LABEL)['payload']==r['logic'][LABEL]
assert b.runtime.adaptive_person_model[STORE][-1]['outcome']=='supported'
a.save_model(sys.argv[1],b.runtime.adaptive_person_model)
loaded,load_trace=a.load_model(sys.argv[1])
assert loaded[STORE]==b.runtime.adaptive_person_model[STORE]
print('4 runtime contract turns, fake generation plus explicit missing-pending fault injection; disk receipt roundtrip passed')
'''
    done = subprocess.run([sys.executable, "-c", program, str(tmp_path / "model.json")], capture_output=True, text=True)
    assert done.returncode == 0, done.stdout + done.stderr
