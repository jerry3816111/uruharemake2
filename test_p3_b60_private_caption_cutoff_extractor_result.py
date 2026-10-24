import p3_b60_private_caption_cutoff_extractor as b60


def test_saved_b60_result_is_valid_redacted_caption_get_failure():
    result = b60.load_json(
        b60.ROOT / "analysis" / "p3_b60_private_caption_cutoff_extractor_result_2026-09-20.json"
    )
    assert b60.validate_result(result) == {"valid": True, "errors": []}
    assert result["resolver_returncode"] == 0
    assert result["caption_get_invocation_count"] == 1
    assert result["failure_stage"] == "caption_get"
    assert result["failure_category"] == "tls_or_network"
    assert result["private_acquisition_full_caption_access_count"] == 0
    assert result["prediction_side_future_access_count"] == 0
    assert result["raw_caption_persisted"] is False
    assert result["public_artifact_count"] == 0
    assert result["prediction_execution_count"] == 0
    assert result["model_call_count"] == 0
