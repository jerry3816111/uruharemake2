from copy import deepcopy

import p3_b75_real_episode_sampling_frame as b75
import p3_b76_official_channel_inventory_selection as b76


def _entry(video_id, title, duration=3600, channel_id=None):
    value = {"id": video_id, "title": title, "duration": duration}
    if channel_id is not None:
        value["channel_id"] = channel_id
    return value


def test_contract_is_single_official_inventory_repair_with_no_content():
    assert b76.validate_contract() == {"valid": True, "errors": []}
    contract = b76.load_contract()
    assert contract["inventory"]["provider_entry_limit"] == 200
    assert contract["inventory"]["retry_alternate_tab_query_keyword_or_manual_selection_allowed"] is False
    assert contract["slot_algorithm"]["reuse_b75_build_slots_without_change"] is True
    assert all(contract["denied_actions"].values())


def test_inventory_command_targets_channel_videos_and_has_no_retry():
    command = b76.build_inventory_command("/usr/bin/yt-dlp")
    assert command[-1] == "https://www.youtube.com/channel/UC5LyYg6cCA4yHEYvtUsir3g/videos"
    assert command[command.index("--playlist-end") + 1] == "200"
    assert command[command.index("--retries") + 1] == "0"
    assert "--skip-download" in command


def test_selection_accepts_parent_channel_identity_and_preserves_provider_order():
    document = {
        "channel_id": "UC5LyYg6cCA4yHEYvtUsir3g",
        "entries": [
            _entry("4y5GiQpgJgo", "雑談"),
            _entry("no-keyword", "APEX"),
            _entry("a", "コラボ雑談"),
            _entry("b", "飲酒配信"),
            _entry("c", "質問に答える"),
            _entry("d", "対談"),
        ],
    }
    selected = b76.select_sources(document)
    assert [source["video_id"] for source in selected] == ["a", "b", "c"]
    assert [source["selection_rank"] for source in selected] == [3, 4, 5]


def test_success_result_reuses_b75_exact_18_slot_algorithm():
    sources = [
        {"source_id": f"youtube_s{i}", "video_id": f"s{i}", "channel_id": "UC5LyYg6cCA4yHEYvtUsir3g", "duration_seconds": 4000.0, "title": "雑談", "selection_rank": i}
        for i in range(1, 4)
    ]
    result = {
        "schema": "uruha_p3_b76_official_channel_inventory_result_v1", "version": "1.0.0", "status": "frame_frozen",
        "provider_inventory_process_invocation_count": 1, "caption_metadata_access_count": 0, "caption_content_access_count": 0,
        "media_playback_count": 0, "model_call_count": 0, "outcome_access_count": 0, "retry_count": 0, "fallback_count": 0,
        "raw_inventory_stdout_or_stderr_persisted": False, "selected_sources": sources,
        "sampling_slots": b75.build_slots(sources, b76.b75_slot_contract()), "claim_boundary": b76.load_contract()["claim_boundary"],
    }
    result["result_hash"] = b76.sha256_bytes(b76.canonical_json(result).encode("utf-8"))
    assert b76.validate_result(result) == {"valid": True, "errors": []}
    assert len(result["sampling_slots"]) == 18
    changed = deepcopy(result)
    changed["sampling_slots"][0]["search_region_seconds"][0] += 1
    unhashed = {key: value for key, value in changed.items() if key != "result_hash"}
    changed["result_hash"] = b76.sha256_bytes(b76.canonical_json(unhashed).encode("utf-8"))
    assert "frame" in b76.validate_result(changed)["errors"]


def test_insufficient_result_is_valid_terminal_without_fallback():
    result = {
        "schema": "uruha_p3_b76_official_channel_inventory_result_v1", "version": "1.0.0",
        "status": "insufficient_eligible_sources", "provider_inventory_process_invocation_count": 1,
        "caption_metadata_access_count": 0, "caption_content_access_count": 0, "media_playback_count": 0,
        "model_call_count": 0, "outcome_access_count": 0, "retry_count": 0, "fallback_count": 0,
        "raw_inventory_stdout_or_stderr_persisted": False, "eligible_source_count_found": 0, "selected_sources": [],
        "claim_boundary": b76.load_contract()["claim_boundary"],
    }
    result["result_hash"] = b76.sha256_bytes(b76.canonical_json(result).encode("utf-8"))
    assert b76.validate_result(result) == {"valid": True, "errors": []}
