"""Developer-authored P2 space-authority tests; not holdout or human evidence."""
from copy import deepcopy
import json
import os
import subprocess
import sys

import pytest

import uruha_explicit_space_authority_p2 as space


@pytest.mark.parametrize(
    "text,language,scope,expected",
    [
        (
            "不對，現在先別理我。",
            "zh",
            "now",
            "あ、そっちか。分かった。今は一人にしとく。",
        ),
        (
            "No, I want to be alone today.",
            "en",
            "today",
            "あ、そっちか。分かった。今日は一人にしとく。",
        ),
        (
            "しばらく放っておいて。",
            "ja",
            "now",
            "分かった。今は一人にしとく。",
        ),
    ],
)
def test_source_disjoint_multilingual_requests_select_observable_action(
    text, language, scope, expected
):
    result = space.classify_explicit_space_request_p2(text)
    assert result["status"] == "selected_observable_explicit_space_request"
    assert result["language"] == language
    assert result["temporal_scope"] == scope
    assert result["selected_core_jp"] == expected
    assert result["epistemic_status"] == "known_observable_response_request"
    assert result["private_emotion_or_cause_inferred"] is False
    assert result["model_call_added"] is False
    assert result["fact_memory_write_count"] == 0
    assert text not in json.dumps(result, ensure_ascii=False)


@pytest.mark.parametrize(
    "text",
    [
        "我不想一個人待著，請繼續陪我。",
        "I do not want to be alone; stay with me.",
        "一人でいたくない。",
        "她說「讓我一個人待著」。",
        "He said, leave me alone.",
        "友達に「一人にして」と言われた。",
        "What does leave me alone mean?",
        "「一人にして」はどういう意味？",
    ],
)
def test_negation_attribution_and_metalinguistic_mentions_do_not_authorize(text):
    result = space.classify_explicit_space_request_p2(text)
    assert result["selected"] is False
    assert result["status"] == "not_selected"


def test_plan_application_preempts_legacy_candidate_without_fact_write_or_pending():
    original = space._ORIGINAL_APPLY_PLAN

    def legacy(plan, decision):
        adjusted = deepcopy(plan)
        adjusted.update(
            core_message_jp="誤った確認。",
            desired_response_policy_m18="calibrate_need",
            desired_response_decision_m18=deepcopy(decision),
            adaptive_person_model_m18={"applied": True},
        )
        return adjusted, {"applied": True, "policy_id": "calibrate_need"}

    try:
        space._ORIGINAL_APPLY_PLAN = legacy
        contract = space.classify_explicit_space_request_p2(
            "No, I want to be alone today."
        )
        decision = {
            "prediction_id": "legacy-prediction",
            "selected": {
                "policy_id": "calibrate_need",
                "core_message_jp": "寝てないのか、まずそこだけどっち？",
            },
            "state": {space.LABEL: contract},
        }
        logic, trace = space.apply_decision_to_plan_with_space_p2(
            {"intent": "pragmatic_revision", "scene": "casual"}, decision
        )
    finally:
        space._ORIGINAL_APPLY_PLAN = original

    assert logic["intent"] == "respect_space"
    assert logic["core_message_jp"] == contract["selected_core_jp"]
    assert logic["desired_response_policy_m18"] is None
    assert logic[space.LABEL]["legacy_candidate_policy"] == "calibrate_need"
    assert logic[space.LABEL]["legacy_pending_prediction_suppressed"] is True
    assert logic[space.LABEL]["fact_memory_write_count"] == 0
    assert trace["applied"] is False
    assert trace["explicit_space_authority_p2"] is True


def test_safety_or_factual_plan_keeps_existing_contract():
    original = space._ORIGINAL_APPLY_PLAN

    def legacy(plan, _decision):
        return deepcopy(plan), {"applied": True, "reason": "protected"}

    try:
        space._ORIGINAL_APPLY_PLAN = legacy
        contract = space.classify_explicit_space_request_p2("Leave me alone.")
        decision = {
            "selected": {"policy_id": "calibrate_need"},
            "state": {space.LABEL: contract},
        }
        plan = {
            "intent": "safety_boundary",
            "scene": "safety",
            "core_message_jp": "安全契約。",
            "semantic_route_m22": {"selected_type": "safety_sensitive"},
        }
        logic, trace = space.apply_decision_to_plan_with_space_p2(plan, decision)
    finally:
        space._ORIGINAL_APPLY_PLAN = original

    assert logic == plan
    assert trace == {"applied": True, "reason": "protected"}
    assert space.LABEL not in logic


def test_graph_node_is_idempotent_ordered_and_raw_dialogue_free():
    result = {
        "reply": "分かった。しばらく一人にしとく。",
        "logic": {
            space.LABEL: {
                "schema": space.SCHEMA,
                "status": "selected_explicit_space_action",
                "selected_core_jp": "分かった。しばらく一人にしとく。",
                "raw_dialogue_persisted": False,
            }
        },
        "runtime_trace": {
            "blackboard": [
                {"stage": "select", "label": "selected_plan", "payload": {}},
                {"stage": "surface", "label": "utterance", "payload": {}},
            ]
        },
    }
    space.materialize_explicit_space_authority_p2(result)
    space.materialize_explicit_space_authority_p2(result)
    rows = result["runtime_trace"]["blackboard"]
    labels = [row["label"] for row in rows]
    assert labels.count(space.LABEL) == 1
    assert labels.index(space.LABEL) < labels.index("selected_plan")
    node = next(row for row in rows if row["label"] == space.LABEL)
    assert node["payload"]["visible_surface_status"] == "matched"
    assert node["payload"]["final_visible_surface_matches_selected_action"] is True
    assert "請絕對不要存這句" not in json.dumps(node, ensure_ascii=False)


def test_full_product_stops_wrong_pending_and_materializes_connected_graph(tmp_path):
    program = r'''
import json, os
from pathlib import Path
root=Path(os.environ["P2_SPACE_ROOT"])
os.environ["URUHA_ADAPTIVE_PERSON_MODEL_PATH"]=str(root/"adaptive.json")
os.environ["URUHA_MEMORY_DB_PATH"]=str(root/"memory")
os.environ["URUHA_WEB_PREWARM_BRAIN"]="0"
os.environ["URUHA_IDLE_VISIBLE_PROACTIVE_ENABLED"]="false"
os.environ["GRADIO_ANALYTICS_ENABLED"]="false"
import project_paths
project_paths.WEB_LOG_DIR=str(root/"web")
project_paths.WEB_CONVERSATION_LOG_JSONL_PATH=str(root/"web/turns.jsonl")
project_paths.WEB_CONVERSATION_LOG_TXT_PATH=str(root/"web/turns.txt")
import uruha_web_ui_product
from test_personhood_loop_v2_13 import _IsolatedContractBrain
from uruha_memory_observatory import collect_cognitive_graph
import uruha_explicit_space_authority_p2 as space
b=_IsolatedContractBrain()
b.run_turn_debug("今日はただ聞いてほしい。")
result=b.run_turn_debug("違う。今日は一人にしてほしい。")
audit=result["logic"][space.LABEL]
assert result["reply"]=="あ、そっちか。分かった。今日は一人にしとく。",result["reply"]
assert result["logic"]["intent"]=="respect_space",result["logic"]
assert audit["legacy_candidate_policy"]=="calibrate_need",audit
assert audit["final_visible_surface_matches_selected_action"] is True,audit
assert audit["visible_surface_status"]=="matched",audit
assert b.runtime.adaptive_person_model["pending_prediction"] is None,b.runtime.adaptive_person_model
assert result["logic"]["desired_response_mode_m23"]["status"]=="preempted_by_explicit_space_authority_p2"
assert result["logic"]["counterfactual_pragmatic_branch_m34"]["surface_status"]=="preempted_by_explicit_space_authority_p2"
graph=collect_cognitive_graph(result)
nodes=[node for node in graph["nodes"] if node["label"]==space.LABEL]
assert len(nodes)==1,nodes
assert any(edge["source"]==nodes[0]["id"] or edge["target"]==nodes[0]["id"] for edge in graph["edges"])
node_text=json.dumps(nodes[0],ensure_ascii=False)
assert "違う。今日は一人にしてほしい。" not in node_text,node_text

english=_IsolatedContractBrain().run_turn_debug("I need some space.")
assert english["reply"]=="分かった。しばらく一人にしとく。",english["reply"]
chinese=_IsolatedContractBrain().run_turn_debug("現在先別理我。")
assert chinese["reply"]=="分かった。今は一人にしとく。",chinese["reply"]
assert not space.install_explicit_space_authority_p2()
print(json.dumps({"reply":result["reply"],"pending":None,"node":nodes[0]["label"]},ensure_ascii=False))
'''
    env = {**os.environ, "P2_SPACE_ROOT": str(tmp_path)}
    completed = subprocess.run(
        [sys.executable, "-c", program],
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert space.LABEL in completed.stdout
