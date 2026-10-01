import json
from pathlib import Path

import p3_b71_source3_selection as b71


ROOT = Path(__file__).resolve().parent
RESULT_PATH = ROOT / "analysis" / "p3_b71_source3_selection_result_2026-09-20.json"


def test_saved_b71_result_selects_third_source_by_frozen_rule():
    result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    assert b71.validate_result(result) == {"valid": True, "errors": []}
    assert result["status"] == "selected"
    assert result["selected_source"] == {
        "source_id": "youtube_j6Hlk9cY9LQ",
        "video_id": "j6Hlk9cY9LQ",
        "channel_id": "UC5LyYg6cCA4yHEYvtUsir3g",
        "duration_seconds": 12883.0,
        "title": "【APEX】弾を打ってみます【ぶいすぽ/一ノ瀬うるは】",
        "selection_rank": 2,
    }
    assert result["frozen_rows"] == b71.expected_rows()


def test_saved_b71_result_has_zero_caption_model_future_retry_or_fallback():
    result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    for field in (
        "caption_metadata_access_count",
        "caption_content_access_count",
        "model_call_count",
        "future_access_count",
        "retry_count",
        "fallback_count",
    ):
        assert result[field] == 0
    assert result["provider_search_process_invocation_count"] == 1
    assert result["raw_search_stdout_or_stderr_persisted"] is False
    assert result["result_hash"] == "8b6e043bb09c236bdef8867c973a242c94fc69dda5ddc172198f1012318db92d"
