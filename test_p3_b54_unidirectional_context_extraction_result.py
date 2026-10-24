import p3_b54_unidirectional_context_extraction as b54


def test_saved_b54_synthetic_result_matches_frozen_validator():
    path = (
        b54.ROOT
        / "analysis"
        / "p3_b54_unidirectional_context_extraction_result_2026-09-18.json"
    )
    result = b54.load_json(path)
    assert b54.validate_synthetic_rehearsal(result) == {"valid": True, "errors": []}
    assert result["reserved_source_media_access_count"] == 0
    assert result["hidden_future_access_count"] == 0
    assert result["prediction_execution_count"] == 0
    assert result["model_call_count"] == 0
