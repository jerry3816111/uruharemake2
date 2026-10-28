"""Developer-authored P2 arbitration tests; not holdout or human evidence."""
from copy import deepcopy
import json
import os
import subprocess
import sys

import pytest

import uruha_functional_understanding as understanding
import uruha_personhood_loop as personhood
import uruha_repeated_refusal_arbitration_p2 as arbitration
from test_personhood_loop_v2_13 import build_turn


NO_VERIFICATION = {"status": "not_available"}


def compact_plan(core="じゃあ、また今度な。"):
    return {
        "intent": "chat",
        "scene": "casual",
        "reply_goal": "自然に返す",
        "core_message_jp": core,
        "response_mode": "direct_answer",
        "surface_act": "plain_reply",
        "payload_level": "medium",
        "bounded_slow_path_m21": {
            "schema": "uruha_bounded_slow_path_planner_m21",
            "route": "full_planner",
            "status": "completed_within_budget",
            "model_call_attempted": True,
            "model_call_completed": True,
            "compact_general_plan_p2": {
                "schema": "uruha_compact_general_plan_p2",
                "attempted": True,
                "completed": True,
                "candidate_count": 3,
                "raw_prompt_or_response_persisted": False,
            },
        },
    }


def repeated_pair(previous_text, current_text, core="じゃあ、また今度な。"):
    hypothesis1, pragmatic1 = build_turn(previous_text, 1)
    model, _ = personhood.update_longitudinal_user_model(
        None,
        hypothesis1,
        NO_VERIFICATION,
        NO_VERIFICATION,
        previous_text,
        turn_index=1,
    )
    _, model, _ = personhood.apply_longitudinal_model_to_plan(
        {"intent": "chat", "scene": "casual"}, model, hypothesis1, turn_index=1
    )
    hypothesis2, pragmatic2 = build_turn(current_text, 2)
    general_verification = understanding.verify_previous_hypothesis(
        hypothesis1, current_text, turn_index=2
    )
    pragmatic_verification = personhood.verify_previous_pragmatic_understanding(
        pragmatic1,
        current_text,
        pragmatic2,
        turn_index=2,
    )
    model, update = personhood.update_longitudinal_user_model(
        model,
        hypothesis2,
        general_verification,
        pragmatic_verification,
        current_text,
        turn_index=2,
    )
    base = compact_plan(core)
    proposed = arbitration.apply_repeated_refusal_attunement_p2(
        base,
        pragmatic2,
        hypothesis=hypothesis2,
        pragmatic_verification=pragmatic_verification,
        hypothesis_verification=general_verification,
    )
    return base, proposed, model, hypothesis2, pragmatic_verification, update


@pytest.mark.parametrize(
    "previous_text,current_text,core",
    [
        ("Maybe another time.", "改天再說吧。", "じゃ、またでいいだろ。"),
        ("這週末恐怕排得有點滿，之後有機會再說。", "また今度にしようかな。", "また今度な。"),
        ("考えとく。", "I'll think about it.", "うん、急がなくていい。"),
    ],
)
def test_source_disjoint_repeated_refusal_keeps_each_generated_compact_core(
    previous_text, current_text, core
):
    base, proposed, model, hypothesis, verification, update = repeated_pair(
        previous_text, current_text, core
    )
    assert verification["status"] == "uncertain"
    assert proposed[arbitration.LABEL]["status"] == "candidate_reserved"
    layers_before = deepcopy(model["layers"])
    calibration_before = deepcopy(model["typed_calibration"])
    _, expected_state, _ = personhood.apply_longitudinal_model_to_plan(
        proposed, deepcopy(model), hypothesis, 2
    )

    logic, state, strategy = arbitration.apply_repeated_refusal_arbitration_p2(
        proposed, model, hypothesis, 2
    )

    assert logic["core_message_jp"] == base["core_message_jp"] == core
    assert logic["intent"] == "chat"
    assert strategy["changed_plan"] is False
    assert state["active_validation"]["pending"] is None
    audit = logic[arbitration.LABEL]
    assert audit["status"] == "selected_low_interference_compact_plan"
    assert audit["pragmatic_proposal_suppressed"] is True
    assert audit["new_validation_proposal_suppressed"] is True
    assert audit["validation_proposal"]["kind"] == "pragmatic_implicit_need"
    assert audit["validation_proposal"]["question_jp"]
    assert audit["fact_memory_write_count"] == 0
    assert audit["raw_dialogue_persisted"] is False
    assert {
        key: value for key, value in state.items() if key != "active_validation"
    } == {
        key: value
        for key, value in expected_state.items()
        if key != "active_validation"
    }
    assert state["active_validation"] == model["active_validation"]
    assert model["layers"] == layers_before
    assert model["typed_calibration"] == calibration_before
    assert update["psychological_inference_written_as_fact"] is False


def test_first_exposure_support_bid_noncompact_and_protected_plans_are_unchanged():
    hypothesis, pragmatic = build_turn("Maybe another time.", 1)
    first = arbitration.apply_repeated_refusal_attunement_p2(
        compact_plan(), pragmatic, hypothesis=hypothesis, pragmatic_verification=NO_VERIFICATION
    )
    assert arbitration.LABEL not in first
    assert first["surface_act"] == "pragmatic_attunement"

    support_h1, support_p1 = build_turn("Don't worry about me.", 1)
    support_h2, support_p2 = build_turn("You don't need to worry about me.", 2)
    support_v = personhood.verify_previous_pragmatic_understanding(
        support_p1, "You don't need to worry about me.", support_p2, turn_index=2
    )
    support = arbitration.apply_repeated_refusal_attunement_p2(
        compact_plan(), support_p2, hypothesis=support_h2, pragmatic_verification=support_v
    )
    assert support_p2["pragmatic_label"] == "possible_indirect_support_request"
    assert arbitration.LABEL not in support

    hypothesis2, pragmatic2 = build_turn("改天再說吧。", 2)
    uncertain = {
        "status": "uncertain",
        "previous_pragmatic_snapshot": deepcopy(pragmatic),
    }
    noncompact = compact_plan()
    noncompact["bounded_slow_path_m21"].pop("compact_general_plan_p2")
    ordinary = arbitration.apply_repeated_refusal_attunement_p2(
        noncompact, pragmatic2, hypothesis=hypothesis2, pragmatic_verification=uncertain
    )
    assert arbitration.LABEL not in ordinary

    protected = compact_plan()
    protected["memory_recall_contract"] = {"source_id": "known-profile"}
    guarded = arbitration.apply_repeated_refusal_attunement_p2(
        protected, pragmatic2, hypothesis=hypothesis2, pragmatic_verification=uncertain
    )
    assert arbitration.LABEL not in guarded


@pytest.mark.parametrize("status", ["supported", "contradicted"])
def test_supported_or_contradicted_outcomes_keep_existing_revision_authority(status):
    hypothesis1, pragmatic1 = build_turn("Maybe another time.", 1)
    hypothesis2, pragmatic2 = build_turn("また今度にしようかな。", 2)
    verification = {
        "status": status,
        "previous_pragmatic_snapshot": deepcopy(pragmatic1),
    }
    logic = arbitration.apply_repeated_refusal_attunement_p2(
        compact_plan(),
        pragmatic2,
        hypothesis=hypothesis2,
        pragmatic_verification=verification,
    )
    assert arbitration.LABEL not in logic
    assert logic["response_mode"] in {
        "felt_understanding_confirmation",
        "felt_understanding_revision",
    }


def test_existing_pending_validation_is_preserved_and_owns_the_action():
    _base, proposed, model, hypothesis, _verification, _update = repeated_pair(
        "Maybe another time.", "また今度にしようかな。"
    )
    old_pending = {
        "validation_id": "older",
        "status": "pending",
        "asked_turn": 1,
        "kind": "emotion_or_need",
        "question_jp": "前の確認。",
    }
    model["active_validation"]["pending"] = deepcopy(old_pending)
    model["active_validation"]["status"] = "pending"

    logic, state, strategy = arbitration.apply_repeated_refusal_arbitration_p2(
        proposed, model, hypothesis, 2
    )

    assert state["active_validation"]["pending"] == old_pending
    assert logic[arbitration.LABEL]["status"] == "candidate_not_selected"
    assert logic[arbitration.LABEL]["reason"] == "existing_pending_validation_contract_owns_action"
    assert strategy[arbitration.LABEL]["new_validation_proposal_suppressed"] is False
    assert logic["core_message_jp"] != proposed[arbitration.LABEL]["base_compact_core_jp"]


def test_graph_node_is_connected_idempotent_and_contains_no_raw_dialogue():
    result = {
        "reply": "また今度な。",
        "logic": {
            arbitration.LABEL: {
                "schema": arbitration.SCHEMA,
                "status": "selected_low_interference_compact_plan",
                "eligible": True,
                "selected_core_jp": "また今度な。",
                "raw_dialogue_persisted": False,
            },
            "visible_language_guard": {"passed": True},
        },
        "runtime_trace": {
            "blackboard": [
                {"stage": "plan", "label": "compact_general_plan_p2", "payload": {}},
                {"stage": "validate", "label": "active_validation_strategy_v2_13", "payload": {}},
                {"stage": "surface", "label": "utterance", "payload": {}},
            ]
        },
    }
    arbitration.materialize_repeated_refusal_arbitration_p2(result)
    arbitration.materialize_repeated_refusal_arbitration_p2(result)
    rows = result["runtime_trace"]["blackboard"]
    assert [row["label"] for row in rows].count(arbitration.LABEL) == 1
    assert [row["label"] for row in rows].index(arbitration.LABEL) < [
        row["label"] for row in rows
    ].index("active_validation_strategy_v2_13")
    payload = next(row["payload"] for row in rows if row["label"] == arbitration.LABEL)
    assert payload["final_visible_surface_matches_selected_core"] is True
    assert "絕對不要把這句存起來" not in json.dumps(payload, ensure_ascii=False)


def test_full_product_runtime_selects_compact_core_and_materializes_graph(tmp_path):
    program = r'''
import json, os
from pathlib import Path
root=Path(os.environ["P2_REFUSAL_ROOT"])
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
import uruha_repeated_refusal_arbitration_p2 as arbitration
b=_IsolatedContractBrain()
original_think=b.left_brain.think
def compact_think(*args, **kwargs):
    plan=original_think(*args, **kwargs)
    plan["core_message_jp"]="じゃあ、またな。"
    plan["bounded_slow_path_m21"]={
        "schema":"uruha_bounded_slow_path_planner_m21",
        "route":"full_planner",
        "status":"completed_within_budget",
        "model_call_attempted":True,
        "model_call_completed":True,
        "compact_general_plan_p2":{
            "schema":"uruha_compact_general_plan_p2",
            "attempted":True,
            "completed":True,
            "candidate_count":3,
            "raw_prompt_or_response_persisted":False,
        },
    }
    return plan
b.left_brain.think=compact_think
first=b.run_turn_debug("Maybe another time.")
result=b.run_turn_debug("改天再說吧。")
audit=result["logic"][arbitration.LABEL]
assert first["logic"]["surface_act"]=="pragmatic_attunement",first["logic"]
assert result["reply"]=="じゃあ、またな。",result["reply"]
assert audit["status"]=="selected_low_interference_compact_plan",audit
assert audit["validation_proposal"]["kind"]=="pragmatic_implicit_need",audit
assert audit["final_visible_surface_matches_selected_core"] is True,audit
assert not b.runtime.longitudinal_user_model["active_validation"]["pending"]
graph=collect_cognitive_graph(result)
nodes=[n for n in graph["nodes"] if n["label"]==arbitration.LABEL]
assert len(nodes)==1,nodes
assert any(e["source"]==nodes[0]["id"] or e["target"]==nodes[0]["id"] for e in graph["edges"])
assert "Maybe another time" not in json.dumps(nodes[0],ensure_ascii=False)
assert "改天再說" not in json.dumps(nodes[0],ensure_ascii=False)
assert b.left_brain.think_calls==2
print(json.dumps({"first":first["reply"],"second":result["reply"],"node":nodes[0]["label"]},ensure_ascii=False))
'''
    env = {**os.environ, "P2_REFUSAL_ROOT": str(tmp_path)}
    completed = subprocess.run(
        [sys.executable, "-c", program],
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert arbitration.LABEL in completed.stdout
