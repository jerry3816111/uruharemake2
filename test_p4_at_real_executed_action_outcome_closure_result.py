import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_at_real_executed_action_outcome_closure_evidence_2026-09-26.json"


def _load():
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_p4_at_real_result_preserves_the_formal_surface_action_failure():
    evidence = _load()

    assert evidence["status"] == "fail"
    assert evidence["executed_exactly_once"] is True
    assert evidence["rerun_allowed"] is False
    assert evidence["failed_gates"] == ["turn_2_m39_practical_act_count"]
    assert evidence["metrics"]["turn_2_m39_practical_act_count"] == 0


def test_p4_at_real_result_preserves_the_successful_identity_and_outcome_chain():
    turn_1, turn_2 = _load()["turns"]

    assert turn_1["p4_as_status"] == "executed_and_committed"
    assert turn_1["m44_receipt_status"] == "registered_for_next_user_turn"
    assert turn_1["prediction_id"] == turn_2["prediction_id"]
    assert turn_2["p4_at_status"] == "closed_supported"
    assert turn_2["exact_pending_receipt_identity"] is True
    assert turn_2["m44_outcome_linked"] is True
    assert turn_2["p4_ag_identity_bound"] is True
    assert turn_2["p4_ag_outcome"] == "supported"
    assert turn_2["performed_action_strictly_earlier"] is True
    assert turn_2["prior_future_commitment_consumed"] is True
    assert turn_2["same_turn_outcome_backdated"] is False


def test_p4_at_real_result_keeps_current_request_separate_from_previous_feedback():
    turn_2 = _load()["turns"][1]

    assert turn_2["previous_action_outcome"] == "supported"
    assert turn_2["current_request_policy"] == "solve_regulation"
    assert turn_2["current_request_mode"] == "practical_help"
    assert turn_2["two_independent_acts"] is True
    assert turn_2["m39_policy_act_match_before"] is True
    assert turn_2["m39_policy_act_match_after"] is False
    assert turn_2["m39_unresolved_violations"] == ["practical_action_not_delivered_m45"]


def test_p4_at_real_result_keeps_failure_cause_and_cost_visible():
    turn_2 = _load()["turns"][1]

    assert turn_2["m45_status"] == "withheld_model_unavailable"
    assert turn_2["m45_delivered"] is False
    assert turn_2["m45_reason"] == "TimeoutError"
    assert turn_2["m45_model_calls_attempted"] == 2
    assert turn_2["m45_model_calls_completed"] == 1
    assert turn_2["m45_token_accounting_complete"] is False
    assert turn_2["m46_status"] == "counterfactual_review_unavailable"
    assert turn_2["latency_target_met"] is False


def test_p4_at_real_result_preserves_runtime_and_safari_evidence():
    evidence = _load()
    turn_2 = evidence["turns"][1]
    artifacts = evidence["raw_runtime_artifacts"]

    assert [
        turn_2["p4_at_node_index"],
        turn_2["p4_ag_node_index"],
        turn_2["temporal_node_index"],
        turn_2["utterance_node_index"],
    ] == [66, 67, 68, 69]
    assert turn_2["p4_at_node_before_binding_temporal_and_utterance"] is True
    assert turn_2["p4_at_node_visually_observed_in_safari"] is True
    assert artifacts["conversation_jsonl_rows"] == 2
    assert artifacts["conversation_jsonl_sha256"] == (
        "4d2fcb376b885a322aa173e42817f8045b573d5ad845546e8eaff7ac8de39ed3"
    )
    assert evidence["execution"]["closed_tab_count"] == 0


def test_p4_at_real_failure_does_not_overclaim_understanding():
    evidence = _load()

    assert "not evidence of human-equivalent understanding" in evidence["analysis"]
    assert "Do not rerun or retune this pair" in evidence["next_design_implication"]
