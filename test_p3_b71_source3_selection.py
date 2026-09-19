from copy import deepcopy

import p3_b71_source3_selection as b71


def eligible(video_id="source3", duration=8000, channel_id="UC5LyYg6cCA4yHEYvtUsir3g", title="third"):
    return {"id": video_id, "duration": duration, "channel_id": channel_id, "title": title}


def test_contract_freezes_query_exclusions_and_windows_before_search():
    assert b71.validate_contract() == {"valid": True, "errors": []}
    contract = b71.load_contract()
    assert contract["discovery"]["excluded_video_ids"] == ["4y5GiQpgJgo", "Mlk5e3hBnb8"]
    assert contract["frozen_rows"] == b71.expected_rows()
    assert contract["discovery"]["caption_metadata_or_content_request_allowed"] is False
    assert all(contract["denied_actions"].values())


def test_search_command_is_metadata_only_single_query_without_caption_flags():
    command = b71.build_search_command("yt-dlp")
    assert command.count("--dump-single-json") == 1
    assert "--flat-playlist" in command
    assert "--skip-download" in command
    assert command[command.index("--retries") + 1] == "0"
    assert command[-1] == "ytsearch12:一ノ瀬うるは APEX 配信"
    assert not any("sub" in item.casefold() or "caption" in item.casefold() for item in command)


def test_selection_uses_first_ranked_eligible_official_source_after_exclusions():
    document = {"entries": [
        eligible("4y5GiQpgJgo"),
        eligible("offchannel", channel_id="other"),
        eligible("short", duration=7199),
        eligible("Mlk5e3hBnb8"),
        eligible("chosen", title="chosen title"),
        eligible("later"),
    ]}
    selected = b71.select_source(document)
    assert selected == {
        "source_id": "youtube_chosen",
        "video_id": "chosen",
        "channel_id": "UC5LyYg6cCA4yHEYvtUsir3g",
        "duration_seconds": 8000.0,
        "title": "chosen title",
        "selection_rank": 5,
    }


def test_no_eligible_source_is_terminal_not_manual_substitution():
    document = {"entries": [eligible("4y5GiQpgJgo"), eligible("short", duration=10)]}
    assert b71.select_source(document) is None


def test_contract_drift_in_query_exclusions_or_rows_fails():
    contract = b71.load_contract()
    drifted = deepcopy(contract)
    drifted["discovery"]["query"] = "favorable query"
    assert "discovery" in b71.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["discovery"]["excluded_video_ids"].pop()
    assert "discovery" in b71.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["frozen_rows"][0]["future_seconds"] = [780.0, 840.0]
    assert "rows" in b71.validate_contract(drifted)["errors"]


def test_valid_selected_result_requires_zero_caption_model_future_or_retry():
    result = {
        "schema": "uruha_p3_b71_source3_selection_result_v1",
        "version": "1.0.0",
        "status": "selected",
        "provider_search_process_invocation_count": 1,
        "caption_metadata_access_count": 0,
        "caption_content_access_count": 0,
        "model_call_count": 0,
        "future_access_count": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "raw_search_stdout_or_stderr_persisted": False,
        "selected_source": {
            "source_id": "youtube_source3",
            "video_id": "source3",
            "channel_id": "UC5LyYg6cCA4yHEYvtUsir3g",
            "duration_seconds": 8000.0,
            "title": "third",
            "selection_rank": 3,
        },
        "frozen_rows": b71.expected_rows(),
    }
    b71._finalize_result(result)
    assert b71.validate_result(result) == {"valid": True, "errors": []}
    result["caption_metadata_access_count"] = 1
    result = b71._finalize_result({key: value for key, value in result.items() if key != "result_hash"})
    assert "caption_metadata_access_count" in b71.validate_result(result)["errors"]


def test_implementation_freeze_matches_frozen_files():
    assert b71.validate_implementation_freeze() == {
        "valid": True,
        "provider_search_process_invocation_count_at_freeze": 0,
    }
