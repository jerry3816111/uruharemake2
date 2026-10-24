import p3_b65_bounded_joint_prediction_interface as b65


def test_saved_b65_result_freezes_equal_budget_pair_before_future_access():
    result = b65.load_json(
        b65.ROOT / "analysis" / "p3_b65_bounded_joint_prediction_result_2026-09-20.json"
    )
    assert b65.validate_result(result) == {"valid": True, "errors": []}
    assert result["status"] == "prediction_pair_frozen"
    assert result["model_call_count"] == 2
    assert result["completion_token_ceiling_by_condition"] == {
        "BASELINE_LITERAL": 512,
        "SYSTEM_PRAGMATIC_STATE": 512,
    }
    assert result["actual_completion_tokens_by_condition"] == {
        "BASELINE_LITERAL": 261,
        "SYSTEM_PRAGMATIC_STATE": 233,
    }
    assert result["future_outcome_access_count"] == 0
    assert result["outcome_score_count"] == 0
    assert result["retry_count"] == 0
    assert result["fallback_count"] == 0
    assert [row["selected_behavior"] for row in result["predictions"]] == [
        "accept_support_and_continue",
        "acknowledge_then_continue",
    ]
    assert all(row["state_persisted"] is False for row in result["predictions"])

