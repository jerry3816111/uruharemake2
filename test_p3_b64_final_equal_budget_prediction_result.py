import p3_b64_final_equal_budget_prediction_execution as b64


def test_saved_b64_result_is_terminal_equal_budget_failure_with_future_locked():
    result = b64.load_json(
        b64.ROOT / "analysis" / "p3_b64_final_equal_budget_prediction_result_2026-09-20.json"
    )
    assert b64.validate_result(result) == {"valid": True, "errors": []}
    assert result["status"] == "prediction_failed"
    assert result["model_call_count"] == 1
    assert len(result["call_records"]) == 1
    call = result["call_records"][0]
    assert call["status"] == "completed"
    assert call["prompt_tokens"] == 1986
    assert call["completion_tokens"] == 320
    assert call["num_predict"] == 320
    assert result["retry_count"] == 0
    assert result["fallback_count"] == 0
    assert result["future_outcome_access_count"] == 0
    assert result["outcome_score_count"] == 0

