import p3_b61_native_subtitle_cutoff_extractor as b61


def test_saved_b61_result_is_valid_real_pre_cutoff_context_release():
    result = b61.load_json(
        b61.ROOT / "analysis" / "p3_b61_native_subtitle_cutoff_extractor_result_2026-09-20.json"
    )
    assert b61.validate_result(result) == {"valid": True, "errors": []}
    assert result["downloader_returncode"] == 0
    assert result["private_acquisition_full_caption_access_count"] == 1
    assert result["private_caption_deleted_before_fresh_reader"] is True
    assert result["private_runtime_deleted_before_fresh_reader"] is True
    assert result["public_cue_count"] == 65
    assert result["public_first_cue_start_seconds"] >= 3000.0
    assert result["public_last_cue_end_seconds"] <= 3180.0
    assert result["fresh_reader_artifact_sha256"] == result["public_artifact_sha256"]
    assert result["fresh_reader_caption_text_returned"] is False
    assert result["prediction_side_future_access_count"] == 0
    assert result["prediction_execution_count"] == 0
    assert result["model_call_count"] == 0
