import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_ax_real_compound_feedback_to_action_delivery_evidence_2026-09-26.json"


def _load():
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_p4_ax_real_result_preserves_the_formal_failure_without_rerun():
    evidence = _load()

    assert evidence["status"] == "fail"
    assert evidence["executed_turn_count"] == 2
    assert evidence["executed_exactly_once"] is True
    assert evidence["rerun_allowed"] is False
    assert evidence["metrics"]["turn_2_m45_delivered_count"] == 0
    assert evidence["metrics"]["turn_2_m39_practical_act_count"] == 0
    assert evidence["metrics"]["turn_2_generic_promise_or_clarification_count"] == 1


def test_p4_ax_real_result_records_the_narrow_compound_split_product_pass():
    turn_1, turn_2 = _load()["turns"]

    assert turn_1["p4_as_status"] == "executed_and_committed"
    assert turn_2["p4_ax_status"] == "bounded_support_composed"
    assert turn_2["p4_ax_exact_pending_receipt_identity"] is True
    assert turn_2["p4_ax_predecessor_previous_action_outcome"] == "unknown"
    assert turn_2["p4_ax_previous_action_outcome_after"] == "supported"
    assert turn_2["p4_ax_two_independent_acts_after"] is True
    assert turn_2["p4_ax_predecessor_mutated"] is False
    assert turn_2["p4_ax_p4_au_gate_bypassed"] is False
    assert turn_2["p4_at_prediction_id"] == turn_1["prediction_id"]
    assert turn_2["p4_at_status"] == "closed_supported"
    assert turn_2["p4_ag_outcome"] == "supported"


def test_p4_ax_real_result_preserves_the_new_earliest_p4_au_failure():
    turn_1, turn_2 = _load()["turns"]

    assert turn_2["p4_au_status"] == "blocked_current_task_replacement"
    assert turn_2["p4_au_reason"] == "current_turn_contains_independent_task_source"
    assert turn_2["p4_au_current_nonfeedback_task_ref_count"] == 1
    assert turn_2["p4_au_prior_source_added"] is False
    assert turn_2["p4_au_prior_source_digest"] == turn_1["input_digest"]
    assert turn_2["p4_au_assistant_source_count"] == 0
    assert turn_2["p4_au_private_inference_source_count"] == 0


def test_p4_ax_real_result_does_not_promote_absent_downstream_nodes_to_passes():
    turn = _load()["turns"][1]
    metrics = _load()["metrics"]

    assert turn["p4_av_status"] == "not_reached"
    assert turn["p4_av_integrity_pass"] is False
    assert turn["m53_status"] == "not_reached"
    assert turn["m53_no_unsupported_verified"] is False
    assert turn["p4_av_node_index"] is None
    assert turn["m53_node_index"] is None
    assert metrics["turn_2_p4_av_integrity_pass_count"] == 0
    assert metrics["turn_2_m53_no_unsupported_count"] == 0
    assert metrics["p4_au_node_before_m50_m53_m46_m45_utterance_count"] == 0
    assert metrics["p4_av_node_before_m53_m46_m45_utterance_count"] == 0


def test_p4_ax_real_result_keeps_the_model_json_failure_independent():
    turn = _load()["turns"][1]

    assert turn["m51_status"] == "not_invoked"
    assert turn["m51_candidate_count"] == 0
    assert turn["m46_status"] == "plan_unavailable"
    assert turn["m45_status"] == "withheld_model_unavailable"
    assert turn["m45_reason"] == "JSONDecodeError"
    assert turn["m45_model_calls_attempted"] == 1
    assert turn["m45_model_calls_completed"] == 1
    assert turn["m45_prompt_tokens"] == 1001
    assert turn["m45_completion_tokens"] == 360
    assert turn["m45_prior_user_source_count"] == 0
    assert turn["m39_policy_act_match_after"] is False


def test_p4_ax_real_result_records_graph_durability_and_cost():
    evidence = _load()
    turn = evidence["turns"][1]
    metrics = evidence["metrics"]

    assert metrics["natural_japanese_visible_count"] == 2
    assert metrics["durable_episode_count"] == 2
    assert metrics["isolated_chroma_embedding_count"] == 2
    assert metrics["graph_visible_count"] == 2
    assert turn["p4_ax_node_index"] < turn["p4_at_node_index"]
    assert turn["p4_ax_node_index"] < turn["p4_ag_node_index"]
    assert turn["p4_ax_node_index"] < turn["temporal_node_index"]
    assert turn["p4_ax_node_index"] < turn["utterance_node_index"]
    assert metrics["total_model_calls_attempted"] == 1
    assert metrics["total_model_calls_completed"] == 1
    assert metrics["total_prompt_tokens"] == 1001
    assert metrics["total_completion_tokens"] == 360
    assert metrics["token_accounting_complete"] is False
    assert metrics["maximum_end_to_end_seconds"] == 31.0372
    assert metrics["latency_target_met_count"] == 1
    assert evidence["raw_runtime_artifacts"]["conversation_jsonl_rows"] == 2
    assert evidence["raw_runtime_artifacts"]["conversation_jsonl_sha256"] == "49266d5dbca5d6a58d82612288dfb305f908b0b5db031187dc4b7cd8443fa083"


def test_p4_ax_real_failure_does_not_overclaim_understanding():
    evidence = _load()

    assert "not evidence of felt understanding" in evidence["analysis"]
    assert "Do not rerun or retune this pair" in evidence["next_design_implication"]
