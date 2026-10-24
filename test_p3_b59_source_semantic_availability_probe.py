from copy import deepcopy
import json

import pytest

import p3_b59_source_semantic_availability_probe as b59


def _payload(manual, automatic):
    return (json.dumps(manual) + "\n" + json.dumps(automatic) + "\n").encode()


def test_contract_binds_closed_audio_branch_and_preserves_content_lock():
    assert b59.validate_contract() == {"valid": True, "errors": []}
    contract = b59.load_contract()
    assert contract["authorization"]["resolver_process_invocation_count_max"] == 1
    assert contract["authorization"]["caption_content_download_count_max"] == 0
    assert contract["authorization"]["retry_or_fallback_authorized"] is False
    assert contract["decision"]["automatic_next_execution_allowed"] is False
    assert contract["source"]["context_end_seconds"] == 3180.0
    assert contract["source"]["hidden_future_start_seconds"] == 3181.0
    assert all(contract["denied_actions"].values())


def test_probe_command_prints_metadata_only_without_caption_download_or_cookie():
    command = b59.build_probe_command()
    indexes = [index for index, value in enumerate(command) if value == "--print"]
    assert [command[index + 1] for index in indexes] == [
        "%(subtitles)j",
        "%(automatic_captions)j",
    ]
    assert "--skip-download" in command
    assert "--no-write-subs" in command
    assert "--no-write-auto-subs" in command
    assert "--no-write-info-json" in command
    assert "--no-cache-dir" in command
    assert command[command.index("--retries") + 1] == "0"
    assert command[command.index("--fragment-retries") + 1] == "0"
    assert command[command.index("--extractor-retries") + 1] == "0"
    assert not any("cookie" in value.lower() for value in command)
    assert not any(value in {"-o", "--output", "--write-subs", "--write-auto-subs"} for value in command)


def test_projection_prefers_manual_japanese_and_persists_no_track_url():
    payload = _payload(
        {
            "ja": [
                {"ext": "vtt", "url": "https://private.example/manual?token=CANARY"},
                {"ext": "json3", "url": "https://private.example/manual-json?token=CANARY"},
            ],
            "en": [{"ext": "vtt", "url": "https://private.example/en"}],
        },
        {
            "ja": [{"ext": "json3", "url": "https://private.example/auto?token=CANARY"}],
            "zh-Hant": [{"ext": "vtt", "url": "https://private.example/zh"}],
        },
    )
    projection = b59.parse_private_probe_output(payload)
    assert projection == {
        "manual_language_code_count": 2,
        "automatic_language_code_count": 2,
        "manual_japanese_available": True,
        "automatic_japanese_available": True,
        "selected_track_type": "manual",
        "selected_language_code": "ja",
        "selected_format": "json3",
    }
    serialized = b59.canonical_json(projection)
    assert "private.example" not in serialized
    assert "CANARY" not in serialized


def test_projection_uses_automatic_when_manual_japanese_is_absent():
    projection = b59.parse_private_probe_output(
        _payload(
            {"en": [{"ext": "vtt", "url": "https://private.example/en"}]},
            {"ja": [{"ext": "vtt", "url": "https://private.example/ja"}]},
        )
    )
    assert projection["manual_japanese_available"] is False
    assert projection["automatic_japanese_available"] is True
    assert projection["selected_track_type"] == "automatic"
    assert projection["selected_language_code"] == "ja"
    assert projection["selected_format"] == "vtt"


def test_projection_records_unavailable_without_inventing_selection():
    projection = b59.parse_private_probe_output(_payload({}, {}))
    assert projection == {
        "manual_language_code_count": 0,
        "automatic_language_code_count": 0,
        "manual_japanese_available": False,
        "automatic_japanese_available": False,
        "selected_track_type": None,
        "selected_language_code": None,
        "selected_format": None,
    }


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"{}\n",
        b"{}\n{}\nextra\n",
        b"not-json\n{}\n",
        b"[]\n{}\n",
        b'{"ja":{}}\n{}\n',
        b'{"ja":["not-an-object"]}\n{}\n',
    ],
)
def test_probe_output_rejects_malformed_private_metadata(payload):
    with pytest.raises(b59.B59ExecutionError):
        b59.parse_private_probe_output(payload)


def test_result_validator_accepts_redacted_availability_and_rejects_content():
    result = b59._base_result(b59.load_contract())
    result.update(
        {
            "status": "availability_probe_passed",
            "resolver_process_invocation_count": 1,
            "resolver_returncode": 0,
            "private_metadata_cleared_before_result": True,
            "availability_projection": {
                "manual_language_code_count": 0,
                "automatic_language_code_count": 1,
                "manual_japanese_available": False,
                "automatic_japanese_available": True,
                "selected_track_type": "automatic",
                "selected_language_code": "ja",
                "selected_format": "json3",
            },
            "next_stage": "caption_acquisition_design",
        }
    )
    b59._finalize_result(result)
    assert b59.validate_result(result) == {"valid": True, "errors": []}
    leaked = deepcopy(result)
    leaked["caption_text"] = "PRIVATE-CANARY"
    b59._finalize_result(leaked)
    assert "forbidden_key:caption_text" in b59.validate_result(leaked)["errors"]
    future = deepcopy(result)
    future["hidden_future_content_access_count"] = 1
    b59._finalize_result(future)
    assert "hidden_future_content_access_count" in b59.validate_result(future)["errors"]


def test_contract_drift_to_content_cookie_retry_or_future_fails():
    contract = b59.load_contract()
    drifted = deepcopy(contract)
    drifted["probe"]["caption_content_download_allowed"] = True
    assert "probe_denial:caption_content_download_allowed" in b59.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["probe"]["cookies_or_browser_session_allowed"] = True
    assert "probe_denial:cookies_or_browser_session_allowed" in b59.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["probe"]["network_retry_count"] = 1
    assert "probe_retries" in b59.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["source"]["context_start_seconds"] = 3181.0
    assert "source_boundary" in b59.validate_contract(drifted)["errors"]


def test_preexisting_state_fails_before_probe(monkeypatch, tmp_path):
    monkeypatch.setattr(b59, "ROOT", tmp_path)
    contract = b59.load_contract()
    state_root = tmp_path / contract["runtime_state"]["state_root"]
    state_root.mkdir(parents=True)
    with pytest.raises(b59.B59ExecutionError, match="already consumed"):
        b59._fresh_state_root(contract)


def test_implementation_freeze_matches_frozen_files():
    assert b59.validate_implementation_freeze() == {
        "valid": True,
        "resolver_process_invocation_count_at_freeze": 0,
        "caption_content_download_count_at_freeze": 0,
        "hidden_future_content_access_count_at_freeze": 0,
    }
