import json
from pathlib import Path

import p3_b75_real_episode_sampling_frame as b75


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p3_b75_real_episode_sampling_frame_result_2026-09-20.json"


def test_saved_result_is_valid_terminal_insufficient_source_result():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert b75.validate_result(result) == {"valid": True, "errors": []}
    assert result["status"] == "insufficient_eligible_sources"
    assert result["eligible_source_count_found"] == 0
    assert result["selected_sources"] == []
    assert result["provider_search_process_invocation_count"] == 1
    assert result["retry_count"] == 0
    assert result["fallback_count"] == 0
    assert result["result_hash"] == "e730066e132f08f8027a0c43223220afe59708cbcb2a37cc4c9ab405ac54d03e"


def test_saved_result_did_not_touch_content_model_or_outcome():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["caption_metadata_access_count"] == 0
    assert result["caption_content_access_count"] == 0
    assert result["media_playback_count"] == 0
    assert result["model_call_count"] == 0
    assert result["outcome_access_count"] == 0
    assert result["raw_search_stdout_or_stderr_persisted"] is False
    assert result["controlled_context_flip_lane_separate"] is True
