import p3_b69a_source2_caption_availability as b69a


def test_saved_b69a_result_releases_automatic_ja_without_content_access():
    result = b69a.load_json(
        b69a.ROOT / "analysis" / "p3_b69a_source2_caption_availability_result_2026-09-20.json"
    )
    assert b69a.validate_result(result) == {"valid": True, "errors": []}
    assert result["status"] == "available"
    assert result["manual_japanese_available"] is False
    assert result["automatic_japanese_available"] is True
    assert result["selected_track_type"] == "automatic"
    assert result["selected_language_code"] == "ja"
    assert result["selected_format"] == "json3"
    assert result["caption_content_download_count"] == 0
    assert result["future_content_access_count"] == 0
    assert result["model_call_count"] == 0

