from copy import deepcopy
from pathlib import Path

import pytest

import p3_b55_reserved_source_context_transport as b55


def test_contract_binds_b54_release_and_one_transport_attempt():
    assert b55.validate_contract() == {"valid": True, "errors": []}
    contract = b55.load_contract()
    assert contract["transport"]["maximum_attempts"] == 1
    assert contract["failure_policy"]["retry_count"] == 0
    assert contract["failure_policy"]["fallback_count"] == 0
    assert contract["execution_authorization"]["hidden_future_media_request_authorized"] is False
    assert contract["execution_authorization"]["prediction_execution_authorized"] is False


def test_transport_command_is_exactly_context_only_and_ignores_user_configuration(tmp_path):
    command = b55.build_transport_command(tmp_path)
    assert command[1] == "--ignore-config"
    assert command[command.index("--download-sections") + 1] == "*3000-3180"
    assert command[command.index("--retries") + 1] == "0"
    assert command[command.index("--fragment-retries") + 1] == "0"
    assert command[command.index("--extractor-retries") + 1] == "0"
    assert "--force-keyframes-at-cuts" in command
    assert "--no-playlist" in command
    assert "--no-write-info-json" in command
    assert "--no-write-subs" in command
    assert "--no-write-auto-subs" in command
    assert "--no-write-comments" in command
    assert "--no-cache-dir" in command
    assert not any("cookie" in item.lower() for item in command)
    assert command[-1] == "https://www.youtube.com/watch?v=4y5GiQpgJgo"


def test_contract_drift_to_future_or_retry_fails():
    contract = b55.load_contract()
    future = deepcopy(contract)
    future["transport"]["download_section"] = "*3181-3241"
    assert "download_section" in b55.validate_contract(future)["errors"]
    retry = deepcopy(contract)
    retry["transport"]["network_retry_count"] = 1
    assert "transport_retries" in b55.validate_contract(retry)["errors"]


def test_preexisting_runtime_state_or_public_artifact_fails_before_transport(monkeypatch, tmp_path):
    monkeypatch.setattr(b55, "ROOT", tmp_path)
    contract = b55.load_contract()
    state_root = tmp_path / contract["crash_safe_state"]["root"]
    state_root.mkdir(parents=True)
    with pytest.raises(b55.B55ExecutionError, match="already consumed"):
        b55._fresh_runtime_roots(contract)
    state_root.rmdir()
    public_root = tmp_path / contract["public_output"]["root"]
    public_root.mkdir(parents=True)
    (public_root / "existing.wav").write_bytes(b"occupied")
    with pytest.raises(b55.B55ExecutionError, match="already nonempty"):
        b55._fresh_runtime_roots(contract)


def test_failure_receipt_validator_requires_zero_public_artifacts():
    contract = b55.load_contract()
    result = b55._base_result(contract)
    result.update(
        {
            "status": "reserved_source_context_transport_failed",
            "failure_stage": "network_transport",
            "failure_class": "B55ExecutionError",
        }
    )
    b55._finalize_result(result)
    assert b55.validate_result(result) == {"valid": True, "errors": []}
    invalid = deepcopy(result)
    invalid["public_artifact_count"] = 1
    b55._finalize_result(invalid)
    assert "failure_public_counts" in b55.validate_result(invalid)["errors"]


def test_success_receipt_requires_hash_duration_delete_and_fresh_reader():
    contract = b55.load_contract()
    result = b55._base_result(contract)
    result.update(
        {
            "status": "reserved_source_context_transport_passed",
            "network_attempt_count": 1,
            "transport_returncode": 0,
            "private_transport_deleted_before_fresh_public_reader": True,
            "public_artifact_count": 1,
            "public_manifest_count": 1,
            "fresh_public_reader_count": 1,
            "fresh_public_reader_exit_code": 0,
            "public_artifact_duration_seconds": 180.0,
            "public_artifact_sha256": "a" * 64,
            "fresh_reader_artifact_sha256": "a" * 64,
        }
    )
    b55._finalize_result(result)
    assert b55.validate_result(result) == {"valid": True, "errors": []}


def test_implementation_freeze_matches_frozen_files():
    assert b55.validate_implementation_freeze() == {
        "valid": True,
        "reserved_source_media_request_count_at_freeze": 0,
        "hidden_future_media_request_count_at_freeze": 0,
    }
