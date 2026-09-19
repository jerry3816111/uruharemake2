from copy import deepcopy
import json

import p3_b69a_source2_caption_availability as b69a


def test_contract_binds_frozen_source_and_metadata_only_boundary():
    assert b69a.validate_contract() == {"valid": True, "errors": []}
    contract = b69a.load_contract()
    assert contract["source"]["video_id"] == "Mlk5e3hBnb8"
    assert contract["probe"]["resolver_process_invocation_count_max"] == 1
    assert contract["probe"]["caption_content_download_count_max"] == 0
    assert all(contract["denied_actions"].values())


def test_command_cannot_download_caption_content():
    command = b69a.build_command()
    assert "--skip-download" in command
    assert "--no-write-subs" in command
    assert "--no-write-auto-subs" in command
    assert "--write-subs" not in command
    assert "--write-auto-subs" not in command
    assert command[-1] == "https://www.youtube.com/watch?v=Mlk5e3hBnb8"


def test_b59_parser_projects_availability_without_track_urls():
    contract = b69a.load_contract()
    manual = {}
    automatic = {"ja": [{"ext": "json3", "url": "PRIVATE"}]}
    payload = (json.dumps(manual) + "\n" + json.dumps(automatic) + "\n").encode()
    projection = b69a.b59.parse_private_probe_output(payload, b69a._b59_parse_contract(contract))
    assert projection["selected_track_type"] == "automatic"
    assert projection["selected_format"] == "json3"
    assert "url" not in projection


def test_result_validator_accepts_available_metadata_only_result():
    result = {
        "schema": "uruha_p3_b69a_source2_caption_availability_result_v1", "version": "1.0.0",
        "status": "available", "source_id": "youtube_Mlk5e3hBnb8",
        "resolver_process_invocation_count": 1, "caption_content_download_count": 0,
        "retry_count": 0, "fallback_count": 0, "model_call_count": 0,
        "future_content_access_count": 0, "training_write_count": 0, "production_write_count": 0,
        "raw_stdout_stderr_or_track_url_persisted": False, "selected_track_type": "automatic",
        "selected_language_code": "ja", "selected_format": "json3",
    }
    b69a._finalize(result)
    assert b69a.validate_result(result) == {"valid": True, "errors": []}


def test_contract_rejects_source_content_or_substitution_drift():
    contract = b69a.load_contract()
    drifted = deepcopy(contract)
    drifted["source"]["video_id"] = "4y5GiQpgJgo"
    assert "source" in b69a.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["probe"]["caption_content_download_count_max"] = 1
    assert "probe_limits" in b69a.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["denied_actions"]["source_or_window_substitution"] = False
    assert "denied" in b69a.validate_contract(drifted)["errors"]


def test_implementation_freeze_matches_frozen_files():
    assert b69a.validate_implementation_freeze() == {
        "valid": True,
        "resolver_process_invocation_count_at_freeze": 0,
        "caption_content_download_count_at_freeze": 0,
    }
