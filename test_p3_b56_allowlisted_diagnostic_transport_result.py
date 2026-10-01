import p3_b56_allowlisted_diagnostic_transport as b56


def test_saved_b56_result_is_valid_redacted_failure():
    result = b56.load_json(
        b56.ROOT
        / "analysis"
        / "p3_b56_allowlisted_diagnostic_transport_result_2026-09-19.json"
    )
    assert b56.validate_result(result) == {"valid": True, "errors": []}
    assert result["status"] == "diagnostic_transport_failed"
    assert result["diagnostic_category"] == "ffmpeg_or_postprocessing"
    assert result["network_attempt_count"] == 1
    assert result["public_artifact_count"] == 0
    assert result["hidden_future_media_request_count"] == 0
    assert result["prediction_execution_count"] == 0
    assert result["model_call_count"] == 0
    assert result["stderr_text_persisted"] is False
    assert result["stderr_hash_persisted"] is False
    assert result["stderr_excerpt_or_token_persisted"] is False
