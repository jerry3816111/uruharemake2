import p3_b66_future_outcome_unlock_scoring as b66


def test_saved_b66_result_is_bound_positive_proxy_with_zero_judge_calls():
    result = b66.load_json(
        b66.ROOT / "analysis" / "p3_b66_future_outcome_scored_result_2026-09-20.json"
    )
    assert b66.validate_result(result) == {"valid": True, "errors": []}
    assert result["status"] == "outcome_scored"
    assert result["actual_proxy_label"] == "ask_clarification"
    assert result["matched_proxy_marker"] == "?"
    assert result["proxy_winner"] == "SYSTEM_PRAGMATIC_STATE"
    assert result["scores"][0]["actual_label_probability"] == 0.05
    assert result["scores"][1]["actual_label_probability"] == 0.1
    assert result["scores"][1]["multiclass_brier"] < result["scores"][0]["multiclass_brier"]
    assert result["scores"][1]["log_loss"] < result["scores"][0]["log_loss"]
    assert result["scores"][0]["selected_label_hit"] is False
    assert result["scores"][1]["selected_label_hit"] is False
    assert result["model_or_judge_call_count"] == 0
    assert result["prediction_mutation_count"] == 0
    assert result["retry_count"] == 0

