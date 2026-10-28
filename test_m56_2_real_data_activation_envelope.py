from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import inspect
from pathlib import Path
import tempfile
import unittest

import m55_temporal_row_contract as temporal_m55
import m56_2_real_data_activation_envelope as activation
import m56_fair_comparison_preflight as preflight
import m56_pre_outcome_equation_artifacts as artifacts


ROOT = Path(__file__).resolve().parent


def forged_real_packet() -> dict:
    """A structurally real-looking in-memory packet with no human provenance."""

    demo, _, _ = artifacts.build_demo_packet()
    base = deepcopy(demo["model_inputs"][0]["model_input"])
    rows = []
    for index in range(30):
        model_input = deepcopy(base)
        sample_id = f"forged-no-human-evidence-{index + 1:02d}"
        model_input["sample_id"] = sample_id
        model_input["prediction_time"] = f"2026-01-{index + 1:02d}T00:00:10+00:00"
        model_input["available_history_cutoff"] = model_input["prediction_time"]
        rows.append(
            {
                "sample_id": sample_id,
                "condition_order": preflight._condition_order(sample_id, preflight.load_contract()),
                "model_input": model_input,
                "model_input_hash": preflight.digest(model_input),
            }
        )
    packet = {
        "schema": preflight.PREDICTION_PACKET_SCHEMA,
        "version": "1.0.0",
        "status": "private_real_blinded_packet_pending_formal_run",
        "data_kind": temporal_m55.REAL_KIND,
        "contract_hash": preflight.validate_contract()["contract_hash"],
        "dataset_hash": "d" * 64,
        "sample_count": 30,
        "conditions": list(preflight.CONDITION_IDS),
        "model_inputs": rows,
        "data_boundary": {
            "outcome_key_available_to_generation": False,
            "post_cutoff_evidence_available": False,
            "private_mental_fact_available": False,
            "raw_or_verbatim_content_available": False,
        },
    }
    assert preflight.validate_prediction_packet(packet)["valid"]
    return packet


def fake_request() -> dict:
    request = {
        "activation_request_hash": "a" * 64,
        "runtime_snapshot_hash": "b" * 64,
        "equation_artifact_bundle_hash": "c" * 64,
    }
    return request


def fake_receipt(request: dict, *, now: datetime) -> dict:
    receipt = {
        "schema": activation.RECEIPT_SCHEMA,
        "version": "1.0.0",
        "status": "issued_unconsumed",
        "run_id": "forged-run",
        "activation_request_hash": request["activation_request_hash"],
        "runtime_snapshot_hash": request["runtime_snapshot_hash"],
        "equation_artifact_bundle_hash": request["equation_artifact_bundle_hash"],
        "execution_nonce": "0" * 48,
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(seconds=1800)).isoformat(),
        "consumed_at": None,
        "formal_generation_authorized": True,
        "formal_scoring_authorized": False,
        "formal_result_claim_authorized": False,
        "production_memory_write_authorized": False,
        "external_deployment_authorized": False,
        "retry_or_fallback_authorized": False,
        "generation_target_outcome_access_count": 0,
    }
    receipt["receipt_hash"] = activation.digest(receipt)
    return receipt


class M562RealDataActivationTests(unittest.TestCase):
    def test_contract_and_all_frozen_dependencies_validate(self):
        report = activation.validate_contract()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["binding_count"], 10)

    def test_public_live_audit_has_no_caller_readiness_injection(self):
        signature = inspect.signature(activation.build_live_activation_audit)
        self.assertNotIn("readiness", signature.parameters)
        audit = activation.build_live_activation_audit()
        self.assertFalse(audit["caller_supplied_readiness_used"])

    def test_current_authoritative_state_is_denied_without_receipt_or_calls(self):
        audit = activation.build_live_activation_audit()
        self.assertEqual(audit["status"], "formal_activation_denied")
        self.assertFalse(audit["current_execution_authorized"])
        self.assertEqual(audit["counts"]["v7_slots_by_ledger"], [0, 0])
        self.assertEqual(audit["counts"]["v9_independently_reviewed_events"], 0)
        self.assertEqual(audit["counts"]["real_temporal_rows"], 0)
        self.assertEqual(audit["formal_model_calls"], 0)
        self.assertEqual(audit["generation_target_outcome_access_count"], 0)
        self.assertFalse(audit["formal_activation_receipt_created"])
        self.assertIn("two_distinct_v7_ledgers_complete", audit["blocking_gates"])

    def test_private_layout_is_gitignored_and_rejects_outside_or_shared_root(self):
        valid = activation.validate_private_layout(
            activation.DEFAULT_PRIVATE_ROOT / "future-run-001"
        )
        self.assertTrue(valid["valid"], valid["errors"])
        self.assertFalse(valid["layout"]["generation_can_read_outcome_key"])
        shared = activation.validate_private_layout(activation.DEFAULT_PRIVATE_ROOT)
        outside = activation.validate_private_layout(ROOT / "analysis/not-private-m56")
        self.assertFalse(shared["valid"])
        self.assertFalse(outside["valid"])

    def test_runtime_snapshot_binds_real_local_model_manifest_and_hardware(self):
        snapshot = activation.capture_runtime_snapshot()
        report = activation.validate_runtime_snapshot(snapshot, compare_live=True)
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(snapshot["model_name"], "qwen3.5:9b")
        self.assertEqual(
            snapshot["model_manifest_sha256"],
            "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7",
        )
        self.assertEqual(snapshot["model_calls"], 0)

    def test_synthetic_rehearsal_uses_distinct_schema_and_never_authorizes(self):
        rehearsal = activation.build_synthetic_rehearsal()
        self.assertEqual(rehearsal["schema"], activation.REHEARSAL_SCHEMA)
        self.assertEqual(rehearsal["data_kind"], temporal_m55.SYNTHETIC_KIND)
        self.assertFalse(rehearsal["formal_execution_authorized"])
        self.assertFalse(rehearsal["formal_receipt_created"])
        self.assertEqual(rehearsal["model_calls"], 0)
        with self.assertRaises(PermissionError):
            activation.build_real_run_manifest(
                artifacts.build_demo_packet()[0], activation.capture_runtime_snapshot()
            )

    def test_forged_real_shaped_packet_can_build_pending_mechanics_but_not_live_authority(self):
        packet = forged_real_packet()
        snapshot = activation.capture_runtime_snapshot()
        manifest = activation.build_real_run_manifest(packet, snapshot)
        capsule = activation.build_formal_capsule(packet, manifest)
        capsule_report = activation.validate_formal_capsule(capsule, packet, manifest)
        self.assertTrue(capsule_report["valid"], capsule_report["errors"])
        self.assertEqual(capsule_report["task_count"], 210)
        bundle = activation.build_formal_artifact_bundle(packet, capsule, manifest)
        bundle_report = activation.validate_formal_artifact_bundle(
            bundle, packet, capsule, manifest
        )
        self.assertTrue(bundle_report["valid"], bundle_report["errors"])
        self.assertEqual(bundle_report["artifact_count"], 90)
        self.assertEqual(bundle_report["private_state_fabrication_count"], 0)
        self.assertFalse(capsule["formal_execution_authorized"])
        self.assertFalse(bundle["authorization"]["formal_model_execution"])
        audit = activation.build_live_activation_audit(compiled_temporal_result={})
        self.assertFalse(audit["current_execution_authorized"])

    def test_capsule_and_bundle_tampering_or_outcome_injection_fail_closed(self):
        packet = forged_real_packet()
        snapshot = activation.capture_runtime_snapshot()
        manifest = activation.build_real_run_manifest(packet, snapshot)
        capsule = activation.build_formal_capsule(packet, manifest)
        changed = deepcopy(capsule)
        changed["prediction_tasks"][0]["view"]["actual_observed_behavior"] = "ask_or_check"
        changed["capsule_hash"] = activation.digest(
            {key: value for key, value in changed.items() if key != "capsule_hash"}
        )
        report = activation.validate_formal_capsule(changed, packet, manifest)
        self.assertFalse(report["valid"])
        self.assertGreater(report["forbidden_key_count"], 0)
        bundle = activation.build_formal_artifact_bundle(packet, capsule, manifest)
        changed_bundle = deepcopy(bundle)
        changed_bundle["sample_artifacts"][0]["actual_observed_behavior"] = "ask_or_check"
        changed_bundle["artifact_bundle_hash"] = activation.digest(
            {key: value for key, value in changed_bundle.items() if key != "artifact_bundle_hash"}
        )
        bundle_report = activation.validate_formal_artifact_bundle(
            changed_bundle, packet, capsule, manifest
        )
        self.assertFalse(bundle_report["valid"])
        self.assertGreater(bundle_report["forbidden_key_count"], 0)

    def test_runtime_drift_and_dependency_tampering_fail_closed(self):
        snapshot = activation.capture_runtime_snapshot()
        snapshot["model_manifest_sha256"] = "0" * 64
        snapshot["runtime_snapshot_hash"] = activation.digest(
            {key: value for key, value in snapshot.items() if key != "runtime_snapshot_hash"}
        )
        self.assertFalse(activation.validate_runtime_snapshot(snapshot)["valid"])
        contract = activation.load_contract()
        contract["bindings"]["m56_capsule_freeze"]["sha256"] = "0" * 64
        self.assertFalse(activation.validate_contract(contract)["valid"])

    def test_prepare_real_activation_denies_before_writing_any_private_run(self):
        run_id = "must-not-exist-before-human-gate"
        run_root = activation.DEFAULT_PRIVATE_ROOT / run_id
        self.assertFalse(run_root.exists())
        with self.assertRaises(PermissionError):
            activation.prepare_real_activation({}, run_id=run_id)
        self.assertFalse(run_root.exists())

    def test_receipt_expiry_consumption_mutation_and_fake_hash_fail_closed(self):
        now = datetime(2026, 9, 2, 0, 0, tzinfo=timezone.utc)
        request = fake_request()
        receipt = fake_receipt(request, now=now)
        self.assertTrue(
            activation.validate_activation_receipt(receipt, request, now=now)["valid"]
        )
        expired = activation.validate_activation_receipt(
            receipt, request, now=now + timedelta(seconds=1801)
        )
        self.assertFalse(expired["valid"])
        consumed = deepcopy(receipt)
        consumed["status"] = "consumed"
        consumed["consumed_at"] = now.isoformat()
        consumed["receipt_hash"] = activation.digest(
            {key: value for key, value in consumed.items() if key != "receipt_hash"}
        )
        self.assertFalse(
            activation.validate_activation_receipt(consumed, request, now=now)["valid"]
        )
        tampered = deepcopy(receipt)
        tampered["formal_scoring_authorized"] = True
        tampered["receipt_hash"] = activation.digest(
            {key: value for key, value in tampered.items() if key != "receipt_hash"}
        )
        self.assertFalse(
            activation.validate_activation_receipt(tampered, request, now=now)["valid"]
        )

    def test_dashboard_is_graphical_read_only_and_shows_current_boundary(self):
        page = activation.render_dashboard()
        self.assertIn("M56 FORMAL RUN · DENIED NOW", page)
        self.assertIn("0/18 + 0/18", page)
        self.assertIn("0/30", page)
        self.assertIn("generation", page)
        self.assertIn("commitments", page)
        self.assertIn("scoring · PRIVATE", page)
        self.assertIn("telemetry", page)
        self.assertNotIn("<form", page)
        self.assertNotIn("overflow-x", page)

    def test_implementation_freeze_matches(self):
        freeze_path = ROOT / "research/m56_2_real_data_activation_envelope_implementation_freeze_2026-09-02.json"
        freeze = activation.load_json(freeze_path)
        self.assertEqual(
            freeze["schema"],
            "uruha_m56_real_data_activation_envelope_implementation_freeze_v1",
        )
        for row in freeze["files"]:
            self.assertEqual(activation.sha256_file(ROOT / row["path"]), row["sha256"])


if __name__ == "__main__":
    unittest.main()
