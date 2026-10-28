import json
from pathlib import Path

import p3_b76_official_channel_inventory_selection as b76


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p3_b76_official_channel_inventory_result_2026-09-20.json"


def test_saved_result_is_valid_terminal_inventory_failure():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert b76.validate_result(result) == {"valid": True, "errors": []}
    assert result["status"] == "insufficient_eligible_sources"
    assert result["eligible_source_count_found"] == 0
    assert result["selected_sources"] == []
    assert result["provider_inventory_process_invocation_count"] == 1
    assert result["retry_count"] == 0
    assert result["fallback_count"] == 0
    assert result["result_hash"] == "40b28a7677b29c3be63cffcfc79802beb3ed713990da1eb744a3cdbaa275f82c"


def test_saved_result_has_zero_content_model_and_outcome_access():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["caption_metadata_access_count"] == 0
    assert result["caption_content_access_count"] == 0
    assert result["media_playback_count"] == 0
    assert result["model_call_count"] == 0
    assert result["outcome_access_count"] == 0
    assert result["raw_inventory_stdout_or_stderr_persisted"] is False
