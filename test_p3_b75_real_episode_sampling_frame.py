from copy import deepcopy
import json

import p3_b75_real_episode_sampling_frame as b75


def _entry(video_id, rank, *, title="【コラボ】雑談", duration=3600, channel=True):
    return {
        "id": video_id,
        "duration": duration,
        "channel_id": "UC5LyYg6cCA4yHEYvtUsir3g" if channel else "other",
        "title": title,
        "rank": rank,
    }


def test_contract_freezes_separate_observational_lane_before_content():
    contract = b75.load_contract()
    assert b75.validate_contract(contract) == {"valid": True, "errors": []}
    assert contract["lane_separation"]["controlled_context_flip_lane_is_separate"] is True
    assert contract["slot_algorithm"]["adjacent_monologue_substitution_allowed"] is False
    assert contract["slot_algorithm"]["unusable_region_is_preserved_without_replacement"] is True
    assert contract["discovery"]["caption_media_or_content_access_allowed"] is False


def test_search_command_is_one_metadata_only_no_retry_query():
    command = b75.build_search_command("/usr/bin/yt-dlp")
    assert command.count("--dump-single-json") == 1
    assert "--skip-download" in command
    assert command[command.index("--retries") + 1] == "0"
    assert command[command.index("--extractor-retries") + 1] == "0"
    assert command[-1] == "ytsearch24:一ノ瀬うるは コラボ 雑談"


def test_selection_uses_rank_official_duration_keyword_and_exclusions():
    document = {"entries": [
        _entry("4y5GiQpgJgo", 1),
        _entry("wrong-channel", 2, channel=False),
        _entry("too-short", 3, duration=1200),
        _entry("no-keyword", 4, title="APEX配信"),
        _entry("source-a", 5, title="コラボで雑談"),
        _entry("source-b", 6, title="飲酒しながら話す"),
        _entry("source-c", 7, title="質問に答える"),
        _entry("source-d", 8, title="対談"),
    ]}
    selected = b75.select_sources(document)
    assert [source["video_id"] for source in selected] == ["source-a", "source-b", "source-c"]
    assert [source["selection_rank"] for source in selected] == [5, 6, 7]


def test_slot_frame_is_exact_18_relative_regions_and_no_replacement():
    sources = [
        {"source_id": f"youtube_s{i}", "video_id": f"s{i}", "channel_id": "UC5LyYg6cCA4yHEYvtUsir3g", "duration_seconds": 4000.0 + i * 100, "title": "雑談", "selection_rank": i}
        for i in range(1, 4)
    ]
    slots = b75.build_slots(sources)
    assert len(slots) == 18
    assert [slot["relative_start_fraction"] for slot in slots[:6]] == [0.10, 0.25, 0.40, 0.55, 0.70, 0.85]
    assert all(slot["search_region_seconds"][1] - slot["search_region_seconds"][0] == 300 for slot in slots)
    assert all(slot["unusable_without_replacement"] is True for slot in slots)
    assert len({slot["slot_id"] for slot in slots}) == 18


def test_insufficient_sources_remains_terminal_negative_result_shape():
    contract = b75.load_contract()
    result = {
        "schema": "uruha_p3_b75_real_episode_sampling_frame_result_v1",
        "version": "1.0.0",
        "status": "insufficient_eligible_sources",
        "provider_search_process_invocation_count": 1,
        "caption_metadata_access_count": 0,
        "caption_content_access_count": 0,
        "media_playback_count": 0,
        "model_call_count": 0,
        "outcome_access_count": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "raw_search_stdout_or_stderr_persisted": False,
        "controlled_context_flip_lane_separate": True,
        "eligible_source_count_found": 1,
        "selected_sources": [_entry("only-one", 1)],
        "claim_boundary": contract["claim_boundary"],
    }
    result["result_hash"] = b75.sha256_bytes(b75.canonical_json(result).encode("utf-8"))
    assert b75.validate_result(result) == {"valid": True, "errors": []}


def test_result_fails_closed_on_forbidden_access_or_frame_mutation():
    sources = [
        {"source_id": f"youtube_s{i}", "video_id": f"s{i}", "channel_id": "UC5LyYg6cCA4yHEYvtUsir3g", "duration_seconds": 4000.0, "title": "雑談", "selection_rank": i}
        for i in range(1, 4)
    ]
    result = {
        "schema": "uruha_p3_b75_real_episode_sampling_frame_result_v1",
        "version": "1.0.0",
        "status": "frame_frozen",
        "provider_search_process_invocation_count": 1,
        "caption_metadata_access_count": 0,
        "caption_content_access_count": 0,
        "media_playback_count": 0,
        "model_call_count": 0,
        "outcome_access_count": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "raw_search_stdout_or_stderr_persisted": False,
        "controlled_context_flip_lane_separate": True,
        "selected_sources": sources,
        "sampling_slots": b75.build_slots(sources),
        "claim_boundary": b75.load_contract()["claim_boundary"],
    }
    result["result_hash"] = b75.sha256_bytes(b75.canonical_json(result).encode("utf-8"))
    assert b75.validate_result(result) == {"valid": True, "errors": []}
    changed = deepcopy(result)
    changed["caption_content_access_count"] = 1
    assert b75.validate_result(changed)["valid"] is False
    changed = json.loads(json.dumps(result))
    changed["sampling_slots"][0]["search_region_seconds"][0] += 1
    changed_without_hash = {key: value for key, value in changed.items() if key != "result_hash"}
    changed["result_hash"] = b75.sha256_bytes(b75.canonical_json(changed_without_hash).encode("utf-8"))
    assert "frame" in b75.validate_result(changed)["errors"]
