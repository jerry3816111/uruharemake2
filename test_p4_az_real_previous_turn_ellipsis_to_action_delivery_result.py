import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_az_real_previous_turn_ellipsis_to_action_delivery_evidence_2026-09-26.json"


def _load():
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_p4_az_real_result_preserves_the_formal_failure_without_rerun():
    evidence = _load()

    assert evidence["status"] == "fail"
    assert evidence["executed_turn_count"] == 2
    assert evidence["executed_exactly_once"] is True
    assert evidence["rerun_allowed"] is False
    assert evidence["metrics"]["turn_2_m45_delivered_count"] == 0
    assert evidence["metrics"]["turn_2_m39_practical_act_count"] == 0
    assert evidence["metrics"]["turn_2_generic_promise_or_clarification_count"] == 1


def test_p4_az_real_result_records_the_narrow_source_authority_product_pass():
    turn_1, turn_2 = _load()["turns"]

    assert turn_1["p4_as_status"] == "executed_and_committed"
    assert turn_2["p4_ax_status"] == "bounded_support_composed"
    assert turn_2["p4_at_status"] == "closed_supported"
    assert turn_2["p4_at_prediction_id"] == turn_1["prediction_id"]
    assert turn_2["p4_ay_authorized_constraint_ref_count"] == 1
    assert turn_2["p4_ay_genuine_task_ref_count"] == 0
    assert turn_2["p4_ay_remaining_guard_status"] == "blocked_prior_source_role"
    assert turn_2["p4_az_status"] == "authorized_previous_turn_cjk_ellipsis"
    assert turn_2["p4_az_source_role_preserved"] == "unspecified"
    assert turn_2["p4_az_source_role_rewritten"] is False
    assert turn_2["p4_az_failed_exact_chain_checks"] == []
    assert turn_2["p4_az_failed_source_checks"] == []


def test_p4_az_real_result_records_exact_prior_source_handoff_without_private_source():
    turn_1, turn_2 = _load()["turns"]

    assert turn_2["p4_au_status"] == "prior_source_linked"
    assert turn_2["p4_au_prior_source_added"] is True
    assert turn_2["p4_au_prior_source_id"] == "prior:1"
    assert turn_2["p4_au_prior_source_digest"] == turn_1["input_digest"]
    assert turn_2["p4_au_prior_source_digest_matches_turn_1"] is True
    assert turn_2["p4_au_assistant_source_count"] == 0
    assert turn_2["p4_au_private_inference_source_count"] == 0


def test_p4_az_real_result_preserves_downstream_integrity_gates():
    turn = _load()["turns"][1]

    assert turn["p4_av_integrity_pass"] is True
    assert turn["p4_av_remaining_unsupported_count"] == 0
    assert turn["p4_av_m46_review_bypassed"] is False
    assert turn["p4_av_m45_or_m39_gate_weakened"] is False
    assert turn["m53_status"] == "no_named_labels"
    assert turn["m53_unsupported_count"] == 0


def test_p4_az_real_result_preserves_the_new_earliest_model_review_failure():
    turn = _load()["turns"][1]

    assert turn["m51_status"] == "valid_candidate_selected"
    assert turn["m51_candidate_count"] == 2
    assert turn["m51_structurally_valid_count"] == 1
    assert turn["m51_selected_structurally_valid"] is True
    assert turn["m46_status"] == "counterfactual_review_unavailable"
    assert turn["m46_verified"] is False
    assert turn["m45_status"] == "withheld_model_unavailable"
    assert turn["m45_reason"] == "TimeoutError"
    assert turn["m45_model_calls_attempted"] == 2
    assert turn["m45_model_calls_completed"] == 1
    assert turn["m45_delivered"] is False
    assert turn["m39_status"] == "repair_failed_closed"
    assert turn["m39_policy_act_match_after"] is False


def test_p4_az_real_result_records_graph_durability_and_cost():
    evidence = _load()
    turn = evidence["turns"][1]
    metrics = evidence["metrics"]

    assert metrics["natural_japanese_visible_count"] == 2
    assert metrics["durable_episode_count"] == 2
    assert metrics["isolated_chroma_embedding_count"] == 2
    assert metrics["graph_visible_count"] == 2
    assert turn["p4_ay_node_index"] < turn["p4_az_node_index"] < turn["p4_au_node_index"]
    assert turn["p4_az_node_index"] < turn["m50_node_index"] < turn["m53_node_index"]
    assert turn["m53_node_index"] < turn["m46_node_index"] < turn["m45_node_index"]
    assert turn["m45_node_index"] < turn["utterance_node_index"]
    assert metrics["total_model_calls_attempted"] == 2
    assert metrics["total_model_calls_completed"] == 1
    assert metrics["total_prompt_tokens"] == 876
    assert metrics["total_completion_tokens"] == 300
    assert metrics["token_accounting_complete"] is False
    assert metrics["maximum_end_to_end_seconds"] == 38.1682
    assert metrics["latency_target_met_count"] == 1
    assert evidence["raw_runtime_artifacts"]["conversation_jsonl_rows"] == 2
    assert evidence["raw_runtime_artifacts"]["conversation_jsonl_sha256"] == "6fdb5ed82b4cb6dbd4babfd366582b9106ebbb61b82e7c3e7dffb689a07dd4fe"


def test_p4_az_real_failure_does_not_overclaim_understanding():
    evidence = _load()

    assert "not evidence of advice usefulness" in evidence["analysis"]
    assert "Do not rerun or retune this pair" in evidence["next_design_implication"]
