"""Development contracts, not formal reserve or human-rated evidence."""
from copy import deepcopy
import json
import subprocess
import sys

from uruha_supported_feedback_closure_m43 import (
    LABEL_M43, SCHEMA_M43, classify_support_act_m43, build_feedback_closure_m43,
    apply_feedback_closure_m43, close_linked_validation_m43,
    verify_current_act_surface_m43, materialize_feedback_trace_m43,
    apply_longitudinal_closure_m43, bind_emitted_validation_m43,
)
from uruha_memory_observatory import collect_cognitive_graph
from uruha_m43_memory_observatory import render_memory_observatory_m43


def feedback():
    return {"status":"supported","previous_prediction_id":"dev-prediction-4",
            "previous_policy_id":"calibrate_need","feedback_linked_to_previous_prediction":True,
            "causal_outcome_calibration_m27":{"status":"resolved_decisive"}}


def plan():
    return {"intent":"casual","scene":"casual","core_message_jp":"うん。",
            "desired_response_policy_m18":"calibrate_need",
            "counterfactual_pragmatic_branch_m34":{"selected_branch":{"policy_id":"calibrate_need"}}}


def applied(text="That's correct.", source=None, current=None):
    return apply_feedback_closure_m43(current or plan(),build_feedback_closure_m43(text,source or feedback(),{}))


def test_retained_real_failure_and_compositional_dev_support():
    for text in ["Yes, that's exactly right.","Yeah, correct, thanks.","你說得對，謝謝。",
                 "そうそう、その通り。", "Well, you really got it right!"]:
        assert classify_support_act_m43(text)["status"]=="pure_support",text
        logic,contract = applied(text)
        assert logic[LABEL_M43]["authoritative"] and contract["suppresses_new_pending_prediction"],text


def test_whole_utterance_scope_never_swallows_new_or_quoted_content():
    for text in ["Correct, but please explain the bus route.","那句『對』是他說的。",
                 "Yes?", "そうだけど、分からない。", "not exactly", "They said that's correct.",
                 "'That's correct.'", "對我來說不一樣。", "thanks", " "]:
        assert classify_support_act_m43(text)["status"]=="not_pure_support",text
        assert not applied(text)[0][LABEL_M43]["authoritative"],text


def test_no_new_support_truth_and_no_raw_trace():
    source = feedback()
    original = deepcopy(source)
    logic,contract = applied(source=source)
    assert source==original and not logic[LABEL_M43]["upstream_outcome_changed"]
    assert "That's correct." not in json.dumps(logic[LABEL_M43],ensure_ascii=False)
    for modification in [{"status":"uncertain"},{"feedback_linked_to_previous_prediction":False},
                         {"causal_outcome_calibration_m27":{"status":"resolved_unknown_excluded"}},
                         {"current_request_separated_from_feedback":True}]:
        candidate={**source,**modification}
        assert not applied(source=candidate)[0][LABEL_M43]["authoritative"]


def test_protected_and_factual_fields_unchanged():
    for current in [{"intent":"crisis_support","scene":"crisis","core_message_jp":"一人にならないで。"},
                    {"intent":"recall_fact","scene":"casual","core_message_jp":"青だったよ。"},
                    {"semantic_route_m22":{"selected_type":"deliberation"},"core_message_jp":"確認する。"}]:
        result,contract=applied(current=current)
        assert all(result[k]==v for k,v in current.items())
        assert not contract["surface_authority"] and not result[LABEL_M43]["authoritative"]


def test_only_matching_act_validation_closed_never_promote_fact():
    closure=applied()[0][LABEL_M43]
    pending={"status":"pending","asked_turn":3,"validation_id":"dev-val","model_item_id":"dev-unknown",
             "response_prediction_id_m43":"dev-prediction-4","response_binding_verified_m43":True}
    state={"active_validation":{"pending":pending,"history":[]},
           "layers":{"provisional":[{"value":"unknown","confidence":0.3}],"stable":[]}}
    original=deepcopy(state)
    updated,audit=close_linked_validation_m43(state,closure,5)
    assert updated["active_validation"]["pending"] is None and audit["closed_count"]==1
    assert updated["layers"]==state["layers"] and state==original
    for changes in [{"response_prediction_id_m43":"different"},{"response_binding_verified_m43":False},
                    {"asked_turn":5},{"status":"resolved"}]:
        other=deepcopy(state);other["active_validation"]["pending"].update(changes)
        assert close_linked_validation_m43(other,closure,5)[0]==other
    no_authority={**closure,"authoritative":False}
    assert close_linked_validation_m43(state,no_authority,5)[0]==state


def test_current_ack_not_previous_policy_is_verified_without_rewriting_ledger():
    logic,contract=applied()
    branch=deepcopy(logic["counterfactual_pragmatic_branch_m34"])
    final,trace=verify_current_act_surface_m43("That's correct.","ん、そこもう少しだけ聞かせて。",logic)
    assert final==contract["expected_surface_jp"]=="ん、分かった。"
    assert not logic[LABEL_M43]["surface"]["question_reopened"]
    assert trace["policy_act_match_after"] and trace["current_turn_act_m43"]=="acknowledge_previous_response"
    assert logic["counterfactual_pragmatic_branch_m34"]==branch
    assert logic["desired_response_policy_m18"]=="calibrate_need"


def test_suppression_retains_provisional_model_and_unrelated_pending():
    import uruha_personhood_loop as p
    model=p.empty_longitudinal_model()
    model["layers"]["provisional"]=[{
        "model_item_id":"dev-unknown","kind":"pragmatic_implicit_need","value":"unknown",
        "status":"active","confidence":0.3,"linked_hypothesis_ids":["dev-hyp"],
        "consecutive_influence_count":1,"last_influenced_turn":3}]
    hypothesis={"hypothesis_id":"dev-hyp","semantic_features":[]}
    contract=build_feedback_closure_m43("That's correct.",feedback(),{})
    old_plan,old_model,old_strategy=p.apply_longitudinal_model_to_plan(plan(),model,hypothesis,4)
    assert old_strategy["changed_plan"]
    new_plan,new_model,strategy,audit=apply_longitudinal_closure_m43(plan(),model,hypothesis,4,contract)
    assert audit["new_generic_validation_suppressed"] and not strategy["changed_plan"]
    assert new_model["layers"]==old_model["layers"]
    assert not new_model["active_validation"]["pending"]
    assert new_plan["intent"]=="casual"
    unrelated={"validation_id":"unrelated","status":"pending","asked_turn":2}
    model["active_validation"]["pending"]=unrelated
    preserved=apply_longitudinal_closure_m43(plan(),model,hypothesis,4,contract)[1]
    assert preserved["active_validation"]["pending"]==unrelated


def test_binding_requires_emitted_question_and_links_only_response_not_truth():
    model={"active_validation":{"pending":{"status":"pending","asked_turn":2,
                                              "question_jp":"今は聞いてほしい？","validation_id":"dev"}}}
    prediction={"prediction_id":"dev-pred"}
    logic={"surface_act":"functional_understanding_active_verify"}
    bound,audit=bind_emitted_validation_m43(model,prediction,logic,"今は聞いてほしい？",2)
    assert audit["verified"] and not audit["mental_fact_promoted"]
    assert bound["active_validation"]["pending"]["response_prediction_id_m43"]=="dev-pred"
    assert "response_prediction_id_m43" not in model["active_validation"]["pending"]
    for current,reply,turn in [(logic,"別の返事。",2),({},"今は聞いてほしい？",2),(logic,"今は聞いてほしい？",3)]:
        unchanged,trace=bind_emitted_validation_m43(model,prediction,current,reply,turn)
        assert unchanged==model and not trace["verified"]


def test_persona_ack_variation_is_grounded_in_act_not_user_mental_fact():
    outputs=[]
    for text,source in [("That's correct.",feedback()),("That's correct, thank you.",feedback()),
                        ("That's correct.",{**feedback(),"previous_policy_id":"listen_presence"})]:
        logic,contract=applied(text,source)
        final,_=verify_current_act_surface_m43(text,"承知しました。",logic)
        assert final==contract["expected_surface_jp"]
        assert not any('a'<=c.lower()<='z' for c in final)
        outputs.append(final)
    assert len(set(outputs))==3


def test_current_graph_payload_connected_once_no_stale_node():
    logic,_=applied()
    result={"logic":logic,"reply":"ん、分かった。","runtime_trace":{"blackboard":[
        {"stage":"select","label":"selected_plan","payload":{}},
        {"stage":"speak","label":"utterance","payload":{}}]}}
    materialize_feedback_trace_m43(result);materialize_feedback_trace_m43(result)
    graph=collect_cognitive_graph(result)
    node=next(n for n in graph["nodes"] if n["label"]==LABEL_M43)
    assert any(e["source"]==node["id"] or e["target"]==node["id"] for e in graph["edges"])
    assert sum(x["label"]==LABEL_M43 for x in result["runtime_trace"]["blackboard"])==1
    assert 'aria-label="M43 confirmed feedback flow"' in render_memory_observatory_m43(result)
    result["logic"]={};materialize_feedback_trace_m43(result)
    assert not any(x["label"]==LABEL_M43 for x in result["runtime_trace"]["blackboard"])


def test_actual_installer_chain_seed_feedback_and_history_contract():
    program = r'''
from test_personhood_loop_v2_13 import _IsolatedContractBrain
from test_adaptive_person_model_m16 import AMBIGUOUS_INPUT
from test_outcome_calibrated_implicit_response_m26 import PRACTICAL_CORRECTION,REPEATED_AMBIGUOUS
import uruha_web_ui_m43
from uruha_supported_feedback_closure_m43 import LABEL_M43,install_m43_feedback_closure
assert not install_m43_feedback_closure()
brain=_IsolatedContractBrain()
brain.run_turn_debug(AMBIGUOUS_INPUT)
brain.run_turn_debug(PRACTICAL_CORRECTION)
brain.run_turn_debug(REPEATED_AMBIGUOUS)
result=brain.run_turn_debug("Yes, that's exactly right.")
trace=result['logic'][LABEL_M43]
assert trace['authoritative'],trace
assert result['reply']=='ん、分かった。',result['reply']
assert brain.runtime.adaptive_person_model.get('pending_prediction') is None
for view in [result['runtime_trace'],result['runtime_state']['recent_turn_traces'][-1]]:
    row=next(x for x in view['blackboard'] if x['label']==LABEL_M43)
    assert row['payload']==trace
assert result['runtime_trace']['adaptive_person_feedback_m18']['status']=='supported'
print('actual runtime contract chain passed, fake generation and isolated memory')
'''
    done=subprocess.run([sys.executable,"-c",program],capture_output=True,text=True)
    assert done.returncode==0,done.stdout+done.stderr
