import p3_b67_same_source_multiwindow_predictions as b67


def test_saved_b67_result_freezes_all_eight_predictions_before_any_future():
    result = b67.load_json(
        b67.ROOT / "analysis" / "p3_b67_same_source_multiwindow_prediction_result_2026-09-20.json"
    )
    assert b67.validate_result(result) == {"valid": True, "errors": []}
    assert result["status"] == "prediction_batch_frozen"
    assert result["model_call_count"] == 8
    assert result["prediction_count"] == 8
    assert result["actual_prompt_tokens_total"] == 18908
    assert result["actual_completion_tokens_total"] == 1697
    assert result["prediction_side_future_access_count"] == 0
    assert result["outcome_score_count"] == 0
    assert result["retry_count"] == 0
    assert result["fallback_count"] == 0
    assert [row["row_id"] for row in result["predictions"]] == [
        "r0600", "r0600", "r1200", "r1200", "r1800", "r1800", "r2400", "r2400"
    ]
    assert all(row["state_persisted"] is False for row in result["predictions"])

