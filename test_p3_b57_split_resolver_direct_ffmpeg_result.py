import p3_b57_split_resolver_direct_ffmpeg as b57


def test_saved_b57_result_is_valid_redacted_split_transport_failure():
    result = b57.load_json(
        b57.ROOT
        / "analysis"
        / "p3_b57_split_resolver_direct_ffmpeg_result_2026-09-19.json"
    )
    assert b57.validate_result(result) == {"valid": True, "errors": []}
    assert result["resolver_returncode"] == 0
    assert result["resolver_url_count"] == 1
    assert result["resolver_url_host_category"] == "googlevideo_cdn"
    assert result["direct_ffmpeg_returncode"] == 8
    assert result["failure_stage"] == "direct_ffmpeg"
    assert result["failure_category"] == "tls_or_network"
    assert result["signed_url_text_persisted"] is False
    assert result["signed_url_hash_persisted"] is False
    assert result["signed_url_excerpt_or_query_key_persisted"] is False
    assert result["public_artifact_count"] == 0
    assert result["hidden_future_media_request_count"] == 0
    assert result["prediction_execution_count"] == 0
    assert result["model_call_count"] == 0
