"""Developer regressions for bounded shared-amusement surface authority."""

from copy import deepcopy
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

import uruha_shared_amusement_authority_p3 as amusement


@pytest.mark.parametrize(
    ("text", "language"),
    [
        ("我不是要你給建議，只希望你跟我一起笑。", "zh"),
        ("I don't need advice; just laugh at it with me.", "en"),
        ("助けはいらないよ。一緒に笑ってほしいだけ。", "ja"),
    ],
)
def test_source_disjoint_multilingual_explicit_requests_are_selected_without_raw_text(
    text,
    language,
):
    result = amusement.classify_shared_amusement_authority_p3(text)
    serialized = json.dumps(result, ensure_ascii=False)
    assert result["selected"] is True
    assert result["status"] == "explicit_shared_amusement_authorized"
    assert result["language"] == language
    assert result["observable_cues"] == [
        "explicit_no_solve_or_no_trouble",
        "direct_shared_amusement_request",
    ]
    assert result["authority"] == "current_explicit_desired_response"
    assert result["fact_memory_write_count"] == 0
    assert result["raw_dialogue_persisted"] is False
    assert text not in serialized


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("笑ってください。", "required_clause_missing"),
        ("別に困ってない、ただ笑ってほしくない。", "shared_amusement_negated"),
        (
            "台本の例：別に困ってない、ただ笑ってほしかっただけ。",
            "metalinguistic_or_quoted_context",
        ),
        (
            "彼女は困ってない、ただ笑ってほしかっただけ。",
            "third_person_report",
        ),
        (
            "VRMモデルは困ってない。モデルを笑わせて。",
            "action_or_avatar_expression_command",
        ),
        (
            "死にたい。でも困ってない、ただ笑ってほしかっただけ。",
            "protected_risk_cue",
        ),
        ("猫が箱を落として笑った。", "required_clause_missing"),
    ],
)
def test_ambiguous_negated_quoted_third_party_action_and_risk_inputs_do_not_select(
    text,
    reason,
):
    result = amusement.classify_shared_amusement_authority_p3(text)
    assert result["selected"] is False
    assert result["status"] == "not_selected"
    assert result["reason"] == reason


def test_case06_exposed_wording_selects_bounded_natural_japanese_surface():
    contract = amusement.build_shared_amusement_contract_p3(
        "別に困ってない、ただ笑ってほしかっただけ。"
    )
    assert contract["selected"] is True
    assert contract["selected_core_jp"] == amusement._SELECTED_CORE_JP
    assert "聞かせて" not in contract["selected_core_jp"]
    assert "手伝" not in contract["selected_core_jp"]
    assert "？" not in contract["selected_core_jp"]
    assert "?" not in contract["selected_core_jp"]
    assert not re.search(r"[A-Za-z]", contract["selected_core_jp"])
    assert contract["must_not"] == [
        "ask_follow_up_question",
        "offer_problem_solving",
        "continue_previous_problem",
        "invent_event_details",
    ]


def test_rule_plan_delegates_nonmatch_and_visible_authority_never_overrides_safety():
    original_plan = amusement._ORIGINAL_RULE_PLAN
    original_guard = amusement._ORIGINAL_VISIBLE_GUARD
    sentinel = {"intent": "legacy", "core_message_jp": "そのまま。"}

    def legacy_plan(_self, _text, _psyche, _memory=None):
        return deepcopy(sentinel)

    def legacy_guard(_self, reply, logic, **_kwargs):
        logic["visible_language_guard"] = {"final_reply": reply}
        return reply

    try:
        amusement._ORIGINAL_RULE_PLAN = legacy_plan
        amusement._ORIGINAL_VISIBLE_GUARD = legacy_guard
        selected = amusement.rule_plan_with_shared_amusement_p3(
            object(),
            "I'm not asking you for help; I just wanted you to laugh.",
            {},
            {},
        )
        delegated = amusement.rule_plan_with_shared_amusement_p3(
            object(), "猫が箱を落とした。", {}, {}
        )
        logic = {"semantic_route_m22": {"selected_type": "general_conversation"}}
        visible = amusement.visible_guard_with_shared_amusement_p3(
            object(),
            "壊れた候補。",
            logic,
            user_input="別に困ってない、ただ笑ってほしかっただけ。",
        )
        protected = {"semantic_route_m22": {"selected_type": "safety_sensitive"}}
        protected_visible = amusement.visible_guard_with_shared_amusement_p3(
            object(),
            "安全側の返答。",
            protected,
            user_input="別に困ってない、ただ笑ってほしかっただけ。",
        )
    finally:
        amusement._ORIGINAL_RULE_PLAN = original_plan
        amusement._ORIGINAL_VISIBLE_GUARD = original_guard

    assert selected["planner_path"] == "explicit_shared_amusement_authority_p3"
    assert selected["core_message_jp"] == amusement._SELECTED_CORE_JP
    assert delegated == sentinel
    assert visible == amusement._SELECTED_CORE_JP
    assert logic["shared_amusement_contract_p3"]["final_visible_surface_matches_contract"] is True
    assert logic["explicit_desired_response_m25"][amusement.LABEL]["surface_status"] == "matched"
    assert logic["desired_response_mode_m23"][amusement.LABEL]["selected_mode"] == "shared_amusement"
    assert protected_visible == "安全側の返答。"
    assert "shared_amusement_contract_p3" not in protected


def test_graph_node_is_idempotent_ordered_and_raw_free():
    raw = "I don't need advice; just laugh at it with me."
    contract = amusement.build_shared_amusement_contract_p3(raw)
    result = {
        "reply": contract["selected_core_jp"],
        "logic": {"shared_amusement_contract_p3": contract},
        "runtime_trace": {
            "blackboard": [
                {"stage": "reason", "label": "desired_response_mode_m23", "payload": {}},
                {"stage": "select", "label": "selected_plan", "payload": {}},
                {"stage": "surface", "label": "utterance", "payload": {}},
            ]
        },
    }
    amusement.materialize_shared_amusement_p3(result)
    amusement.materialize_shared_amusement_p3(result)
    labels = [row["label"] for row in result["runtime_trace"]["blackboard"]]
    assert labels.count(amusement.LABEL) == 1
    assert labels.index("desired_response_mode_m23") < labels.index(amusement.LABEL)
    assert labels.index(amusement.LABEL) < labels.index("selected_plan")
    assert raw not in json.dumps(result["runtime_trace"][amusement.LABEL], ensure_ascii=False)


def test_isolated_product_runtime_repairs_case06_and_materializes_connected_graph(tmp_path):
    program = r'''
import json, os, re
from pathlib import Path
root=Path(os.environ["P3_AMUSE_ROOT"])
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
from uruha_brain_mac import LeftBrain, RightBrain
from uruha_memory_observatory import collect_cognitive_graph
import uruha_shared_amusement_authority_p3 as amusement
b=_IsolatedContractBrain()
b.left_brain=LeftBrain(None)
b.right_brain=RightBrain(load_model=False)
b.right_brain.speak=lambda user_input, logic, memory_data, psyche: str(logic.get("core_message_jp") or "まだ分かんない。")
b.run_turn_debug("あれ、やっぱり違うかも。")
b.run_turn_debug("さっき言ってた『今週中に決める』って件、旅行じゃなくて部屋探しのこと。")
b.run_turn_debug("その話はいったん置いといて。今日は猫が棚から箱を落とした。")
result=b.run_turn_debug("別に困ってない、ただ笑ってほしかっただけ。")
contract=result["logic"]["shared_amusement_contract_p3"]
assert result["reply"]==amusement._SELECTED_CORE_JP,result["reply"]
assert contract["status"]=="explicit_shared_amusement_authorized",contract
assert contract["final_visible_surface_matches_contract"] is True,contract
assert result["logic"]["bounded_slow_path_m21"]["model_call_attempted"] is False
assert result["logic"]["explicit_desired_response_m25"][amusement.LABEL]["surface_status"]=="matched"
assert result["logic"]["desired_response_mode_m23"][amusement.LABEL]["selected_mode"]=="shared_amusement"
assert not re.search(r"[A-Za-z]",result["reply"]),result["reply"]
assert all(token not in result["reply"] for token in ("聞かせて","手伝","？","?")),result["reply"]
graph=collect_cognitive_graph(result)
nodes=[node for node in graph["nodes"] if node["label"]==amusement.LABEL]
assert len(nodes)==1,nodes
assert any(edge["source"]==nodes[0]["id"] or edge["target"]==nodes[0]["id"] for edge in graph["edges"])
raw="別に困ってない、ただ笑ってほしかっただけ。"
assert raw not in json.dumps(nodes[0],ensure_ascii=False)
writes=result["runtime_trace"].get("memory_writes") or []
assert all(row.get("kind")=="turn_episode" for row in writes),writes
assert contract["fact_memory_write_count"]==0
generic=_IsolatedContractBrain()
generic.left_brain=LeftBrain(None)
generic.right_brain=RightBrain(load_model=False)
generic.right_brain.speak=lambda user_input, logic, memory_data, psyche: str(logic.get("core_message_jp") or "まだ分かんない。")
action=generic.run_turn_debug("笑ってください。")
assert action["logic"].get("shared_amusement_contract_p3") is None,action["logic"]
assert not amusement.install_shared_amusement_authority_p3()
print(json.dumps({"reply":result["reply"],"node":nodes[0]["label"],"fact_writes":0},ensure_ascii=False))
'''
    env = {**os.environ, "P3_AMUSE_ROOT": str(tmp_path)}
    completed = subprocess.run(
        [sys.executable, "-c", program],
        env=env,
        check=True,
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parent,
        timeout=180,
    )
    assert amusement.LABEL in completed.stdout
