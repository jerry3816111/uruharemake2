import json
from pathlib import Path

import p3_b75_real_episode_sampling_frame as b75


ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "research" / "p3_b75_real_episode_sampling_frame_release_2026-09-20.json"


def test_release_preserves_ranked_search_failure_without_content_access():
    release = json.loads(RELEASE.read_text(encoding="utf-8"))
    assert release["status"] == "released_insufficient_ranked_search_sources_no_content_review"
    assert release["result"]["eligible_source_count_found"] == 0
    assert release["result"]["selected_source_count"] == 0
    assert release["result"]["sampling_slot_count"] == 0
    assert release["result"]["caption_or_media_content_access_count"] == 0
    assert release["result"]["retry_count"] == 0


def test_release_bindings_match_and_only_one_inventory_repair_is_allowed():
    release = json.loads(RELEASE.read_text(encoding="utf-8"))
    for binding in release["bindings"].values():
        path = ROOT / binding["path"]
        assert path.is_file()
        assert b75.sha256_file(path) == binding["sha256"]
    assert release["next_stage"]["id"] == "P3-B76"
    assert release["next_stage"]["repair_index"] == 1
    assert release["next_stage"]["repair_limit"] == 1
    assert release["next_stage"]["content_or_playback_allowed"] is False
    assert release["next_stage"]["alternate_keyword_or_manual_selection_after_failure_allowed"] is False
