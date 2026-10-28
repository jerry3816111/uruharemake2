from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import inspect
from pathlib import Path
import unittest

import m55_temporal_row_contract as temporal_m55
import m56_2_real_data_activation_envelope as activation
import m56_3_lease_gated_generation_runner as runner
import m56_blinded_execution_capsule as capsule_base
import m56_fair_comparison_preflight as preflight
import m56_pre_outcome_equation_artifacts as artifacts


ROOT = Path(__file__).resolve().parent


def forged_real_packet() -> dict:
    demo, _, _ = artifacts.build_demo_packet()
    base = deepcopy(demo["model_inputs"][0]["model_input"])
    rows = []
    for index in range(30):
        model_input = deepcopy(base)
        sample_id = f"forged-runner-no-human-{index + 1:02d}"
        model_input["sample_id"] = sample_id
        model_input["prediction_time"] = f"2026-01-{index + 1:02d}T00:00:10+00:00"
        model_input["available_history_cutoff"] = model_input["prediction_time"]
        rows.append({
            "sample_id": sample_id,
            "condition_order": preflight._condition_order(sample_id, preflight.load_contract()),
            "model_input": model_input,
            "model_input_hash": preflight.digest(model_input),
        })
    packet = {
        "schema": preflight.PREDICTION_PACKET_SCHEMA,
        "version": "1.0.0",
        "status": "private_real_blinded_packet_pending_formal_run",
        "data_kind": temporal_m55.REAL_KIND,
        "contract_hash": preflight.validate_contract()["contract_hash"],
        "dataset_hash": "e" * 64,
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


def mechanics(run_id: str = "forged-unleased-mechanics") -> dict:
    packet = forged_real_packet()
    snapshot = activation.capture_runtime_snapshot()
    manifest = activation.build_real_run_manifest(packet, snapshot)
    capsule = activation.build_formal_capsule(packet, manifest)
    bundle = activation.build_formal_artifact_bundle(packet, capsule, manifest)
    request_row = {
        "schema": activation.REQUEST_SCHEMA,
        "version": "1.0.0",
        "status": "private_real_activation_request_pending_receipt",
        "run_id": run_id,
        "contract_hash": activation.validate_contract()["contract_hash"],
        "dependency_set_hash": activation.build_live_activation_audit()["dependency_set_hash"],
        "dataset_hash": packet["dataset_hash"],
        "prediction_packet_hash": activation.digest(packet),
        "outcome_key_hash": "1" * 64,
        "split_report_hash": "2" * 64,
        "run_manifest_hash": activation.digest(manifest),
        "capsule_hash": capsule["capsule_hash"],
        "equation_artifact_bundle_hash": bundle["artifact_bundle_hash"],
        "runtime_snapshot_hash": snapshot["runtime_snapshot_hash"],
        "private_layout_hash": "3" * 64,
        "sample_count": 30,
        "condition_count": 7,
        "generation_target_outcome_access_count": 0,
        "model_calls_before_activation": 0,
        "formal_execution_authorized": False,
        "formal_scoring_authorized": False,
    }
    request_row["activation_request_hash"] = runner.digest(request_row)
    now = datetime(2026, 9, 2, 0, 0, tzinfo=timezone.utc)
    issued = {
        "schema": activation.RECEIPT_SCHEMA,
        "version": "1.0.0",
        "status": "issued_unconsumed",
        "run_id": run_id,
        "activation_request_hash": request_row["activation_request_hash"],
        "runtime_snapshot_hash": snapshot["runtime_snapshot_hash"],
        "equation_artifact_bundle_hash": bundle["artifact_bundle_hash"],
        "execution_nonce": "4" * 48,
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
    issued["receipt_hash"] = runner.digest(issued)
    receipt = deepcopy(issued)
    receipt["status"] = "consumed"
    receipt["consumed_at"] = now.isoformat()
    receipt.pop("receipt_hash")
    receipt["receipt_hash"] = runner.digest(receipt)
    lease = {
        "schema": activation.LEASE_SCHEMA,
        "version": "1.0.0",
        "status": "single_formal_generation_run_in_progress",
        "run_id": run_id,
        "consumed_receipt_hash": receipt["receipt_hash"],
        "activation_request_hash": request_row["activation_request_hash"],
        "execution_nonce_hash": sha256(receipt["execution_nonce"].encode("utf-8")).hexdigest(),
        "started_at": now.isoformat(),
        "formal_generation_authorized": True,
        "formal_scoring_authorized": False,
        "retry_or_fallback_authorized": False,
        "generation_target_outcome_access_count": 0,
    }
    lease["lease_hash"] = runner.digest(lease)
    return {
        "request": request_row,
        "receipt": receipt,
        "lease": lease,
        "packet": packet,
        "manifest": manifest,
        "capsule": capsule,
        "bundle": bundle,
        "snapshot": snapshot,
    }


def mock_call(labels: list[str], *, prompt_tokens: int = 128) -> dict:
    weights = {label: float(index + 1) for index, label in enumerate(labels)}
    total = sum(weights.values())
    return {
        "parsed": {
            "probabilities": {label: value / total for label, value in weights.items()},
            "authorized_evidence_ids": [],
            "brief_evidence": "No-call mechanics fixture; no human provenance.",
        },
        "prompt_hash": "5" * 64,
        "raw_response_hash": "6" * 64,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": 20,
        "latency_seconds": 0.01,
        "process_cpu_seconds": 0.001,
        "process_peak_rss_bytes": 1024,
        "ollama_rss_bytes": 2048,
        "total_duration_ns": 10,
        "load_duration_ns": 1,
        "prompt_eval_duration_ns": 4,
        "eval_duration_ns": 5,
        "transport_attempt_count": 1,
        "retry_count": 0,
        "fallback_count": 0,
    }


def complete_mock_submission(rows: dict) -> tuple[dict, dict, dict]:
    packet, manifest, capsule, bundle = rows["packet"], rows["manifest"], rows["capsule"], rows["bundle"]
    lease = rows["lease"]
    schedule = runner.build_generation_schedule(packet, manifest, capsule, bundle, lease["lease_hash"])
    run_map = {row["condition_id"]: row for row in manifest["condition_runs"]}
    summaries = [runner._empty_summary_artifact(task, rows["snapshot"]) for task in capsule["summary_tasks"]]
    summary_map = {row["summary_task_id"]: row for row in summaries}
    predictions = []
    for task in capsule["prediction_tasks"]:
        condition = task["condition_id"]
        run = run_map[condition]
        if condition == "B0_PRIOR":
            predictions.append(runner._deterministic_b0(task, run))
        else:
            predictions.append(runner._prediction_row(
                task, mock_call(task["view"]["candidate_behavior_labels"]), run, summary_map, bundle
            ))
    submission = runner.build_formal_submission(
        schedule, packet, manifest, capsule, bundle, lease, summaries, predictions, 0.001
    )
    validation = runner.validate_formal_submission(
        submission, schedule, packet, manifest, capsule, bundle, lease
    )
    return schedule, submission, validation


class M563LeaseGatedRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = mechanics()

    def test_contract_and_frozen_dependencies_validate(self):
        report = runner.validate_contract()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["binding_count"], 6)

    def test_public_execution_accepts_only_run_id(self):
        signature = inspect.signature(runner.execute_formal_generation)
        self.assertEqual(list(signature.parameters), ["run_id"])

    def test_current_live_state_denies_without_calls_commitment_or_release(self):
        audit = runner.build_live_audit()
        self.assertEqual(audit["status"], "formal_generation_denied_waiting_for_human_chain")
        self.assertEqual(audit["counts"]["v7_slots_by_ledger"], [0, 0])
        self.assertEqual(audit["counts"]["real_temporal_rows"], 0)
        self.assertFalse(audit["formal_generation_authorized"])
        self.assertEqual(audit["formal_model_calls"], 0)
        self.assertFalse(audit["formal_commitment_created"])
        self.assertFalse(audit["formal_scoring_release_created"])

    def test_missing_live_lease_fails_before_writing(self):
        run_id = "m56-3-must-not-exist-before-human-gate"
        root = runner.PRIVATE_ROOT / run_id
        self.assertFalse(root.exists())
        with self.assertRaises(FileNotFoundError):
            runner.execute_formal_generation(run_id)
        self.assertFalse(root.exists())

    def test_forged_in_memory_mechanics_validate_but_are_not_live_authority(self):
        report = runner.validate_runner_inputs("forged-unleased-mechanics", self.rows)
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["generation_target_outcome_access_count"], 0)
        audit = runner.build_live_audit()
        self.assertFalse(audit["formal_generation_authorized"])

    def test_schedule_is_exact_210_ordered_and_lease_bound(self):
        schedule = runner.build_generation_schedule(
            self.rows["packet"], self.rows["manifest"], self.rows["capsule"],
            self.rows["bundle"], self.rows["lease"]["lease_hash"],
        )
        report = runner.validate_generation_schedule(
            schedule, self.rows["packet"], self.rows["manifest"], self.rows["capsule"],
            self.rows["bundle"], self.rows["lease"]["lease_hash"],
        )
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["prediction_task_count"], 210)
        self.assertEqual(schedule["required_model_call_count"], 180)
        changed = deepcopy(schedule)
        changed["prediction_steps"][0], changed["prediction_steps"][1] = changed["prediction_steps"][1], changed["prediction_steps"][0]
        changed["schedule_hash"] = runner.digest({key: value for key, value in changed.items() if key != "schedule_hash"})
        self.assertFalse(runner.validate_generation_schedule(
            changed, self.rows["packet"], self.rows["manifest"], self.rows["capsule"],
            self.rows["bundle"], self.rows["lease"]["lease_hash"],
        )["valid"])

    def test_prompt_boundary_keeps_b5_free_of_equation_and_ours_bound(self):
        capsule = self.rows["capsule"]
        bundle = self.rows["bundle"]
        summary_map = {
            task["summary_task_id"]: runner._empty_summary_artifact(task, self.rows["snapshot"])
            for task in capsule["summary_tasks"]
        }
        b5 = next(row for row in capsule["prediction_tasks"] if row["condition_id"] == capsule_base.PRIMARY_CONTROL)
        ours = next(row for row in capsule["prediction_tasks"] if row["condition_id"] == capsule_base.PRIMARY_SYSTEM)
        b5_prompt = runner.build_prediction_prompt(b5, summary_map, bundle)["prompt"]
        ours_prompt = runner.build_prediction_prompt(ours, summary_map, bundle)["prompt"]
        self.assertNotIn("pre_outcome_equation_artifacts", b5_prompt)
        self.assertIn("pre_outcome_equation_artifacts", ours_prompt)
        self.assertNotIn("actual_observed_behavior", ours_prompt)

    def test_complete_submission_commitment_and_release_validate(self):
        schedule, submission, validation = complete_mock_submission(self.rows)
        self.assertTrue(validation["valid"], validation["errors"])
        self.assertEqual(validation["row_count"], 210)
        self.assertEqual(validation["model_call_count"], 180)
        commitment = runner.build_prediction_commitment(submission, schedule, self.rows["lease"], validation)
        self.assertTrue(runner.validate_prediction_commitment(
            commitment, submission, schedule, self.rows["lease"], validation
        )["valid"])
        release = runner.build_scoring_release(
            commitment, submission, schedule, self.rows["lease"], validation
        )
        release_report = runner.validate_scoring_release(
            release, commitment, submission, schedule, self.rows["lease"], validation
        )
        self.assertTrue(release_report["valid"], release_report["errors"])
        self.assertTrue(release["scoring_compartment_read_allowed_by_separate_scorer"])
        self.assertFalse(release["generation_target_outcome_access_allowed"])
        self.assertFalse(release["formal_result_claim_authorized"])

    def test_incomplete_retry_outcome_and_post_commit_mutation_fail_closed(self):
        schedule, submission, validation = complete_mock_submission(self.rows)
        commitment = runner.build_prediction_commitment(submission, schedule, self.rows["lease"], validation)
        release = runner.build_scoring_release(
            commitment, submission, schedule, self.rows["lease"], validation
        )
        incomplete = deepcopy(submission)
        incomplete["prediction_rows"].pop()
        incomplete["submission_hash"] = runner.digest({key: value for key, value in incomplete.items() if key != "submission_hash"})
        self.assertFalse(runner.validate_formal_submission(
            incomplete, schedule, self.rows["packet"], self.rows["manifest"],
            self.rows["capsule"], self.rows["bundle"], self.rows["lease"],
        )["valid"])
        retry = deepcopy(submission)
        retry["prediction_rows"][1]["retry_count"] = 1
        retry["submission_hash"] = runner.digest({key: value for key, value in retry.items() if key != "submission_hash"})
        self.assertFalse(runner.validate_formal_submission(
            retry, schedule, self.rows["packet"], self.rows["manifest"],
            self.rows["capsule"], self.rows["bundle"], self.rows["lease"],
        )["valid"])
        outcome = deepcopy(submission)
        outcome["actual_observed_behavior"] = "ask_or_check"
        outcome["submission_hash"] = runner.digest({key: value for key, value in outcome.items() if key != "submission_hash"})
        self.assertFalse(runner.validate_formal_submission(
            outcome, schedule, self.rows["packet"], self.rows["manifest"],
            self.rows["capsule"], self.rows["bundle"], self.rows["lease"],
        )["valid"])
        changed = deepcopy(submission)
        changed["prediction_rows"][0]["brief_evidence"] = "post-commit mutation"
        changed["submission_hash"] = runner.digest({key: value for key, value in changed.items() if key != "submission_hash"})
        changed_validation = runner.validate_formal_submission(
            changed, schedule, self.rows["packet"], self.rows["manifest"],
            self.rows["capsule"], self.rows["bundle"], self.rows["lease"],
        )
        self.assertFalse(runner.validate_scoring_release(
            release, commitment, changed, schedule, self.rows["lease"], changed_validation
        )["valid"])

    def test_lease_runtime_and_artifact_drift_fail_closed(self):
        changed = deepcopy(self.rows)
        changed["lease"]["retry_or_fallback_authorized"] = True
        changed["lease"]["lease_hash"] = runner.digest({key: value for key, value in changed["lease"].items() if key != "lease_hash"})
        self.assertFalse(runner.validate_runner_inputs("forged-unleased-mechanics", changed)["valid"])
        changed = deepcopy(self.rows)
        changed["snapshot"]["model_manifest_sha256"] = "0" * 64
        changed["snapshot"]["runtime_snapshot_hash"] = runner.digest({
            key: value for key, value in changed["snapshot"].items() if key != "runtime_snapshot_hash"
        })
        self.assertFalse(runner.validate_runner_inputs("forged-unleased-mechanics", changed)["valid"])
        changed = deepcopy(self.rows)
        changed["bundle"]["sample_artifacts"][0]["fit_artifact"]["fit_artifact_hash"] = "0" * 64
        changed["bundle"]["artifact_bundle_hash"] = runner.digest({
            key: value for key, value in changed["bundle"].items() if key != "artifact_bundle_hash"
        })
        self.assertFalse(runner.validate_runner_inputs("forged-unleased-mechanics", changed)["valid"])

    def test_malformed_probability_token_overflow_and_retry_resources_fail(self):
        labels = self.rows["capsule"]["prediction_tasks"][0]["view"]["candidate_behavior_labels"]
        parsed = mock_call(labels)["parsed"]
        parsed["probabilities"][labels[0]] += 0.1
        with self.assertRaises(ValueError):
            runner._validate_prediction_output(parsed, labels, set())
        call = mock_call(labels, prompt_tokens=8193)
        errors = runner._validate_call_resources(call, input_budget=8192, output_budget=384)
        self.assertIn("resource.input_token_budget", errors)
        call = mock_call(labels)
        call["retry_count"] = 1
        self.assertIn("resource.retry_or_fallback", runner._validate_call_resources(
            call, input_budget=8192, output_budget=384
        ))
        with self.assertRaises(ValueError):
            runner._validate_model_identity({"model_reported": "different:model"}, "qwen3.5:9b")

    def test_synthetic_rehearsal_is_distinct_and_never_authorizes(self):
        rehearsal = runner.build_synthetic_rehearsal()
        self.assertEqual(rehearsal["schema"], runner.REHEARSAL_SCHEMA)
        self.assertEqual(rehearsal["model_calls"], 0)
        self.assertFalse(rehearsal["formal_lease_created"])
        self.assertFalse(rehearsal["formal_execution_authorized"])
        self.assertEqual(rehearsal["human_evidence_count"], 0)

    def test_dashboard_is_graphical_read_only_and_explicitly_denied(self):
        page = runner.render_dashboard()
        self.assertIn("M56.3 FORMAL GENERATION · DENIED NOW", page)
        self.assertIn("不能跳步的狀態機", page)
        self.assertIn("GENERATION", page)
        self.assertIn("SCORING · PRIVATE", page)
        self.assertIn("0/18 + 0/18", page)
        self.assertNotIn("<form", page)
        self.assertNotIn("overflow-x", page)

    def test_implementation_freeze_matches(self):
        freeze = runner.load_json(
            ROOT / "research/m56_3_lease_gated_generation_runner_implementation_freeze_2026-09-02.json"
        )
        self.assertEqual(
            freeze["schema"],
            "uruha_m56_lease_gated_generation_runner_implementation_freeze_v1",
        )
        for row in freeze["files"]:
            self.assertEqual(runner.sha256_file(ROOT / row["path"]), row["sha256"])


if __name__ == "__main__":
    unittest.main()
