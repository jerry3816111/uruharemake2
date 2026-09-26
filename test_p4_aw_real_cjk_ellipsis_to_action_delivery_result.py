import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_aw_real_cjk_ellipsis_to_action_delivery_evidence_2026-09-26.json"


def _load():
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_p4_aw_real_result_preserves_the_formal_failure_without_rerun():
    evidence = _load()

    assert evidence["status"] == "fail"
    assert evidence["executed_turn_count"] == 2
    assert evidence["executed_exactly_once"] is True
    assert evidence["rerun_allowed"] is False
    assert evidence["metrics"]["turn_2_m45_delivered_count"] == 0
    assert evidence["metrics"]["turn_2_m39_practical_act_count"] == 0
    assert evidence["metrics"]["turn_2_generic_promise_or_clarification_count"] == 1


def test_p4_aw_real_result_records_the_narrow_turn_one_product_pass():
    turn = _load()["turns"][0]

    assert turn["p4_aw_status"] == "authorized_current_user_ellipsis"
    assert turn["p4_aw_source_role_preserved"] == "unspecified"
    assert turn["p4_aw_final_exact_chain_verified"] is True
    assert turn["p4_as_status"] == "executed_and_committed"
    assert turn["m44_receipt_status"] == "registered_for_next_user_turn"
    assert turn["p4_ar_status"] == "authorized_executed_product_event"
    assert turn["p4_ag_binding_status"] == "pending"
    assert turn["temporal_future_status"] == "committed_outcome_locked"
    assert turn["p4_aw_private_truth_claimed"] is False


def test_p4_aw_real_result_keeps_compound_feedback_failure_separate():
    turn_1, turn_2 = _load()["turns"]

    assert turn_2["p4_at_prediction_id"] == turn_1["prediction_id"]
    assert turn_2["p4_at_exact_pending_receipt_identity"] is True
    assert turn_2["p4_at_status"] == "closed_unknown"
    assert turn_2["p4_at_two_independent_acts"] is False
    assert turn_2["p4_at_current_request_policy"] == "solve_regulation"
    assert turn_2["p4_au_status"] == "blocked_no_decisive_action_feedback"
    assert turn_2["p4_au_prior_source_added"] is False
    assert turn_2["p4_au_prior_source_digest_matches_turn_1"] is True


def test_p4_aw_real_result_preserves_independent_model_timeout_failure():
    turn = _load()["turns"][1]

    assert turn["m51_candidate_count"] == 2
    assert turn["m51_structurally_valid_count"] == 2
    assert turn["m52_realized_count"] == 2
    assert turn["m46_status"] == "counterfactual_review_unavailable"
    assert turn["m45_status"] == "withheld_model_unavailable"
    assert turn["m45_reason"] == "TimeoutError"
    assert turn["m45_model_calls_attempted"] == 2
    assert turn["m45_model_calls_completed"] == 1
    assert turn["m39_unresolved_violations"] == ["practical_action_not_delivered_m45"]


def test_p4_aw_real_result_preserves_graph_and_safari_observation():
    evidence = _load()
    turn_1, turn_2 = evidence["turns"]

    assert [turn_1["p4_aw_node_index"], turn_1["p4_as_node_index"], turn_1["p4_ar_node_index"], turn_1["temporal_node_index"], turn_1["utterance_node_index"]] == [65, 66, 67, 68, 70]
    assert turn_1["p4_ag_node_index"] is None
    assert [turn_2["p4_au_node_index"], turn_2["p4_av_node_index"], turn_2["m53_node_index"], turn_2["m46_node_index"], turn_2["m45_node_index"], turn_2["utterance_node_index"]] == [49, 54, 55, 56, 57, 69]
    assert turn_2["p4_at_node_visually_observed_in_safari"] is True
    assert turn_2["p4_au_node_visually_observed_in_safari"] is True
    assert turn_2["p4_av_node_visually_observed_in_safari"] is True
    assert turn_2["m45_failure_visually_observed_in_safari"] is True
    assert evidence["execution"]["closed_tab_count"] == 0


def test_p4_aw_real_result_records_cost_and_raw_artifact_identity():
    evidence = _load()
    metrics = evidence["metrics"]

    assert metrics["total_model_calls_attempted"] == 2
    assert metrics["total_model_calls_completed"] == 1
    assert metrics["total_prompt_tokens"] == 546
    assert metrics["total_completion_tokens"] == 272
    assert metrics["token_accounting_complete"] is False
    assert metrics["maximum_end_to_end_seconds"] == 38.1546
    assert metrics["latency_target_met_count"] == 1
    assert evidence["raw_runtime_artifacts"]["conversation_jsonl_rows"] == 2
    assert evidence["raw_runtime_artifacts"]["conversation_jsonl_sha256"] == "25ba455d5916097f9c0d44f5e1311a676a4a1b5e8f673bd068ed13b16dbd3fad"


def test_p4_aw_real_failure_does_not_overclaim_understanding():
    evidence = _load()

    assert "not evidence of felt understanding" in evidence["analysis"]
    assert "Do not rerun or retune this pair" in evidence["next_design_implication"]
