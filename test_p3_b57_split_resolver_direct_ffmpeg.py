from copy import deepcopy
from pathlib import Path

import pytest

import p3_b57_split_resolver_direct_ffmpeg as b57


def test_contract_binds_b56_review_and_preserves_future_lock():
    assert b57.validate_contract() == {"valid": True, "errors": []}
    contract = b57.load_contract()
    assert contract["authorization"]["overrides_b56_next_execution_authorized_false"] is True
    assert contract["authorization"]["resolver_process_invocation_count_max"] == 1
    assert contract["authorization"]["direct_ffmpeg_process_invocation_count_max"] == 1
    assert contract["authorization"]["retry_or_additional_correction_authorized"] is False
    assert contract["source"]["context_start_seconds"] == 3000.0
    assert contract["source"]["context_end_seconds"] == 3180.0
    assert all(contract["denied_actions"].values())


def test_resolver_command_returns_url_only_without_cookie_or_download_capability():
    command = b57.build_resolver_command()
    assert command[1] == "--ignore-config"
    assert "--get-url" in command
    assert command[command.index("-f") + 1] == "bestaudio/best"
    assert command[command.index("--retries") + 1] == "0"
    assert command[command.index("--fragment-retries") + 1] == "0"
    assert command[command.index("--extractor-retries") + 1] == "0"
    assert "--no-playlist" in command
    assert "--no-write-info-json" in command
    assert "--no-write-subs" in command
    assert "--no-write-auto-subs" in command
    assert "--no-write-comments" in command
    assert "--no-cache-dir" in command
    assert not any("cookie" in value.lower() for value in command)
    assert not any(value in {"-o", "--output"} for value in command)
    assert command[-1] == "https://www.youtube.com/watch?v=4y5GiQpgJgo"


def test_private_url_parser_accepts_one_https_googlevideo_url_only():
    private_url = (
        b"https://rr1---sn-test.googlevideo.com/videoplayback?sig=PRIVATE-CANARY\n"
    )
    parsed = b57.parse_private_media_url(private_url)
    assert parsed.endswith("sig=PRIVATE-CANARY")
    for rejected in (
        b"",
        b"https://rr1.googlevideo.com/a\nhttps://rr2.googlevideo.com/b\n",
        b"http://rr1.googlevideo.com/a\n",
        b"https://youtube.com/watch?v=x\n",
        b"https://user:password@rr1.googlevideo.com/a\n",
    ):
        with pytest.raises(b57.B57ExecutionError, match="resolver URL"):
            b57.parse_private_media_url(rejected)


def test_direct_ffmpeg_command_uses_exact_frozen_interval_and_audio_profile(tmp_path):
    private_url = "https://rr1.googlevideo.com/videoplayback?sig=PRIVATE-CANARY"
    output = tmp_path / "bounded.wav"
    command = b57.build_direct_ffmpeg_command(private_url, output)
    assert command[command.index("-ss") + 1] == "3000.000000"
    assert command[command.index("-i") + 1] == private_url
    assert command[command.index("-t") + 1] == "180.000000"
    assert command[command.index("-map") + 1] == "0:a:0"
    assert command[command.index("-ac") + 1] == "1"
    assert command[command.index("-ar") + 1] == "16000"
    assert command[command.index("-c:a") + 1] == "pcm_s16le"
    assert command[-1] == str(output)


def test_failure_receipt_contains_no_url_or_raw_diagnostics():
    contract = b57.load_contract()
    result = b57._base_result(contract)
    result.update(
        {
            "status": "split_transport_failed",
            "resolver_process_invocation_count": 1,
            "resolver_returncode": 0,
            "resolver_stdout_bytes_discarded": 80,
            "resolver_url_count": 1,
            "resolver_url_host_category": "googlevideo_cdn",
            "direct_ffmpeg_process_invocation_count": 1,
            "direct_ffmpeg_returncode": 1,
            "direct_ffmpeg_stderr_bytes_discarded": 35,
            "signed_url_reference_cleared_before_public_reader": True,
            "private_runtime_deleted_before_public_reader": True,
            "failure_stage": "direct_ffmpeg",
            "failure_category": "tls_or_network",
            "failure_class": "B57ExecutionError",
        }
    )
    b57._finalize_result(result)
    assert b57.validate_result(result) == {"valid": True, "errors": []}
    serialized = b57.canonical_json(result)
    assert "PRIVATE-CANARY" not in serialized
    assert "googlevideo.com" not in serialized
    assert "videoplayback" not in serialized


def test_result_validator_rejects_url_persistence_and_future_access():
    contract = b57.load_contract()
    result = b57._base_result(contract)
    result.update(
        {
            "status": "split_transport_failed",
            "failure_stage": "resolver",
            "failure_category": "unknown",
            "failure_class": "B57ExecutionError",
            "private_runtime_deleted_before_public_reader": True,
            "signed_url": "https://rr1.googlevideo.com/private",
            "hidden_future_media_request_count": 1,
        }
    )
    b57._finalize_result(result)
    report = b57.validate_result(result)
    assert "forbidden_key:signed_url" in report["errors"]
    assert "hidden_future_media_request_count" in report["errors"]


def test_contract_drift_to_future_retry_or_cookie_fails():
    contract = b57.load_contract()
    drifted = deepcopy(contract)
    drifted["source"]["context_start_seconds"] = 3181.0
    assert "source_boundary" in b57.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["resolver"]["network_retry_count"] = 1
    assert "resolver_retries" in b57.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["resolver"]["cookies_or_browser_session_allowed"] = True
    assert "resolver_denial:cookies_or_browser_session_allowed" in b57.validate_contract(drifted)["errors"]


def test_preexisting_state_or_public_output_fails_before_resolver(monkeypatch, tmp_path):
    monkeypatch.setattr(b57, "ROOT", tmp_path)
    contract = b57.load_contract()
    state_root = tmp_path / contract["runtime_state"]["state_root"]
    state_root.mkdir(parents=True)
    with pytest.raises(b57.B57ExecutionError, match="already consumed"):
        b57._fresh_runtime_roots(contract)
    state_root.rmdir()
    public_root = tmp_path / contract["runtime_state"]["public_root"]
    public_root.mkdir(parents=True)
    (public_root / "occupied").write_bytes(b"x")
    with pytest.raises(b57.B57ExecutionError, match="nonempty"):
        b57._fresh_runtime_roots(contract)


def test_implementation_freeze_matches_frozen_files():
    assert b57.validate_implementation_freeze() == {
        "valid": True,
        "resolver_process_invocation_count_at_freeze": 0,
        "direct_ffmpeg_process_invocation_count_at_freeze": 0,
        "hidden_future_media_request_count_at_freeze": 0,
    }
