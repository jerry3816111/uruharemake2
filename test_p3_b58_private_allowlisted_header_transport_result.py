import p3_b58_private_allowlisted_header_transport as b58


def test_saved_b58_result_is_valid_redacted_header_transport_failure():
    result = b58.load_json(
        b58.ROOT
        / "analysis"
        / "p3_b58_private_allowlisted_header_transport_result_2026-09-20.json"
    )
    assert b58.validate_result(result) == {"valid": True, "errors": []}
    assert result["resolver_returncode"] == 0
    assert result["resolver_url_count"] == 1
    assert result["private_allowlisted_header_count"] == 3
    assert result["direct_ffmpeg_returncode"] == 8
    assert result["failure_stage"] == "direct_ffmpeg"
    assert result["failure_category"] == "tls_or_network"
    assert result["header_names_persisted"] is False
    assert result["header_values_persisted"] is False
    assert result["header_hashes_persisted"] is False
    assert result["public_artifact_count"] == 0
    assert result["hidden_future_media_request_count"] == 0
    assert result["prediction_execution_count"] == 0
    assert result["model_call_count"] == 0
    assert result["paid_api_or_account_access_count"] == 0
