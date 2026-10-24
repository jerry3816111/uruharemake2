"""Developer regressions for bounded explicit playful-guess authority."""

from copy import deepcopy
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

import uruha_playful_guess_authority_p3 as guessing


@pytest.mark.parametrize(("text", "language"), [
    ("不用安慰我，我很興奮。猜猜我第一張會拍什麼。", "zh"),
    ("Don't calm me down—I'm thrilled. Guess what I'm going to photograph first.", "en"),
    ("心配じゃなくて楽しみなんだ。うちが最初に何を撮るか当てて。", "ja"),
])
def test_source_disjoint_multilingual_requests_select_without_raw_text(text, language):
    result = guessing.classify_playful_guess_authority_p3(text)
    assert result["selected"] is True
    assert result["status"] == "explicit_playful_guess_authorized"
    assert result["language"] == language
    assert result["observable_cues"] == [
        "explicit_positive_arousal_or_no_calm",
        "first_person_photography_guess_invitation",
    ]
    assert result["model_call_added"] is False
    assert result["fact_memory_write_count"] == 0
    assert text not in json.dumps(result, ensure_ascii=False)


@pytest.mark.parametrize(("text", "reason"), [
    ("Guess what I'm going to photograph first.", "required_clause_missing"),
    ("I'm excited, but don't guess what I'll photograph.", "guess_negated"),
    ("Script example: I'm excited. Guess what I'm going to photograph first.", "metalinguistic_or_quoted_context"),
    ("She is excited and asked you to guess what she will photograph first.", "third_person_report"),
    ("Make the VRM camera function guess what I'll photograph first.", "action_or_avatar_command"),
    ("I want to die. I'm excited; guess what I'm going to photograph first.", "protected_risk_cue"),
    ("I'm excited that my camera arrives tomorrow.", "required_clause_missing"),
])
def test_negated_meta_third_party_action_risk_and_incomplete_fail_closed(text, reason):
    result = guessing.classify_playful_guess_authority_p3(text)
    assert result["selected"] is False
    assert result["status"] == "not_selected"
    assert result["reason"] == reason


def test_b38_wording_selects_one_tentative_japanese_guess():
    contract = guessing.build_playful_guess_contract_p3(
        "Don't calm me down—I'm excited. Guess what I'm going to photograph first."
    )
    assert contract["selected"] is True
    assert contract["selected_core_jp"] == guessing._SELECTED_CORE_JP
    assert "とか？" in contract["selected_core_jp"]
    assert "予想" in contract["selected_core_jp"]
    assert not re.search(r"[A-Za-z]", contract["selected_core_jp"])
    assert contract["must_not"] == [
        "calm_user_down",
        "ask_user_to_supply_answer_instead",
        "state_guess_as_fact",
        "write_guess_as_memory",
    ]


def test_plan_delegates_nonmatch_and_surface_never_overrides_safety():
    original_plan = guessing._ORIGINAL_RULE_PLAN
    original_guard = guessing._ORIGINAL_VISIBLE_GUARD
    sentinel = {"intent": "legacy", "core_message_jp": "そのまま。"}

    def legacy_plan(_self, _text, _psyche, _memory=None):
        return deepcopy(sentinel)

    def legacy_guard(_self, reply, logic, **_kwargs):
        logic["visible_language_guard"] = {"final_reply": reply}
        return reply

    try:
        guessing._ORIGINAL_RULE_PLAN = legacy_plan
        guessing._ORIGINAL_VISIBLE_GUARD = legacy_guard
        selected = guessing.rule_plan_with_playful_guess_p3(
            object(), "Don't calm me down—I'm excited. Guess what I'm going to photograph first.", {}, {}
        )
        delegated = guessing.rule_plan_with_playful_guess_p3(object(), "The camera arrives tomorrow.", {}, {})
        logic = {"semantic_route_m22": {"selected_type": "general_conversation"}}
        visible = guessing.visible_guard_with_playful_guess_p3(
            object(), "壊れた候補。", logic,
            user_input="Don't calm me down—I'm excited. Guess what I'm going to photograph first.",
        )
        protected = {"semantic_route_m22": {"selected_type": "safety_sensitive"}}
        safe = guessing.visible_guard_with_playful_guess_p3(
            object(), "安全側の返答。", protected,
            user_input="I want to die. I'm excited. Guess what I'm going to photograph first.",
        )
    finally:
        guessing._ORIGINAL_RULE_PLAN = original_plan
        guessing._ORIGINAL_VISIBLE_GUARD = original_guard

    assert selected["planner_path"] == "explicit_playful_guess_authority_p3"
    assert delegated == sentinel
    assert visible == guessing._SELECTED_CORE_JP
    assert logic["playful_guess_contract_p3"]["final_visible_surface_matches_contract"] is True
    assert logic["explicit_desired_response_m25"][guessing.LABEL]["surface_status"] == "matched"
    assert logic["desired_response_mode_m23"][guessing.LABEL]["selected_mode"] == "playful_tentative_guess"
    assert safe == "安全側の返答。"
    assert "playful_guess_contract_p3" not in protected


def test_graph_node_is_idempotent_ordered_and_raw_free():
    raw = "Don't calm me down—I'm excited. Guess what I'm going to photograph first."
    contract = guessing.build_playful_guess_contract_p3(raw)
    result = {
        "reply": contract["selected_core_jp"],
        "logic": {"playful_guess_contract_p3": contract},
        "runtime_trace": {"blackboard": [
            {"stage": "reason", "label": "desired_response_mode_m23", "payload": {}},
            {"stage": "select", "label": "selected_plan", "payload": {}},
            {"stage": "surface", "label": "utterance", "payload": {}},
        ]},
    }
    guessing.materialize_playful_guess_p3(result)
    guessing.materialize_playful_guess_p3(result)
    labels = [row["label"] for row in result["runtime_trace"]["blackboard"]]
    assert labels.count(guessing.LABEL) == 1
    assert labels.index("desired_response_mode_m23") < labels.index(guessing.LABEL) < labels.index("selected_plan")
    assert raw not in json.dumps(result["runtime_trace"][guessing.LABEL], ensure_ascii=False)


def test_isolated_product_runtime_repairs_b38_four_turn_replay_and_graph(tmp_path):
    program = r'''
import json, os, re
from pathlib import Path
root=Path(os.environ["P3_GUESS_ROOT"])
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
import uruha_playful_guess_authority_p3 as guessing
b=_IsolatedContractBrain()
b.left_brain=LeftBrain(None)
b.right_brain=RightBrain(load_model=False)
b.right_brain.speak=lambda user_input, logic, memory_data, psyche: str(logic.get("core_message_jp") or "まだ分かんない。")
b.run_turn_debug("I kept refreshing the delivery page even though it says tomorrow.")
b.run_turn_debug("Nothing is wrong with the order; I'm waiting for a camera I saved up for.")
b.run_turn_debug("It finally changed to out for delivery this morning.")
result=b.run_turn_debug("Don't calm me down—I'm excited. Guess what I'm going to photograph first.")
contract=result["logic"]["playful_guess_contract_p3"]
assert result["reply"]==guessing._SELECTED_CORE_JP,result["reply"]
assert contract["status"]=="explicit_playful_guess_authorized",contract
assert contract["final_visible_surface_matches_contract"] is True,contract
assert result["logic"]["bounded_slow_path_m21"]["model_call_attempted"] is False
assert result["logic"]["explicit_desired_response_m25"][guessing.LABEL]["surface_status"]=="matched"
assert result["logic"]["desired_response_mode_m23"][guessing.LABEL]["selected_mode"]=="playful_tentative_guess"
assert "予想" in result["reply"] and "とか？" in result["reply"]
assert not re.search(r"[A-Za-z]",result["reply"]),result["reply"]
graph=collect_cognitive_graph(result)
nodes=[node for node in graph["nodes"] if node["label"]==guessing.LABEL]
assert len(nodes)==1,nodes
assert any(edge["source"]==nodes[0]["id"] or edge["target"]==nodes[0]["id"] for edge in graph["edges"])
raw="Don't calm me down—I'm excited. Guess what I'm going to photograph first."
assert raw not in json.dumps(nodes[0],ensure_ascii=False)
writes=result["runtime_trace"].get("memory_writes") or []
assert all(row.get("kind")=="turn_episode" for row in writes),writes
assert contract["fact_memory_write_count"]==0
assert not guessing.install_playful_guess_authority_p3()
print(json.dumps({"reply":result["reply"],"node":nodes[0]["label"],"fact_writes":0},ensure_ascii=False))
'''
    completed = subprocess.run(
        [sys.executable, "-c", program],
        env={**os.environ, "P3_GUESS_ROOT": str(tmp_path)},
        check=True,
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parent,
        timeout=180,
    )
    assert guessing.LABEL in completed.stdout

