"""Author-created mechanism tests; not human preference or held-out evidence."""
from copy import deepcopy
import json
import subprocess
import sys

import pytest
import uruha_personhood_loop as personhood
import uruha_grounded_validation_p2 as gate


def fixture(text="今日は本を読んだ。"):
    pragmatic = personhood.build_human_pragmatic_understanding(text, turn_index=2)
    hypothesis = {"hypothesis_id": "dev-h2", "semantic_features": [],
                  "pragmatic_understanding_v2_13": pragmatic}
    model = personhood.empty_longitudinal_model()
    source = pragmatic["inferences"]["implicit_need"]
    model["layers"]["provisional"] = [{
        "model_item_id": "dev-slot", "kind": "pragmatic_implicit_need", "value": source["value"],
        "status": "active", "confidence": 0.4, "linked_hypothesis_ids": ["dev-h2"],
        "consecutive_influence_count": 1, "last_influenced_turn": 1}]
    plan = {"intent": "casual", "scene": "casual", "core_message_jp": "うん。",
            "constraints": {"unsolicited_advice": False}, "unrelated_field": "preserve"}
    return plan, model, hypothesis


def test_unresolved_slot_proposes_unjustified_choice_before_and_is_withdrawn_after():
    plan, model, hypothesis = fixture()
    frozen = deepcopy((plan, model, hypothesis))
    old_plan, old_state, old_strategy = gate._previous_apply(plan, model, hypothesis, 2)
    assert old_strategy["changed_plan"] and "放っといて" in old_plan["core_message_jp"]
    new_plan, new_state, strategy = gate.apply_grounded_validation_p2(plan, model, hypothesis, 2)
    assert not strategy["changed_plan"] and not new_state["active_validation"]["pending"]
    assert strategy[gate.TRACE]["blocked"]
    assert all(new_plan[k] == v for k, v in plan.items())
    assert new_state["layers"] == old_state["layers"]
    assert new_state["typed_calibration"] == old_state["typed_calibration"]
    assert (plan, model, hypothesis) == frozen
    assert not strategy[gate.TRACE]["upstream_outcome_changed"]


def test_concrete_uncertain_hypothesis_remains_eligible():
    plan, model, hypothesis = fixture("Maybe another time.")
    before = gate._previous_apply(plan, model, hypothesis, 2)
    logic, state, strategy = gate.apply_grounded_validation_p2(plan, model, hypothesis, 2)
    assert strategy["changed_plan"] and not strategy[gate.TRACE]["blocked"]
    assert logic["core_message_jp"] == before[0]["core_message_jp"]
    assert state == before[1]


@pytest.mark.parametrize("mutation", ["schema", "missing_field", "wrong_value", "missing_evidence", "unknown"])
def test_missing_or_mismatched_typed_source_cannot_authorize_question(mutation):
    plan, model, hypothesis = fixture("Maybe another time.")
    pragmatic = hypothesis["pragmatic_understanding_v2_13"]
    source = pragmatic["inferences"]["implicit_need"]
    if mutation == "schema":
        pragmatic.pop("schema")
    elif mutation == "missing_field":
        pragmatic["inferences"].pop("implicit_need")
    elif mutation == "wrong_value":
        source["value"] = "different typed claim"
    elif mutation == "missing_evidence":
        source["evidence"] = []
    else:
        source["epistemic_status"] = "unknown"
    _, state, strategy = gate.apply_grounded_validation_p2(plan, model, hypothesis, 2)
    assert strategy[gate.TRACE]["blocked"] and not state["active_validation"]["pending"]


def test_existing_pending_direct_report_and_protected_action_are_not_replaced():
    for condition in ("pending", "direct_report", "protected"):
        plan, model, hypothesis = fixture()
        direct = None
        if condition == "pending":
            model["active_validation"]["pending"] = {"validation_id": "older", "status": "pending", "asked_turn": 1}
        elif condition == "direct_report":
            direct = {"kind": "current_name_update", "value": "ミナ"}
        else:
            plan["intent"] = "recall_fact"
            plan["memory_recall_contract"] = {"source_id": "dev-fact"}
        old = gate._previous_apply(plan, model, hypothesis, 2, direct_user_report=direct)
        new = gate.apply_grounded_validation_p2(plan, model, hypothesis, 2, direct_user_report=direct)
        assert new[1] == old[1]
        assert not new[2][gate.TRACE]["blocked"]
        assert new[0]["core_message_jp"] == old[0]["core_message_jp"]


def test_non_pragmatic_candidates_are_outside_this_change_and_trace_has_no_raw_input():
    plan, model, hypothesis = fixture()
    model["layers"]["provisional"][0]["kind"] = "emotion_or_need"
    _, _, strategy = gate.apply_grounded_validation_p2(plan, model, hypothesis, 2)
    assert strategy["changed_plan"] and not strategy[gate.TRACE]["blocked"]
    trace = json.dumps(strategy[gate.TRACE], ensure_ascii=False)
    assert "今日は本を読んだ" not in trace
    assert strategy[gate.TRACE]["added_model_calls"] == 0


def test_full_product_installer_retains_trace_in_actual_runtime_graph(tmp_path):
    # Fresh interpreter prevents changing frozen test globals in this process.
    program = r'''
import os, json
from pathlib import Path
root=Path(os.environ['P2_TEST_ROOT'])
os.environ['URUHA_ADAPTIVE_PERSON_MODEL_PATH']=str(root/'adaptive.json')
os.environ['URUHA_MEMORY_DB_PATH']=str(root/'memory')
os.environ['URUHA_WEB_PREWARM_BRAIN']='0'
os.environ['URUHA_IDLE_VISIBLE_PROACTIVE_ENABLED']='false'
os.environ['GRADIO_ANALYTICS_ENABLED']='false'
import project_paths
project_paths.WEB_LOG_DIR=str(root/'web')
project_paths.WEB_CONVERSATION_LOG_JSONL_PATH=str(root/'web/turns.jsonl')
project_paths.WEB_CONVERSATION_LOG_TXT_PATH=str(root/'web/turns.txt')
import uruha_web_ui_product
from test_personhood_loop_v2_13 import _IsolatedContractBrain
from uruha_memory_observatory import collect_cognitive_graph
from uruha_grounded_validation_p2 import TRACE, install_grounded_validation_p2
assert not install_grounded_validation_p2()
brain=_IsolatedContractBrain()
brain.run_turn_debug('方法はいらない。ただ聞いてほしい。')
result=brain.run_turn_debug('そう、それでいい。')
strategy=result['logic']['active_validation_strategy_v2_13']
assert strategy[TRACE]['blocked'], strategy
assert not strategy['changed_plan']
assert '今は放っといてほしいのか' not in result['reply'], result['reply']
assert not brain.runtime.longitudinal_user_model['active_validation']['pending']
rows=brain.runtime.adaptive_person_model['outcome_calibration_ledger_m27']
assert rows[0]['result_status']=='uncertain', rows
graph=collect_cognitive_graph(result)
node=next(n for n in graph['nodes'] if n['label']=='active_validation_strategy_v2_13')
assert TRACE in json.dumps(node), node
assert any(e['source']==node['id'] or e['target']==node['id'] for e in graph['edges'])
'''
    import os
    env = {**os.environ, "P2_TEST_ROOT": str(tmp_path)}
    subprocess.run([sys.executable, "-c", program], env=env, check=True, capture_output=True, text=True, timeout=90)
