from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

import m55_temporal_row_contract as temporal_m55
import m56_fair_comparison_preflight as preflight_m56
from test_m55_temporal_row_contract import synthetic_pack


def compiled_synthetic():
    return temporal_m55.compile_temporal_dataset_m55(synthetic_pack())


def test_contract_freezes_seven_conditions_b5_primary_control_and_no_current_authority():
    report = preflight_m56.validate_contract()
    assert report["valid"] is True
    assert report["errors"] == []
    assert report["binding_count"] == 11
    assert report["condition_count"] == 7
    assert report["primary_control"] == "B5_STRUCTURED_HISTORY"
    assert report["primary_system"] == "OURS_HYBRID"
    contract = preflight_m56.load_contract()
    assert [row["condition_id"] for row in contract["conditions"]] == list(
        preflight_m56.CONDITION_IDS
    )
    assert contract["primary_contrast"]["weaker_baseline_may_replace_control_after_results"] is False
    assert all(value is False for value in contract["authorization"].values())


def test_live_preflight_is_honestly_blocked_before_two_humans_and_runs_no_model():
    report = preflight_m56.build_preflight_report()
    assert report["status"] == "protocol_ready_execution_blocked"
    assert report["m55_pilot_complete"] is False
    assert report["m55_authorizes_m56"] is False
    assert report["current_execution_authorized"] is False
    assert report["blocking_gate"] == "complete_two_independent_v7_18_slot_ledgers"
    assert report["counts"]["v7_completed_slots_by_ledger"] == [0, 0]
    assert report["counts"]["v9_independently_reviewed_event_count"] == 0
    assert report["counts"]["temporally_valid_prediction_row_count"] == 0
    assert report["model_call_count"] == 0
    assert report["target_outcome_access_count"] == 0
    assert report["formal_m56_result_created"] is False


def test_synthetic_split_separates_prediction_packet_and_private_outcome_key():
    compiled = compiled_synthetic()
    artifacts = preflight_m56.build_blinded_artifacts(compiled)
    packet = artifacts["prediction_packet"]
    key = artifacts["outcome_key"]
    split = artifacts["split_report"]
    validation = preflight_m56.validate_prediction_packet(packet)
    assert validation["valid"] is True
    assert validation["forbidden_key_count"] == 0
    assert packet["sample_count"] == 2
    assert key["sample_count"] == 2
    assert split["prediction_packet_hash"] == preflight_m56.digest(packet)
    assert split["outcome_key_hash"] == preflight_m56.digest(key)
    assert split["outcome_key_exposed_to_generation"] is False
    assert split["future_leakage_violations"] == 0
    assert split["model_call_count"] == 0
    assert split["m56_result_created"] is False
    serialized_packet = json.dumps(packet, ensure_ascii=False)
    for forbidden in preflight_m56.FORBIDDEN_PACKET_KEYS:
        assert f'"{forbidden}"' not in serialized_packet
    assert "OUTCOME-SUMMARY-TWO" not in json.dumps(packet["model_inputs"][1], ensure_ascii=False)
    assert "OUTCOME-SUMMARY-TWO" not in json.dumps(key, ensure_ascii=False)


def test_packet_tampering_with_outcome_key_wrong_order_or_stale_hash_fails_closed():
    packet = preflight_m56.build_blinded_artifacts(compiled_synthetic())["prediction_packet"]
    leaked = deepcopy(packet)
    leaked["model_inputs"][0]["actual_observed_behavior"] = "ask_or_check"
    report = preflight_m56.validate_prediction_packet(leaked)
    assert report["valid"] is False
    assert any("forbidden_key" in error for error in report["errors"])
    wrong_order = deepcopy(packet)
    wrong_order["model_inputs"][0]["condition_order"].reverse()
    report = preflight_m56.validate_prediction_packet(wrong_order)
    assert report["valid"] is False
    assert any("condition_order" in error for error in report["errors"])
    stale = deepcopy(packet)
    stale["model_inputs"][0]["model_input"]["event_context"] += " changed"
    report = preflight_m56.validate_prediction_packet(stale)
    assert report["valid"] is False
    assert any("model_input_hash" in error for error in report["errors"])


def test_stale_compiled_dataset_and_real_shaped_data_without_m55_gate_cannot_split():
    compiled = compiled_synthetic()
    stale = deepcopy(compiled)
    stale["dataset"]["samples"][0]["event_context"] += " changed"
    with pytest.raises(ValueError, match="hash is missing or stale"):
        preflight_m56.build_blinded_artifacts(stale)
    real_shaped = deepcopy(compiled)
    real_shaped["audit"]["data_kind"] = temporal_m55.REAL_KIND
    with pytest.raises(PermissionError, match="completed M55"):
        preflight_m56.build_blinded_artifacts(
            real_shaped,
            readiness={"m55_pilot_complete": False, "m56_authorized": False},
        )
    with pytest.raises(PermissionError, match="completed M55"):
        preflight_m56.build_blinded_artifacts(
            real_shaped,
            readiness={"m55_pilot_complete": True, "m56_authorized": True},
        )


def test_synthetic_run_manifest_passes_without_execution_and_b0_is_declared_exception():
    packet = preflight_m56.build_blinded_artifacts(compiled_synthetic())["prediction_packet"]
    manifest = preflight_m56.build_fixture_run_manifest(packet)
    report = preflight_m56.validate_run_manifest(manifest, packet)
    assert report["valid"] is True
    assert report["errors"] == []
    assert report["condition_count"] == 7
    assert report["same_model_artifact"] is True
    assert report["same_hardware"] is True
    b0 = manifest["condition_runs"][0]
    assert b0["condition_id"] == "B0_PRIOR"
    assert b0["model_used"] is False
    assert b0["model_call_cap_per_sample"] == 0
    assert manifest["prediction_commitment_hash"] is None
    assert manifest["scoring_started"] is False
    assert manifest["model_call_count"] == 0


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("model_artifact_digest", "a" * 64, "same_model_artifact"),
        ("hardware_fingerprint", "different-hardware", "same_hardware"),
        ("provider_options", {"temperature": 1}, "provider_options"),
        ("input_token_budget", 4096, "input_token_budget"),
        ("output_token_budget", 128, "output_token_budget"),
        ("outcome_key_visible", True, "outcome_key_visible"),
        ("retry_count", 1, "retry_or_fallback"),
        ("fallback_count", 1, "retry_or_fallback"),
    ],
)
def test_run_manifest_rejects_model_hardware_budget_outcome_retry_and_fallback_mismatch(
    field, value, expected
):
    packet = preflight_m56.build_blinded_artifacts(compiled_synthetic())["prediction_packet"]
    manifest = preflight_m56.build_fixture_run_manifest(packet)
    manifest["condition_runs"][-1][field] = value
    report = preflight_m56.validate_run_manifest(manifest, packet)
    assert report["valid"] is False
    assert any(expected in error for error in report["errors"])


def test_run_manifest_rejects_sample_or_packet_change_and_synthetic_execution_claim():
    packet = preflight_m56.build_blinded_artifacts(compiled_synthetic())["prediction_packet"]
    manifest = preflight_m56.build_fixture_run_manifest(packet)
    wrong_samples = deepcopy(manifest)
    wrong_samples["condition_runs"][5]["source_sample_ids"] = ["wrong"]
    assert any(
        "source_sample_ids" in error
        for error in preflight_m56.validate_run_manifest(wrong_samples, packet)["errors"]
    )
    executed = deepcopy(manifest)
    executed["prediction_commitment_hash"] = "c" * 64
    executed["scoring_started"] = True
    executed["model_call_count"] = 1
    report = preflight_m56.validate_run_manifest(executed, packet)
    assert report["valid"] is False
    assert "manifest.synthetic_commitment_must_be_absent" in report["errors"]
    assert "manifest.synthetic_must_not_execute" in report["errors"]
    changed_packet = deepcopy(packet)
    changed_packet["status"] = "changed"
    report = preflight_m56.validate_run_manifest(manifest, changed_packet)
    assert report["valid"] is False
    assert "manifest.prediction_packet_hash" in report["errors"]


def test_graph_explains_visibility_blinding_fairness_decision_and_current_block():
    page = preflight_m56.render_preflight()
    for phrase in (
        "先把比較規則鎖死",
        "B5 vs Ours",
        "七組看到什麼",
        "Prediction packet",
        "SHA commitment",
        "同模型與硬體",
        "同 token 預算",
        "Brier 與 NLL",
        "0/18",
        "real rows 0/30",
        "M56 禁止",
        "complete_two_independent_v7_18_slot_ledgers",
    ):
        assert phrase in page
    assert "token=" not in page
    assert "OUTCOME-SUMMARY" not in page
    assert "precutoff synthetic" not in page


def test_implementation_freeze_matches_all_frozen_files():
    freeze_path = Path(
        "research/m56_fair_comparison_preflight_implementation_freeze_2026-09-01.json"
    )
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    assert freeze["status"] == "protocol_ready_execution_blocked"
    assert freeze["formal_model_calls_at_freeze"] == 0
    assert freeze["target_outcome_access_at_freeze"] == 0
    for relative_path, expected_sha256 in freeze["frozen_files"].items():
        actual_sha256 = hashlib.sha256(Path(relative_path).read_bytes()).hexdigest()
        assert actual_sha256 == expected_sha256
