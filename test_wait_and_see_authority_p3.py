"""Regressions for explicit neutral wait-and-see authority."""

from copy import deepcopy
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

import uruha_wait_and_see_authority_p3 as waiting


@pytest.mark.parametrize(("text", "language"), [
    ("不要安慰我說一定有希望，陪我一起整理成先觀望。", "zh"),
    ("Don't reassure me it'll be fine; let's call it wait and see.", "en"),
    ("期待していいって励ますより、今回は様子見って一緒に整理して。", "ja"),
])
def test_multilingual_explicit_requests_select_without_raw_dialogue(text, language):
    result = waiting.classify_wait_and_see_authority_p3(text)
    assert result["selected"] is True
    assert result["language"] == language
    assert result["observable_cues"] == ["explicit_no_false_reassurance", "joint_wait_and_see_request"]
    assert result["model_call_added"] is False
    assert result["fact_memory_write_count"] == 0
    assert text not in json.dumps(result, ensure_ascii=False)


@pytest.mark.parametrize(("text", "reason"), [
    ("今回は様子見で。", "required_clause_missing"),
    ("期待していいって励まして。様子見にはしないで。", "wait_and_see_negated"),
    ("台本の例：期待していいって励ますより、今回は様子見って一緒に整理して。", "metalinguistic_or_quoted_context"),
    ("彼女は励まさないで様子見にしてと言った。", "third_person_report"),
    ("VRMモデルを様子見モードにして。", "action_or_avatar_command"),
    ("死にたい。期待させず様子見にして。", "protected_risk_cue"),
    ("前にも一か月空いた。", "required_clause_missing"),
])
def test_incomplete_negated_meta_third_party_action_and_risk_fail_closed(text, reason):
    result = waiting.classify_wait_and_see_authority_p3(text)
    assert result["selected"] is False
    assert result["reason"] == reason


def test_b42_wording_selects_neutral_japanese_without_outcome_claim():
    contract = waiting.build_wait_and_see_contract_p3(
        "期待していいって励ますより、今回は様子見って一緒に整理して。"
    )
    reply = contract["selected_core_jp"]
    assert reply == waiting._SELECTED_CORE_JP
    assert "様子見" in reply
    assert "期待していいとも断られたとも決めず" in reply
    assert all(token not in reply for token in ("絶対", "きっと", "脈あり", "振られた"))
    assert not re.search(r"[A-Za-z]", reply)


def test_plan_surface_safety_and_graph_contract():
    original_plan, original_guard = waiting._ORIGINAL_RULE_PLAN, waiting._ORIGINAL_VISIBLE_GUARD
    sentinel = {"intent": "legacy", "core_message_jp": "そのまま。"}
    def legacy_plan(_self, _text, _psyche, _memory=None): return deepcopy(sentinel)
    def legacy_guard(_self, reply, logic, **_kwargs):
        logic["visible_language_guard"] = {"final_reply": reply}
        return reply
    try:
        waiting._ORIGINAL_RULE_PLAN, waiting._ORIGINAL_VISIBLE_GUARD = legacy_plan, legacy_guard
        selected = waiting.rule_plan_with_wait_and_see_p3(object(), "期待していいって励ますより、今回は様子見って一緒に整理して。", {}, {})
        delegated = waiting.rule_plan_with_wait_and_see_p3(object(), "前にも一か月空いた。", {}, {})
        logic = {"semantic_route_m22": {"selected_type": "general_conversation"}}
        visible = waiting.visible_guard_with_wait_and_see_p3(object(), "壊れた候補。", logic, user_input="期待していいって励ますより、今回は様子見って一緒に整理して。")
        protected = {"semantic_route_m22": {"selected_type": "safety_sensitive"}}
        safe = waiting.visible_guard_with_wait_and_see_p3(object(), "安全側。", protected, user_input="死にたい。期待させず様子見にして。")
    finally:
        waiting._ORIGINAL_RULE_PLAN, waiting._ORIGINAL_VISIBLE_GUARD = original_plan, original_guard
    assert selected["planner_path"] == "explicit_wait_and_see_authority_p3"
    assert delegated == sentinel
    assert visible == waiting._SELECTED_CORE_JP
    assert safe == "安全側。"
    assert logic["explicit_desired_response_m25"][waiting.LABEL]["surface_status"] == "matched"
    assert logic["desired_response_mode_m23"][waiting.LABEL]["selected_mode"] == "neutral_wait_and_see"
    contract = waiting.build_wait_and_see_contract_p3("期待していいって励ますより、今回は様子見って一緒に整理して。")
    result = {"reply": contract["selected_core_jp"], "logic": {"wait_and_see_contract_p3": contract}, "runtime_trace": {"blackboard": [{"stage": "select", "label": "selected_plan", "payload": {}}]}}
    waiting.materialize_wait_and_see_p3(result)
    waiting.materialize_wait_and_see_p3(result)
    labels = [row["label"] for row in result["runtime_trace"]["blackboard"]]
    assert labels.count(waiting.LABEL) == 1
    assert labels.index(waiting.LABEL) < labels.index("selected_plan")


def test_isolated_product_replays_b42_and_materializes_graph_without_fact_write(tmp_path):
    program = r'''
import json, os, re
from pathlib import Path
root=Path(os.environ["P3_WAIT_ROOT"])
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
import uruha_wait_and_see_authority_p3 as waiting
b=_IsolatedContractBrain(); b.left_brain=LeftBrain(None); b.right_brain=RightBrain(load_model=False)
b.right_brain.speak=lambda user_input, logic, memory_data, psyche: str(logic.get("core_message_jp") or "まだ分かんない。")
b.run_turn_debug("昨日、先輩に「また今度ゆっくり話そう」って言われた。")
b.run_turn_debug("断られたって決めつけたいわけじゃない。")
b.run_turn_debug("でも前にも同じことを言われて、そのまま一か月空いた。")
result=b.run_turn_debug("期待していいって励ますより、今回は様子見って一緒に整理して。")
contract=result["logic"]["wait_and_see_contract_p3"]
assert result["reply"]==waiting._SELECTED_CORE_JP,result["reply"]
assert contract["final_visible_surface_matches_contract"] is True
assert result["logic"]["bounded_slow_path_m21"]["model_call_attempted"] is False
assert result["logic"]["desired_response_mode_m23"][waiting.LABEL]["selected_mode"]=="neutral_wait_and_see"
graph=collect_cognitive_graph(result)
nodes=[node for node in graph["nodes"] if node["label"]==waiting.LABEL]
assert len(nodes)==1,nodes
assert any(edge["source"]==nodes[0]["id"] or edge["target"]==nodes[0]["id"] for edge in graph["edges"])
raw="期待していいって励ますより、今回は様子見って一緒に整理して。"
assert raw not in json.dumps(nodes[0],ensure_ascii=False)
writes=result["runtime_trace"].get("memory_writes") or []
assert all(row.get("kind")=="turn_episode" for row in writes),writes
assert contract["fact_memory_write_count"]==0
assert not waiting.install_wait_and_see_authority_p3()
print(json.dumps({"reply":result["reply"],"node":nodes[0]["label"]},ensure_ascii=False))
'''
    completed = subprocess.run([sys.executable, "-c", program], env={**os.environ, "P3_WAIT_ROOT": str(tmp_path)}, check=True, capture_output=True, text=True, cwd=Path(__file__).resolve().parent, timeout=180)
    assert waiting.LABEL in completed.stdout

