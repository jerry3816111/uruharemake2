import p3_b63_schema_enforced_real_context_predictions as b63


def test_saved_b63_result_counts_completed_truncated_call_and_keeps_future_locked():
    result = b63.load_json(
        b63.ROOT / "analysis" / "p3_b63_schema_enforced_prediction_result_2026-09-20.json"
    )
    assert b63.validate_result(result) == {"valid": True, "errors": []}
    assert result["status"] == "prediction_failed"
    assert result["model_call_count"] == 1
    assert len(result["call_records"]) == 1
    call = result["call_records"][0]
    assert call["status"] == "completed"
    assert call["prompt_tokens"] == 1986
    assert call["completion_tokens"] == 256
    assert call["num_predict"] == 256
    assert result["future_outcome_access_count"] == 0
    assert result["outcome_score_count"] == 0
