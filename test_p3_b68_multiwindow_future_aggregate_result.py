import p3_b68_multiwindow_future_aggregate_scoring as b68


def test_saved_b68_result_is_four_row_positive_proxy_with_top1_limit():
    result = b68.load_json(
        b68.ROOT / "analysis" / "p3_b68_multiwindow_future_aggregate_result_2026-09-20.json"
    )
    assert b68.validate_result(result) == {"valid": True, "errors": []}
    assert result["status"] == "aggregate_scored"
    assert result["future_outcome_access_count"] == 4
    assert result["outcome_score_count"] == 8
    assert result["aggregate"]["row_wins"] == {
        "BASELINE_LITERAL": 0,
        "SYSTEM_PRAGMATIC_STATE": 4,
        "TIE": 0,
    }
    baseline = result["aggregate"]["BASELINE_LITERAL"]
    system = result["aggregate"]["SYSTEM_PRAGMATIC_STATE"]
    assert system["mean_actual_label_probability"] == 0.2875
    assert baseline["mean_actual_label_probability"] == 0.2625
    assert system["mean_multiclass_brier"] < baseline["mean_multiclass_brier"]
    assert system["top1_hits"] == baseline["top1_hits"] == 1
    assert result["prediction_mutation_count"] == 0
    assert result["model_human_or_llm_judge_call_count"] == 0

