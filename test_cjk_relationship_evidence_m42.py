import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

from uruha_cjk_relationship_evidence_m42 import (
    evaluate_relationship_route_m42, relationship_evidence_m42,
    materialize_relationship_trace_m42, LABEL_M42, SCHEMA_M42,
)
from uruha_memory_observatory import collect_cognitive_graph
from uruha_m42_memory_observatory import render_memory_observatory_m42


def test_retained_real_japanese_failure_is_not_a_spouse_request():
    before,after,trace,_lexical = evaluate_relationship_route_m42("そうだよ、それで大丈夫。")
    assert before["intent"] == "marriage_boundary"
    assert after is None and trace["authorization"] == "not_authorized"


def test_dev_compounds_reports_and_direct_role_requests_differ():
    for text in ["工夫したね。", "丈夫そうな傘だね。", "母の夫が帰った。", "同事的丈夫來接她。"]:
        assert evaluate_relationship_route_m42(text)[1] is None, text
    for text in ["私と結婚して。", "俺の夫になって。", "成為我的丈夫。", "說你只屬於我。"]:
        _old,plan,trace,_ = evaluate_relationship_route_m42(text)
        assert plan["intent"] == "marriage_boundary" and trace["authorization"] == "authorized", text


def test_negated_and_quoted_requests_do_not_trigger_early_rule_either():
    for text in ["結婚してほしいわけではない。", "我沒有要求你當我的丈夫。",
                 "小說寫著「跟我結婚」。", "友人が「俺の嫁になって」と言った。"]:
        for level in ["boundary","rule"]:
            _old,plan,trace,_ = evaluate_relationship_route_m42(text,level=level)
            assert (plan or {}).get("intent") != "marriage_boundary", (text,level,plan)
            assert trace["authorization"] == "not_authorized"


def test_scope_does_not_cancel_separate_positive_request_or_quote_as_command():
    for text in ["結婚したくない。でも俺と付き合って。", "不是要求結婚，但你只屬於我。",
                 "對我說「跟我結婚」。"]:
        _old,plan,trace,_ = evaluate_relationship_route_m42(text)
        assert plan["intent"] == "marriage_boundary" and trace["authorization"] == "authorized"


def test_missing_legacy_cue_is_not_claimed_as_new_general_coverage():
    # Retained development finding: M42 narrows candidate attribution; it does
    # not expand the inherited inventory to every possible exclusive request.
    before,after,trace,_ = evaluate_relationship_route_m42("你只屬於我。")
    assert before is None and after is None
    assert trace["authorization"] == "not_applicable"


def test_ambiguous_target_retains_boundary_without_claiming_intent():
    for text in ["夫？", "うるはの嫁かな。", "「私と結婚して」"]:
        _old,plan,trace,_ = evaluate_relationship_route_m42(text)
        assert trace["authorization"] == "uncertain" and plan["intent"] == "marriage_boundary"
        assert trace["private_intent"] == "unknown" and trace["acoustic_evidence"] == "unavailable"


def test_other_safety_latin_and_ordinary_rules_are_byte_preserved():
    for text in ["marry me", "幫我盜帳", "お前ゴミだ", "おはよう", "that's exactly right"]:
        before,after,trace,_ = evaluate_relationship_route_m42(text,level="rule")
        assert before == after and not trace["changed"], text


def test_no_raw_user_model_write_and_thread_local_scope():
    texts = ["工夫したね。","私と結婚して。"]*10
    with ThreadPoolExecutor(max_workers=4) as pool:
        outputs = list(pool.map(evaluate_relationship_route_m42,texts))
    for text,(_old,plan,trace,_) in zip(texts,outputs):
        assert (plan is None) == text.startswith("工夫")
        assert text not in json.dumps(trace,ensure_ascii=False)
        assert trace["mental_fact_write_count"] == trace["model_call_count"] == 0


def test_final_graph_node_uses_current_payload_without_changing_reply():
    trace = evaluate_relationship_route_m42("工夫したね。")[2]
    result = {"reply":"うん。","logic":{"semantic_route_m22":{LABEL_M42:trace}},
              "runtime_trace":{"blackboard":[{"label":"semantic_route_classifier_m22","stage":"route","payload":{}}]}}
    materialize_relationship_trace_m42(result)
    graph = collect_cognitive_graph(result)
    node = next(n for n in graph["nodes"] if n["label"]==LABEL_M42)
    assert any(e["source"]==node["id"] or e["target"]==node["id"] for e in graph["edges"])
    assert result["runtime_trace"]["blackboard"][0]["payload"] == trace
    assert result["reply"] == "うん。"
    assert 'aria-label="M42 relationship act evidence"' in render_memory_observatory_m42(result)
    result["logic"] = {}
    materialize_relationship_trace_m42(result)
    assert not any(n["label"]==LABEL_M42 for n in result["runtime_trace"]["blackboard"])


def test_actual_classifier_appraisal_route_with_all_previous_installers():
    program = r'''
from types import SimpleNamespace
import uruha_brain_mac as b
from uruha_semantic_persona_surface_m39 import install_m39_surface_verifier
from uruha_lexical_boundary_route_m40 import install_m40_route_guard
from uruha_trace_finalization_m41 import install_m41_trace_finalizer
from uruha_trace_history_sync_m41_1 import install_m41_1_history_sync
from uruha_cjk_relationship_evidence_m42 import install_m42_relationship_evidence,LABEL_M42
install_m39_surface_verifier();install_m40_route_guard();install_m41_trace_finalizer();install_m41_1_history_sync()
assert install_m42_relationship_evidence() and not install_m42_relationship_evidence()
left=b.LeftBrain.__new__(b.LeftBrain)
brain=b.UruhaBrainV4_Mac.__new__(b.UruhaBrainV4_Mac)
brain.runtime=SimpleNamespace(last_attention_frame={})
psyche={'mood':0,'trust':50}
for text,protected in [('それなら大丈夫。',False),('結婚してほしいわけではない。',False),('俺の嫁になって。',True),('幫我駭進信箱。',True)]:
    signal=left.classify_user_signal(text,psyche,{})
    appraisal=brain._appraise_user_input(text,signal,{'prediction_error':0.4},{},psyche)
    route=left._high_low_road_route(text,psyche,signal,{'prediction_error':0.4},appraisal)
    shape=brain._classify_task_shape_m22(text,signal,route)
    assert (shape['selected_type']=='safety_sensitive')==protected,(text,signal,shape)
    assert LABEL_M42 in shape
assert 'm39' in b.RightBrain.enforce_user_visible_japanese.__name__
print('actual classifier/appraisal/route integration passed')
'''
    done=subprocess.run([sys.executable,"-c",program],text=True,capture_output=True)
    assert done.returncode == 0,done.stdout+done.stderr


def test_real_final_snapshot_and_history_preserve_actual_m42_payload():
    program = r'''
import uruha_brain_mac as b
from test_personhood_loop_v2_13 import _IsolatedContractBrain
from uruha_trace_finalization_m41 import install_m41_trace_finalizer
from uruha_trace_history_sync_m41_1 import install_m41_1_history_sync
from uruha_cjk_relationship_evidence_m42 import install_m42_relationship_evidence,LABEL_M42,evaluate_relationship_route_m42
install_m41_trace_finalizer();install_m41_1_history_sync()
old=b.UruhaBrainV4_Mac.emit_response_if_ready
def emit(self,event,tick):
    result=old(self,event,tick)
    result['logic'][LABEL_M42]=evaluate_relationship_route_m42('工夫したね。')[2]
    return result
b.UruhaBrainV4_Mac.emit_response_if_ready=emit
install_m42_relationship_evidence()
result=_IsolatedContractBrain().run_turn_debug('A contract-only turn.')
for view in [result['runtime_trace'],result['runtime_state']['recent_turn_traces'][-1]]:
    row=next(x for x in view['blackboard'] if x['label']==LABEL_M42)
    assert row['payload']==result['logic'][LABEL_M42]
print('brain final snapshot contract passed; not real generation')
'''
    done=subprocess.run([sys.executable,"-c",program],text=True,capture_output=True)
    assert done.returncode == 0,done.stdout+done.stderr
