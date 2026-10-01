"""Contracts for pre-choice P4 profile plan authority, not a product holdout."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

import uruha_explicit_preference_acknowledgement_p4 as p4h
import uruha_profile_write_ack_truth_p4 as ack
import uruha_profile_plan_authority_repair_p4 as repair
from test_p4_profile_write_ack_truth import guard_chain, writer_chain, _real_result


FRIEND = "友人からの伝言。今は棗茶が好き。今の好みとして覚えといて。"
SELF = "今は柚葉茶が好き。今の飲み物の好みとして覚えといて。"
ORDINARY = "今日は散歩してきた。"


@pytest.fixture
def projection_candidate():
    return {
        "schema": "uruha_literal_topic_projection_candidate_m29",
        "status": "projection_candidate",
        "reason": "fresh_self_contained_literal_topic_requires_grounded_projection",
        "projection_required": True,
        "surface_authority": False,
        "input_digest": "synthetic",
        "raw_dialogue_persisted": False,
    }


@pytest.mark.parametrize("source", [FRIEND, SELF])
def test_selected_profile_act_vetoes_generic_literal_projection(projection_candidate, source):
    preflight = ack.preflight_profile_write_ack_p4(source)
    assert preflight["selected"] is True
    observed = repair.veto_m29_candidate_for_profile_memory_act_p4(
        projection_candidate, source, preflight
    )
    assert observed["status"] == "superseded_by_profile_memory_act_p4"
    assert observed["projection_required"] is False
    assert observed["surface_authority"] is False
    assert observed["pre_veto_status"] == "projection_candidate"
    assert observed["pre_veto_reason"] == projection_candidate["reason"]
    assert observed["pre_veto_projection_required"] is True
    assert observed["profile_input_sha256"] == preflight["input_sha256"]
    assert observed["profile_memory_act"] == "write"
    assert observed["raw_dialogue_persisted"] is False
    assert projection_candidate["projection_required"] is True


def test_nontarget_protected_and_nonprojection_keep_old_candidate(projection_candidate):
    ordinary_preflight = ack.preflight_profile_write_ack_p4(ORDINARY)
    assert ordinary_preflight["selected"] is False
    assert repair.veto_m29_candidate_for_profile_memory_act_p4(
        projection_candidate, ORDINARY, ordinary_preflight
    ) == projection_candidate
    selected_preflight = ack.preflight_profile_write_ack_p4(FRIEND)
    assert repair.veto_m29_candidate_for_profile_memory_act_p4(
        projection_candidate, FRIEND, selected_preflight, protected=True
    ) == projection_candidate
    no_projection = {**projection_candidate, "projection_required": False}
    assert repair.veto_m29_candidate_for_profile_memory_act_p4(
        no_projection, FRIEND, selected_preflight
    ) == no_projection


def test_hash_mismatch_cannot_veto_unrelated_candidate(projection_candidate):
    other = ack.preflight_profile_write_ack_p4(SELF)
    assert repair.veto_m29_candidate_for_profile_memory_act_p4(
        projection_candidate, FRIEND, other
    ) == projection_candidate


def test_protected_decision_uses_only_this_turns_signal():
    assert repair._protected_before_m29({}) is True
    assert repair._protected_before_m29({
        "actual_signal": {
            "actual_intent": "profile_write_ack_rejected",
            "actual_scene": "casual",
            "abuse_like": False,
            "seed_plan": {"intent": "profile_write_ack_rejected", "scene": "casual"},
        }
    }) is False
    assert repair._protected_before_m29({
        "actual_signal": {
            "actual_intent": "crisis_support",
            "actual_scene": "support",
            "abuse_like": False,
            "seed_plan": {"intent": "crisis_support", "scene": "support"},
        }
    }) is True


def test_wrong_role_selected_plan_cannot_hide_behind_truthful_final(
    writer_chain, guard_chain, monkeypatch
):
    """The exact previous failure class must flip truth to mismatch."""
    monkeypatch.setattr(
        repair, "_ORIGINAL_ACK_MATERIALIZE", ack.materialize_profile_write_ack_truth_p4
    )
    logic = {"visible_language_guard": {"original_reply": "友達の話なんだね。"}}
    reply = ack.visible_guard_with_profile_write_ack_truth_p4(
        object(), "友達の話なんだね。", logic, user_input=FRIEND, memory_data={}
    )
    wrong_intent = "deterministic_semantic_commit_m32"
    wrong_core = "今は棗茶が好きであるんだね。"
    logic.update(intent=wrong_intent, core_message_jp=wrong_core)
    brain, result = _real_result(writer_chain, FRIEND, reply, logic)
    result["runtime_trace"]["blackboard"].insert(
        0,
        {
            "stage": "select",
            "label": "selected_plan",
            "payload": {"intent": wrong_intent, "core_message_jp": wrong_core},
        },
    )
    repair.materialize_profile_plan_authority_repair_p4(brain, result)
    truth = result["logic"][ack.LABEL]
    assert truth["status"] == "mismatch"
    assert truth["checks"]["selected_plan_authority"] == "mismatch"
    assert truth["selected_plan_authority"]["actual_selected_intent"] == wrong_intent
    assert result["reply"] == ack.NON_COMMITMENT_REPLY
    assert writer_chain.episode_col.count() == 1
    assert writer_chain.profile_col.count() == 0
    with pytest.raises(ack.ProfileWriteAckIntegrityError, match="mismatch"):
        ack.require_matched_profile_write_ack_p4(result)


def test_no_model_full_brain_selected_plan_and_truth_node_share_authority(tmp_path):
    """Actual cognitive_tick/emit path, with only LLM surface replaced by a stub."""
    program = r'''
import json, os
from pathlib import Path
root=Path(os.environ["P4_PLAN_TEST_ROOT"])
os.environ["URUHA_ADAPTIVE_PERSON_MODEL_PATH"]=str(root/"adaptive.json")
os.environ["URUHA_MEMORY_DB_PATH"]=str(root/"memory")
os.environ["URUHA_WEB_PREWARM_BRAIN"]="0"
os.environ["URUHA_IDLE_VISIBLE_PROACTIVE_ENABLED"]="false"
os.environ["GRADIO_ANALYTICS_ENABLED"]="false"
import project_paths
project_paths.WEB_LOG_DIR=str(root/"web")
project_paths.WEB_CONVERSATION_LOG_JSONL_PATH=str(root/"web/turns.jsonl")
project_paths.WEB_CONVERSATION_LOG_TXT_PATH=str(root/"web/turns.txt")
import uruha_web_ui_product_p4_profile_plan as entry
from test_personhood_loop_v2_13 import _IsolatedContractBrain
from uruha_brain_mac import LeftBrain, MemoryManager, RightBrain
import uruha_profile_write_ack_truth_p4 as ack
import uruha_profile_plan_authority_repair_p4 as repair
import uruha_explicit_preference_acknowledgement_p4 as p4h
brain=_IsolatedContractBrain()
brain.memory=MemoryManager()
brain.left_brain=LeftBrain(None)
brain.right_brain=RightBrain(load_model=False)
brain.right_brain.speak=lambda user_input,logic,memory_data,psyche: str(logic.get("core_message_jp") or "ん。")
for text,expect_intent,expect_core,expect_delta in [
    ("友人からの伝言。今は棗茶が好き。今の好みとして覚えといて。", "profile_write_ack_rejected", ack.NON_COMMITMENT_REPLY, 0),
    ("今は柚葉茶が好き。今の飲み物の好みとして覚えといて。", "explicit_preference_memory_write", p4h.AUTHORITATIVE_SURFACES["write"], 1),
]:
    before=brain.memory.profile_col.count()
    result=brain.run_turn_debug(text)
    rows=[r for r in result["runtime_trace"]["blackboard"] if r.get("label")=="selected_plan"]
    assert len(rows)==1,rows
    assert rows[0]["payload"]["intent"]==expect_intent,rows[0]
    assert rows[0]["payload"]["core_message_jp"]==expect_core,rows[0]
    assert result["logic"]["intent"]==expect_intent,result["logic"]["intent"]
    assert result["logic"]["core_message_jp"]==expect_core,result["logic"].get("core_message_jp")
    assert result["reply"]==expect_core,result["reply"]
    truth=result["logic"][ack.LABEL]
    assert truth["status"]=="matched",truth
    assert truth["checks"]["selected_plan_authority"]=="matched",truth
    if expect_delta==0:
        projection=result["logic"]["literal_topic_projection_m29"]
        assert projection["status"]=="superseded_by_profile_memory_act_p4",projection
        assert projection["pre_veto_projection_required"] is True,projection
    assert brain.memory.profile_col.count()-before==expect_delta
    assert len([r for r in result["runtime_trace"]["blackboard"] if r.get("label")==ack.LABEL])==1
assert brain.memory.episode_col.count()==2
assert entry.RUNTIME is entry._prior.RUNTIME
print(json.dumps({"status":"matched","turns":2,"profile_rows":brain.memory.profile_col.count()}))
'''
    completed = subprocess.run(
        [sys.executable, "-c", program],
        env={**os.environ, "P4_PLAN_TEST_ROOT": str(tmp_path)},
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert '"status": "matched"' in completed.stdout
