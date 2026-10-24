import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_au_real_source_bound_current_action_delivery_evidence_2026-09-26.json"


def _load():
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_p4_au_real_result_preserves_the_formal_delivery_failure():
    evidence = _load()

    assert evidence["status"] == "fail"
    assert evidence["executed_exactly_once"] is True
    assert evidence["rerun_allowed"] is False
    assert evidence["metrics"]["turn_2_m45_delivered_count"] == 0
    assert evidence["metrics"]["turn_2_m46_verified_count"] == 0
    assert evidence["metrics"]["turn_2_m39_practical_act_count"] == 0
    assert evidence["metrics"]["turn_2_generic_promise_or_clarification_count"] == 1


def test_p4_au_real_result_preserves_exact_prior_user_source_handoff():
    turn_1, turn_2 = _load()["turns"]

    assert turn_1["prediction_id"] == turn_2["prediction_id"]
    assert turn_2["p4_at_status"] == "closed_supported"
    assert turn_2["p4_au_status"] == "prior_source_linked"
    assert turn_2["p4_au_prior_source_matches_turn_1"] is True
    assert turn_2["p4_au_prior_source_digest"] == turn_1["input_digest"]
    assert turn_2["p4_au_assistant_source_count"] == 0
    assert turn_2["p4_au_private_inference_source_count"] == 0
    assert turn_2["p4_au_raw_dialogue_persisted"] is False


def test_p4_au_real_result_keeps_failure_at_the_existing_m53_boundary():
    turn_2 = _load()["turns"][1]

    assert turn_2["m45_status"] == "withheld_goal_plan_failed"
    assert turn_2["m45_violations"] == ["unsupported_concrete_scaffold_label_m53"]
    assert turn_2["m51_candidate_count"] == 2
    assert turn_2["m51_structurally_valid_count"] == 0
    assert turn_2["m53_status"] == "blocked"
    assert turn_2["m53_named_label_count"] == 2
    assert turn_2["m53_unsupported_count"] == 2
    assert turn_2["m46_status"] == "plan_rejected"
    assert turn_2["m39_unresolved_violations"] == ["practical_action_not_delivered_m45"]


def test_p4_au_real_result_preserves_graph_order_and_safari_observation():
    evidence = _load()
    turn_2 = evidence["turns"][1]

    assert [
        turn_2["p4_au_node_index"],
        turn_2["m50_node_index"],
        turn_2["m53_node_index"],
        turn_2["m46_node_index"],
        turn_2["m45_node_index"],
        turn_2["utterance_node_index"],
    ] == [50, 51, 55, 56, 57, 69]
    assert turn_2["p4_au_node_before_m50_m45_and_utterance"] is True
    assert turn_2["p4_au_node_visually_observed_in_safari"] is True
    assert evidence["execution"]["closed_tab_count"] == 0
    assert evidence["raw_runtime_artifacts"]["conversation_jsonl_rows"] == 2


def test_p4_au_real_result_records_cost_without_excusing_failure():
    evidence = _load()
    metrics = evidence["metrics"]

    assert metrics["total_model_calls_attempted"] == 1
    assert metrics["total_model_calls_completed"] == 1
    assert metrics["total_prompt_tokens"] == 711
    assert metrics["total_completion_tokens"] == 288
    assert metrics["maximum_end_to_end_seconds"] == 20.7275
    assert evidence["turns"][1]["latency_target_met"] is False


def test_p4_au_real_failure_does_not_overclaim_understanding():
    evidence = _load()

    assert "not evidence of felt understanding" in evidence["analysis"]
    assert "Do not rerun or retune this pair" in evidence["next_design_implication"]
