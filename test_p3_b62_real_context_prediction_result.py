import p3_b62_real_context_prediction_freeze as b62


def test_saved_b62_result_is_valid_terminal_schema_failure_with_future_locked():
    result = b62.load_json(
        b62.ROOT / "analysis" / "p3_b62_real_context_prediction_result_2026-09-20.json"
    )
    assert b62.validate_result(result) == {"valid": True, "errors": []}
    assert result["status"] == "prediction_failed"
    assert result["failure_stage"] == "representation"
    assert result["failure_category"] == "schema"
    assert result["future_outcome_access_count"] == 0
    assert result["outcome_score_count"] == 0
    assert result["retry_count"] == 0


def test_saved_b62_zero_call_count_is_not_accepted_as_operational_truth():
    result = b62.load_json(
        b62.ROOT / "analysis" / "p3_b62_real_context_prediction_result_2026-09-20.json"
    )
    assert result["model_call_count"] == 0
    # The representation-schema failure is reachable only after _call returned model text.
    assert result["failure_stage"] == "representation"
    operational_audit = {
        "actual_model_call_count": 1,
        "basis": "control_flow_call_returned_before_representation_validation",
        "token_and_latency_accounting": "unavailable_due_b62_post_condition_recording_defect",
    }
    assert operational_audit["actual_model_call_count"] == 1
