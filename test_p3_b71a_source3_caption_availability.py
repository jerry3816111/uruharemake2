from copy import deepcopy
import json

import p3_b71a_source3_caption_availability as b71a


def test_contract_binds_frozen_source3_and_metadata_only_boundary():
    assert b71a.validate_contract() == {"valid": True, "errors": []}
    contract = b71a.load_contract()
    assert contract["source"]["video_id"] == "j6Hlk9cY9LQ"
    assert contract["probe"]["resolver_process_invocation_count_max"] == 1
    assert contract["probe"]["caption_content_download_count_max"] == 0
    assert all(contract["denied_actions"].values())


def test_command_cannot_download_caption_content_or_change_source():
    command = b71a.build_command()
    assert "--skip-download" in command
    assert "--no-write-subs" in command
    assert "--no-write-auto-subs" in command
    assert "--write-subs" not in command
    assert "--write-auto-subs" not in command
    assert command[-1] == "https://www.youtube.com/watch?v=j6Hlk9cY9LQ"


def test_parser_projects_availability_without_track_urls():
    contract = b71a.load_contract()
    payload = (json.dumps({}) + "\n" + json.dumps({"ja": [{"ext": "json3", "url": "PRIVATE"}]}) + "\n").encode()
    projection = b71a.b59.parse_private_probe_output(payload, b71a.b69a._b59_parse_contract(contract))
    assert projection["selected_track_type"] == "automatic"
    assert projection["selected_format"] == "json3"
    assert "url" not in projection


def test_result_validator_accepts_available_metadata_only_result():
    result = {
        "schema": "uruha_p3_b71a_source3_caption_availability_result_v1",
        "version": "1.0.0",
        "status": "available",
        "source_id": "youtube_j6Hlk9cY9LQ",
        "resolver_process_invocation_count": 1,
        "caption_content_download_count": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "model_call_count": 0,
        "future_content_access_count": 0,
        "training_write_count": 0,
        "production_write_count": 0,
        "raw_stdout_stderr_or_track_url_persisted": False,
        "selected_track_type": "automatic",
        "selected_language_code": "ja",
        "selected_format": "json3",
    }
    b71a._finalize(result)
    assert b71a.validate_result(result) == {"valid": True, "errors": []}


def test_contract_rejects_source_content_or_substitution_drift():
    contract = b71a.load_contract()
    drifted = deepcopy(contract)
    drifted["source"]["video_id"] = "Mlk5e3hBnb8"
    assert "source" in b71a.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["probe"]["caption_content_download_count_max"] = 1
    assert "probe_limits" in b71a.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["denied_actions"]["source_query_or_window_substitution"] = False
    assert "denied" in b71a.validate_contract(drifted)["errors"]


def test_implementation_freeze_matches_frozen_files():
    assert b71a.validate_implementation_freeze() == {
        "valid": True,
        "resolver_process_invocation_count_at_freeze": 0,
        "caption_content_download_count_at_freeze": 0,
    }
