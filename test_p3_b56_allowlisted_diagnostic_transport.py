from copy import deepcopy

import pytest

import p3_b55_reserved_source_context_transport as b55_v1
import p3_b55_reserved_source_context_transport_v2 as b55_v2
import p3_b56_allowlisted_diagnostic_transport as b56


def test_contract_binds_review_authorization_and_preserves_transport_boundary():
    assert b56.validate_contract() == {"valid": True, "errors": []}
    contract = b56.load_contract()
    assert contract["authorization"]["overrides_b55_next_execution_authorized_false"] is True
    assert contract["authorization"]["diagnostic_transport_request_count_max"] == 1
    assert contract["authorization"]["additional_retry_or_correction_authorized"] is False
    assert contract["unchanged_transport"]["download_section"] == "*3000-3180"
    assert contract["unchanged_transport"]["network_retry_count"] == 0
    assert all(contract["denied_actions"].values())


@pytest.mark.parametrize(
    ("private_stderr", "expected"),
    [
        (b"ERROR: no such option: --secret-canary", "command_or_option"),
        (b"Sign in to confirm you're not a bot secret-canary", "provider_challenge_or_authentication"),
        (b"This video is private secret-canary", "source_unavailable_or_private"),
        (b"SSL certificate verify failed secret-canary", "tls_or_network"),
        (b"ffmpeg postprocessing failed secret-canary", "ffmpeg_or_postprocessing"),
        (b"Requested format is not available secret-canary", "extractor_or_format"),
        (b"secret-canary with no known signature", "unknown"),
    ],
)
def test_private_stderr_classifier_returns_only_allowlisted_category(private_stderr, expected):
    observed = b56.classify_private_stderr(private_stderr)
    assert observed == expected
    assert "secret-canary" not in observed


def test_classifier_priority_is_frozen():
    # A message containing both option and network words must retain the first
    # frozen category rather than changing according to token order.
    assert b56.classify_private_stderr(
        b"network failed because of an invalid option"
    ) == "command_or_option"


def test_diagnostic_command_is_byte_equivalent_to_b55_v2_for_same_private_root(tmp_path):
    b55_contract = b55_v2.load_contract()
    expected = b55_v1.build_transport_command(tmp_path, b55_contract)
    observed = b56.build_diagnostic_transport_command(tmp_path)
    assert observed == expected
    assert observed[observed.index("--download-sections") + 1] == "*3000-3180"
    assert observed[observed.index("--retries") + 1] == "0"
    assert observed[observed.index("--fragment-retries") + 1] == "0"
    assert observed[observed.index("--extractor-retries") + 1] == "0"
    assert not any("cookie" in item.lower() for item in observed)


def test_failure_result_persists_category_and_counts_but_no_stderr_material():
    contract = b56.load_contract()
    result = b56._base_result(contract)
    result.update(
        {
            "status": "diagnostic_transport_failed",
            "diagnostic_category": "provider_challenge_or_authentication",
            "network_attempt_count": 1,
            "transport_returncode": 1,
            "transport_stderr_bytes_discarded": 123,
            "private_runtime_deleted_before_result": True,
            "failure_stage": "network_transport",
            "failure_class": "B56ExecutionError",
        }
    )
    b56._finalize_result(result)
    assert b56.validate_result(result) == {"valid": True, "errors": []}
    serialized = b56.canonical_json(result)
    assert "secret-canary" not in serialized
    assert "https://" not in serialized
    assert "stderr_content" not in serialized
    assert "stderr_sha256" not in serialized


def test_result_validator_rejects_raw_stderr_or_future_access_even_with_new_hash():
    contract = b56.load_contract()
    result = b56._base_result(contract)
    result.update(
        {
            "status": "diagnostic_transport_failed",
            "diagnostic_category": "unknown",
            "private_runtime_deleted_before_result": True,
            "failure_stage": "network_transport",
            "failure_class": "B56ExecutionError",
            "stderr_text": "secret-canary",
            "hidden_future_media_request_count": 1,
        }
    )
    b56._finalize_result(result)
    report = b56.validate_result(result)
    assert "forbidden_result_key:stderr_text" in report["errors"]
    assert "hidden_future_media_request_count" in report["errors"]


def test_contract_drift_to_future_or_retry_fails():
    contract = b56.load_contract()
    drifted = deepcopy(contract)
    drifted["unchanged_transport"]["download_section"] = "*3181-3241"
    assert "transport_drift" in b56.validate_contract(drifted)["errors"]
    drifted = deepcopy(contract)
    drifted["unchanged_transport"]["network_retry_count"] = 1
    assert "transport_drift" in b56.validate_contract(drifted)["errors"]


def test_preexisting_state_or_public_output_fails_before_network(monkeypatch, tmp_path):
    monkeypatch.setattr(b56, "ROOT", tmp_path)
    contract = b56.load_contract()
    state_root = tmp_path / contract["runtime_state"]["state_root"]
    state_root.mkdir(parents=True)
    with pytest.raises(b56.B56ExecutionError, match="already consumed"):
        b56._fresh_runtime_roots(contract)
    state_root.rmdir()
    public_root = tmp_path / contract["runtime_state"]["public_root"]
    public_root.mkdir(parents=True)
    (public_root / "occupied").write_bytes(b"x")
    with pytest.raises(b56.B56ExecutionError, match="already nonempty"):
        b56._fresh_runtime_roots(contract)


def test_implementation_freeze_matches_frozen_files():
    assert b56.validate_implementation_freeze() == {
        "valid": True,
        "b56_diagnostic_request_count_at_freeze": 0,
        "hidden_future_media_request_count_at_freeze": 0,
    }
