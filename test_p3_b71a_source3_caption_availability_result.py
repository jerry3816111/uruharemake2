import json
from pathlib import Path

import p3_b71a_source3_caption_availability as b71a


ROOT = Path(__file__).resolve().parent
RESULT_PATH = ROOT / "analysis" / "p3_b71a_source3_caption_availability_result_2026-09-20.json"


def test_saved_b71a_result_is_available_metadata_only():
    result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    assert b71a.validate_result(result) == {"valid": True, "errors": []}
    assert result["status"] == "available"
    assert result["source_id"] == "youtube_j6Hlk9cY9LQ"
    assert result["manual_japanese_available"] is False
    assert result["automatic_japanese_available"] is True
    assert [result["selected_track_type"], result["selected_language_code"], result["selected_format"]] == ["automatic", "ja", "json3"]


def test_saved_b71a_result_has_zero_content_model_future_retry_or_fallback():
    result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    assert result["resolver_process_invocation_count"] == 1
    for field in ("caption_content_download_count", "model_call_count", "future_content_access_count", "retry_count", "fallback_count"):
        assert result[field] == 0
    assert result["raw_stdout_stderr_or_track_url_persisted"] is False
    assert result["result_hash"] == "4e23708011c4e6e7225b1035a5508091e2abc5ed5e77c242a211e5689ebc63c3"
