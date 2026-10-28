import p3_b59_source_semantic_availability_probe as b59


def test_saved_b59_result_is_valid_redacted_japanese_auto_caption_availability():
    result = b59.load_json(
        b59.ROOT
        / "analysis"
        / "p3_b59_source_semantic_availability_probe_result_2026-09-20.json"
    )
    assert b59.validate_result(result) == {"valid": True, "errors": []}
    projection = result["availability_projection"]
    assert projection["manual_japanese_available"] is False
    assert projection["automatic_japanese_available"] is True
    assert projection["selected_track_type"] == "automatic"
    assert projection["selected_language_code"] == "ja"
    assert projection["selected_format"] == "json3"
    assert result["caption_content_download_count"] == 0
    assert result["hidden_future_content_access_count"] == 0
    assert result["prediction_execution_count"] == 0
    assert result["model_call_count"] == 0
    assert result["track_url_text_persisted"] is False
