from copy import deepcopy

import p3_b55_reserved_source_context_transport as b55_v1
import p3_b55_reserved_source_context_transport_v2 as b55_v2


def test_v2_contract_is_bound_to_v1_zero_network_failure():
    assert b55_v2.validate_contract() == {"valid": True, "errors": []}
    contract = b55_v2.load_contract()
    failure = b55_v2.load_json(b55_v2.ROOT / contract["binding"]["v1_failure"]["path"])
    assert failure["network_attempt_count"] == 0
    assert failure["public_artifact_count"] == 0
    assert failure["hidden_future_media_request_count"] == 0


def test_v2_changes_version_probe_flag_but_not_transport_boundary(tmp_path):
    contract = b55_v2.load_contract()
    assert contract["transport"]["yt_dlp_version_command"] == ["--version"]
    assert contract["transport"]["ffmpeg_version_command"] == ["-version"]
    command = b55_v1.build_transport_command(tmp_path, contract)
    assert command[command.index("--download-sections") + 1] == "*3000-3180"
    assert command[command.index("--retries") + 1] == "0"
    assert command[command.index("--fragment-retries") + 1] == "0"
    assert command[command.index("--extractor-retries") + 1] == "0"
    assert not any("cookie" in item.lower() for item in command)


def test_v2_does_not_authorize_another_correction_or_future_access():
    contract = b55_v2.load_contract()
    assert contract["failure_policy"]["additional_correction_after_v2_failure_allowed"] is False
    assert contract["execution_authorization"]["hidden_future_media_request_authorized"] is False
    assert contract["execution_authorization"]["prediction_execution_authorized"] is False
    drifted = deepcopy(contract)
    drifted["transport"]["download_section"] = "*3181-3241"
    assert "transport_scope" in b55_v2.validate_contract(drifted)["errors"]


def test_v1_saved_failure_remains_valid():
    failure = b55_v2.load_json(
        b55_v2.ROOT
        / "analysis"
        / "p3_b55_v1_pre_network_tool_probe_failure_2026-09-18.json"
    )
    assert b55_v1.validate_result(failure) == {"valid": True, "errors": []}


def test_v2_implementation_freeze_matches_frozen_files():
    assert b55_v2.validate_implementation_freeze() == {
        "valid": True,
        "v1_network_attempt_count_at_freeze": 0,
        "v2_network_attempt_count_at_freeze": 0,
        "hidden_future_media_request_count_at_freeze": 0,
    }
