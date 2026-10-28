from copy import deepcopy
import json
import os

import pytest

import p3_b60_caption_context_reader as reader
import p3_b60_private_caption_cutoff_extractor as b60


def _raw_caption():
    return json.dumps(
        {
            "events": [
                {"tStartMs": 2999000, "dDurationMs": 500, "segs": [{"utf8": "BEFORE"}]},
                {"tStartMs": 3000000, "dDurationMs": 1000, "segs": [{"utf8": "過去"}]},
                {"tStartMs": 3179000, "dDurationMs": 500, "segs": [{"utf8": "境界"}]},
                {"tStartMs": 3179500, "dDurationMs": 1000, "segs": [{"utf8": "CROSS-FUTURE"}]},
                {"tStartMs": 3181000, "dDurationMs": 1000, "segs": [{"utf8": "FUTURE-SENTINEL"}]},
            ]
        },
        ensure_ascii=False,
    ).encode()


def test_contract_binds_b59_release_and_preserves_cutoff_separation():
    assert b60.validate_contract() == {"valid": True, "errors": []}
    contract = b60.load_contract()
    assert contract["authorization"]["resolver_process_invocation_count_max"] == 1
    assert contract["authorization"]["caption_get_invocation_count_max"] == 1
    assert contract["authorization"]["retry_or_fallback_authorized"] is False
    assert contract["source"]["selected_track_type"] == "automatic"
    assert contract["source"]["selected_language_code"] == "ja"
    assert contract["source"]["selected_format"] == "json3"
    assert contract["cutoff_extraction"]["context_start_milliseconds"] == 3000000
    assert contract["cutoff_extraction"]["context_end_milliseconds"] == 3180000
    assert contract["capability_separation"]["prediction_side_future_access_required"] == 0
    assert all(contract["denied_actions"].values())


def test_resolver_command_requests_private_track_metadata_without_download_or_cookie():
    command = b60.build_resolver_command()
    indexes = [index for index, value in enumerate(command) if value == "--print"]
    assert [command[index + 1] for index in indexes] == [
        "%(automatic_captions)j",
        "%(http_headers)j",
    ]
    assert "--skip-download" in command
    assert "--no-write-subs" in command
    assert "--no-write-auto-subs" in command
    assert command[command.index("--retries") + 1] == "0"
    assert not any("cookie" in value.lower() for value in command)
    assert not any(value in {"-o", "--output", "--write-auto-subs"} for value in command)


def test_private_resolver_selects_exact_track_and_allowlisted_headers():
    payload = (
        json.dumps(
            {
                "ja": [
                    {"ext": "vtt", "url": "https://www.youtube.com/api/timedtext?v=x&fmt=vtt"},
                    {"ext": "json3", "url": "https://www.youtube.com/api/timedtext?v=x&fmt=json3&token=PRIVATE"},
                ]
            }
        )
        + "\n"
        + json.dumps(
            {
                "User-Agent": "agent",
                "Accept": "*/*",
                "Accept-Language": "ja",
                "Sec-Fetch-Mode": "navigate",
            }
        )
        + "\n"
    ).encode()
    track_url, headers = b60.parse_private_resolver_output(payload)
    assert track_url.endswith("token=PRIVATE")
    assert headers == {"User-Agent": "agent", "Accept": "*/*", "Accept-Language": "ja"}


@pytest.mark.parametrize("name", ["Cookie", "Authorization", "Proxy-Authorization", "Set-Cookie"])
def test_private_resolver_rejects_sensitive_headers(name):
    payload = (
        json.dumps({"ja": [{"ext": "json3", "url": "https://www.youtube.com/api/timedtext?v=x"}]})
        + "\n"
        + json.dumps({"User-Agent": "agent", name: "PRIVATE"})
        + "\n"
    ).encode()
    with pytest.raises(b60.B60ExecutionError, match="sensitive header"):
        b60.parse_private_resolver_output(payload)


def test_cutoff_extractor_excludes_before_crossing_and_future_cues():
    artifact = b60.extract_context_artifact(_raw_caption())
    assert artifact["context_seconds"] == [3000.0, 3180.0]
    assert artifact["language_code"] == "ja"
    assert artifact["track_type"] == "automatic"
    assert artifact["cues"] == [
        {"start_seconds": 3000.0, "end_seconds": 3001.0, "text": "過去"},
        {"start_seconds": 3179.0, "end_seconds": 3179.5, "text": "境界"},
    ]
    serialized = b60.canonical_json(artifact)
    assert "BEFORE" not in serialized
    assert "CROSS-FUTURE" not in serialized
    assert "FUTURE-SENTINEL" not in serialized


def test_cutoff_extractor_rejects_invalid_or_empty_context():
    with pytest.raises(b60.B60ExecutionError, match="caption JSON"):
        b60.extract_context_artifact(b"not-json")
    with pytest.raises(b60.B60ExecutionError, match="no context cues"):
        b60.extract_context_artifact(json.dumps({"events": []}).encode())


def test_publish_and_fresh_reader_validate_hash_cutoff_and_return_no_text(monkeypatch, tmp_path):
    public_root = tmp_path / "public"
    artifact = b60.extract_context_artifact(_raw_caption())
    manifest = b60.publish_context_artifact(artifact, public_root)
    monkeypatch.setenv(reader.PUBLIC_ROOT_ENV, str(public_root))
    inspection = reader.inspect_artifact(manifest["artifact_id"])
    assert inspection["artifact_summary"]["artifact_sha256"] == manifest["artifact_sha256"]
    assert inspection["artifact_summary"]["cue_count"] == 2
    assert inspection["artifact_summary"]["first_cue_start_seconds"] == 3000.0
    assert inspection["artifact_summary"]["last_cue_end_seconds"] == 3179.5
    assert inspection["artifact_summary"]["caption_text_returned"] is False
    assert "cues" not in inspection
    assert "過去" not in b60.canonical_json(inspection)
    assert (public_root.stat().st_mode & 0o777) == 0o500


def test_fresh_reader_rejects_hash_future_forbidden_field_and_permissions(monkeypatch, tmp_path):
    public_root = tmp_path / "public"
    artifact = b60.extract_context_artifact(_raw_caption())
    manifest = b60.publish_context_artifact(artifact, public_root)
    monkeypatch.setenv(reader.PUBLIC_ROOT_ENV, str(public_root))
    artifact_path = public_root / f"{manifest['artifact_id']}.json"
    os.chmod(public_root, 0o700)
    os.chmod(artifact_path, 0o600)
    with pytest.raises(reader.B60ReaderError, match="mode"):
        reader.inspect_artifact(manifest["artifact_id"])


def test_result_validator_accepts_redacted_success_and_rejects_leakage():
    result = b60._base_result(b60.load_contract())
    result.update(
        {
            "status": "caption_context_published",
            "resolver_process_invocation_count": 1,
            "resolver_returncode": 0,
            "caption_get_invocation_count": 1,
            "caption_response_bytes_discarded_after_projection": 100,
            "private_acquisition_full_caption_access_count": 1,
            "private_acquisition_may_include_post_cutoff_content": True,
            "private_material_cleared_before_fresh_public_reader": True,
            "public_artifact_count": 1,
            "public_manifest_count": 1,
            "public_cue_count": 2,
            "public_first_cue_start_seconds": 3000.0,
            "public_last_cue_end_seconds": 3179.5,
            "public_artifact_sha256": "a" * 64,
            "fresh_public_reader_count": 1,
            "fresh_public_reader_exit_code": 0,
            "fresh_reader_artifact_sha256": "a" * 64,
            "fresh_reader_caption_text_returned": False,
        }
    )
    b60._finalize_result(result)
    assert b60.validate_result(result) == {"valid": True, "errors": []}
    leaked = deepcopy(result)
    leaked["cues"] = [{"text": "FUTURE-SENTINEL"}]
    b60._finalize_result(leaked)
    assert "forbidden_key:cues" in b60.validate_result(leaked)["errors"]
    future = deepcopy(result)
    future["prediction_side_future_access_count"] = 1
    b60._finalize_result(future)
    assert "prediction_side_future_access_count" in b60.validate_result(future)["errors"]


def test_contract_drift_to_retry_cookie_future_or_raw_persistence_fails():
    contract = b60.load_contract()
    drifted = deepcopy(contract)
    drifted["resolver"]["network_retry_count"] = 1
    assert "resolver_retries" in b60.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["resolver"]["cookies_or_browser_session_allowed"] = True
    assert "resolver_denial:cookies_or_browser_session_allowed" in b60.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["cutoff_extraction"]["context_end_milliseconds"] = 3241000
    assert "cutoff" in b60.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["capability_separation"]["private_raw_caption_persistence_allowed"] = True
    assert "separation:private_raw_caption_persistence_allowed" in b60.validate_contract(drifted)["errors"]


def test_preexisting_state_or_public_artifact_fails_before_request(monkeypatch, tmp_path):
    monkeypatch.setattr(b60, "ROOT", tmp_path)
    contract = b60.load_contract()
    state_root = tmp_path / contract["runtime_state"]["state_root"]
    state_root.mkdir(parents=True)
    with pytest.raises(b60.B60ExecutionError, match="already consumed"):
        b60._fresh_roots(contract)
    state_root.rmdir()
    public_root = tmp_path / contract["public_artifact"]["root"]
    public_root.mkdir(parents=True)
    (public_root / "occupied").write_bytes(b"x")
    with pytest.raises(b60.B60ExecutionError, match="nonempty"):
        b60._fresh_roots(contract)


def test_implementation_freeze_matches_frozen_files():
    assert b60.validate_implementation_freeze() == {
        "valid": True,
        "resolver_process_invocation_count_at_freeze": 0,
        "caption_get_invocation_count_at_freeze": 0,
        "prediction_side_future_access_count_at_freeze": 0,
    }
