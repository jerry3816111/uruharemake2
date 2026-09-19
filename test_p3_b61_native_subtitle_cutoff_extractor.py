from copy import deepcopy
import json

import pytest

import p3_b61_native_subtitle_cutoff_extractor as b61


def test_contract_binds_b60_final_correction_and_same_cutoff():
    assert b61.validate_contract() == {"valid": True, "errors": []}
    contract = b61.load_contract()
    assert contract["authorization"]["native_downloader_process_invocation_count_max"] == 1
    assert contract["authorization"]["retry_or_fallback_authorized"] is False
    assert contract["source"]["selected_track_type"] == "automatic"
    assert contract["source"]["selected_language_code"] == "ja"
    assert contract["source"]["selected_format"] == "json3"
    assert contract["cutoff_and_publication"]["context_start_milliseconds"] == 3000000
    assert contract["cutoff_and_publication"]["context_end_milliseconds"] == 3180000
    assert contract["failure_policy"]["final_caption_path_correction"] is True
    assert contract["failure_policy"]["same_path_retry_after_failure_allowed"] is False
    assert all(contract["denied_actions"].values())


def test_native_command_downloads_only_frozen_auto_caption_without_cookie(tmp_path):
    command = b61.build_native_downloader_command(tmp_path)
    assert "--skip-download" in command
    assert "--write-auto-subs" in command
    assert command[command.index("--sub-langs") + 1] == "ja"
    assert command[command.index("--sub-format") + 1] == "json3"
    assert command[command.index("--retries") + 1] == "0"
    assert command[command.index("--fragment-retries") + 1] == "0"
    assert command[command.index("--extractor-retries") + 1] == "0"
    assert command[command.index("-o") + 1] == str(tmp_path / "caption.%(ext)s")
    assert not any("cookie" in value.lower() for value in command)
    assert "--write-info-json" not in command


def test_private_caption_reader_accepts_one_json3_and_rejects_extra_or_large(tmp_path):
    caption = tmp_path / "caption.ja.json3"
    caption.write_text('{"events":[]}', encoding="utf-8")
    path, payload = b61.read_single_private_caption(tmp_path)
    assert path == caption
    assert payload == b'{"events":[]}'
    extra = tmp_path / "extra.json3"
    extra.write_text('{"events":[]}', encoding="utf-8")
    with pytest.raises(b61.B61ExecutionError, match="caption file count"):
        b61.read_single_private_caption(tmp_path)


def test_b60_cutoff_projection_remains_exact_with_future_sentinel():
    raw = json.dumps(
        {
            "events": [
                {"tStartMs": 3000000, "dDurationMs": 500, "segs": [{"utf8": "CONTEXT"}]},
                {"tStartMs": 3179500, "dDurationMs": 1000, "segs": [{"utf8": "CROSS-FUTURE"}]},
                {"tStartMs": 3181000, "dDurationMs": 500, "segs": [{"utf8": "FUTURE-SENTINEL"}]},
            ]
        }
    ).encode()
    artifact = b61.b60.extract_context_artifact(raw, b61.b60.load_contract())
    serialized = b61.canonical_json(artifact)
    assert len(artifact["cues"]) == 1
    assert artifact["cues"][0]["text"] == "CONTEXT"
    assert "CROSS-FUTURE" not in serialized
    assert "FUTURE-SENTINEL" not in serialized


def test_result_validator_accepts_redacted_success_and_rejects_future_or_text():
    result = b61._base_result(b61.load_contract())
    result.update(
        {
            "status": "caption_context_published",
            "native_downloader_process_invocation_count": 1,
            "downloader_returncode": 0,
            "private_acquisition_full_caption_access_count": 1,
            "private_acquisition_may_include_post_cutoff_content": True,
            "private_caption_deleted_before_fresh_reader": True,
            "private_runtime_deleted_before_fresh_reader": True,
            "public_artifact_count": 1,
            "public_manifest_count": 1,
            "public_cue_count": 1,
            "public_first_cue_start_seconds": 3000.0,
            "public_last_cue_end_seconds": 3179.5,
            "public_artifact_sha256": "a" * 64,
            "fresh_public_reader_count": 1,
            "fresh_public_reader_exit_code": 0,
            "fresh_reader_artifact_sha256": "a" * 64,
            "fresh_reader_caption_text_returned": False,
        }
    )
    b61._finalize_result(result)
    assert b61.validate_result(result) == {"valid": True, "errors": []}
    leaked = deepcopy(result)
    leaked["caption_text"] = "FUTURE-SENTINEL"
    b61._finalize_result(leaked)
    assert "forbidden_key:caption_text" in b61.validate_result(leaked)["errors"]
    future = deepcopy(result)
    future["prediction_side_future_access_count"] = 1
    b61._finalize_result(future)
    assert "prediction_side_future_access_count" in b61.validate_result(future)["errors"]


def test_contract_drift_to_retry_cookie_media_or_cutoff_fails():
    contract = b61.load_contract()
    drifted = deepcopy(contract)
    drifted["native_downloader"]["network_retry_count"] = 1
    assert "retries" in b61.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["native_downloader"]["cookies_or_browser_session_allowed"] = True
    assert "native_denial:cookies_or_browser_session_allowed" in b61.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["native_downloader"]["media_file_download_allowed"] = True
    assert "native_denial:media_file_download_allowed" in b61.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["cutoff_and_publication"]["context_end_milliseconds"] = 3241000
    assert "cutoff" in b61.validate_contract(drifted)["errors"]


def test_preexisting_state_or_public_artifact_fails_before_download(monkeypatch, tmp_path):
    monkeypatch.setattr(b61, "ROOT", tmp_path)
    contract = b61.load_contract()
    state_root = tmp_path / contract["runtime_state"]["state_root"]
    state_root.mkdir(parents=True)
    with pytest.raises(b61.B61ExecutionError, match="already consumed"):
        b61._fresh_roots(contract)
    state_root.rmdir()
    public_root = tmp_path / contract["cutoff_and_publication"]["public_root"]
    public_root.mkdir(parents=True)
    (public_root / "occupied").write_bytes(b"x")
    with pytest.raises(b61.B61ExecutionError, match="nonempty"):
        b61._fresh_roots(contract)


def test_implementation_freeze_matches_frozen_files():
    assert b61.validate_implementation_freeze() == {
        "valid": True,
        "native_downloader_process_invocation_count_at_freeze": 0,
        "prediction_side_future_access_count_at_freeze": 0,
    }
