from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import inspect
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

import m56_3_lease_gated_generation_runner as runner
import m56_4_separate_formal_scorer as scorer
import m56_fair_comparison_preflight as preflight
from test_m56_3_lease_gated_generation_runner import complete_mock_submission, mechanics


ROOT = Path(__file__).resolve().parent


def outcome_artifacts(packet: dict) -> tuple[dict, dict]:
    outcomes = []
    for index, row in enumerate(packet["model_inputs"]):
        labels = row["model_input"]["candidate_behavior_labels"]
        prediction = datetime.fromisoformat(row["model_input"]["prediction_time"])
        actual = labels[index % len(labels)]
        outcomes.append({
            "sample_id": row["sample_id"],
            "actual_observed_behavior": actual,
            "acceptable_behavior_labels": [actual],
            "actual_observed_at": (prediction + timedelta(seconds=1)).isoformat(),
            "source_timestamp": (prediction + timedelta(seconds=2)).isoformat(),
            "annotation_confidence": 0.8,
        })
    key = {
        "schema": preflight.OUTCOME_KEY_SCHEMA,
        "version": "1.0.0",
        "status": "private_withheld_until_prediction_commitment",
        "data_kind": packet["data_kind"],
        "contract_hash": packet["contract_hash"],
        "dataset_hash": packet["dataset_hash"],
        "sample_count": len(outcomes),
        "outcomes": outcomes,
        "generation_process_access_allowed": False,
    }
    split = {
        "schema": "uruha_m56_blinded_split_report_v1",
        "data_kind": packet["data_kind"],
        "sample_count": packet["sample_count"],
        "prediction_packet_hash": scorer.digest(packet),
        "outcome_key_hash": scorer.digest(key),
        "outcome_key_exposed_to_generation": False,
        "future_leakage_violations": 0,
        "model_call_count": 0,
        "m56_result_created": False,
        "formal_target_claim": False,
    }
    split["report_hash"] = scorer.digest(split)
    return key, split


def bind_private_hashes(rows: dict, outcome_key: dict, split_report: dict) -> None:
    request = rows["request"]
    request["outcome_key_hash"] = scorer.digest(outcome_key)
    request["split_report_hash"] = scorer.digest(split_report)
    request.pop("activation_request_hash", None)
    request["activation_request_hash"] = scorer.digest(request)
    receipt = rows["receipt"]
    receipt["activation_request_hash"] = request["activation_request_hash"]
    receipt.pop("receipt_hash", None)
    receipt["receipt_hash"] = scorer.digest(receipt)
    lease = rows["lease"]
    lease["activation_request_hash"] = request["activation_request_hash"]
    lease["consumed_receipt_hash"] = receipt["receipt_hash"]
    lease.pop("lease_hash", None)
    lease["lease_hash"] = scorer.digest(lease)


def call_from_row(phase: str, step_id: str, row: dict) -> dict:
    return {
        "schema": runner.CALL_SCHEMA,
        "phase": phase,
        "step_id": step_id,
        "prompt_hash": row["prompt_hash"],
        "raw_response_hash": row["raw_response_hash"],
        "prompt_tokens": row["prompt_tokens"],
        "completion_tokens": row["completion_tokens"],
        "latency_seconds": row["latency_seconds"],
        "process_cpu_seconds": row["process_cpu_seconds"],
        "process_peak_rss_bytes": row["process_peak_rss_bytes"],
        "ollama_rss_bytes": row["ollama_rss_bytes"],
        "total_duration_ns": row["total_duration_ns"],
        "load_duration_ns": row["load_duration_ns"],
        "prompt_eval_duration_ns": row["prompt_eval_duration_ns"],
        "eval_duration_ns": row["eval_duration_ns"],
        "model_reported": row["model_name"],
        "transport_attempt_count": row["transport_attempt_count"],
        "retry_count": row["retry_count"],
        "fallback_count": row["fallback_count"],
    }


def build_ledger(rows: dict) -> dict:
    submission = rows["submission"]
    schedule = rows["schedule"]
    summary_by_id = {row["summary_task_id"]: row for row in submission["summary_artifacts"]}
    prediction_by_id = {row["task_id"]: row for row in submission["prediction_rows"]}
    calls = []
    for step in schedule["summary_steps"]:
        if step["model_call_required"]:
            calls.append(call_from_row("b4_summary", step["step_id"], summary_by_id[step["step_id"]]))
    for step in schedule["prediction_steps"]:
        if step["model_call_required"]:
            calls.append(call_from_row("prediction", step["step_id"], prediction_by_id[step["step_id"]]))
    value = {
        "schema": "uruha_m56_formal_call_ledger_v1",
        "version": "1.0.0",
        "status": "complete_before_prediction_commitment",
        "lease_hash": rows["lease"]["lease_hash"],
        "schedule_hash": schedule["schedule_hash"],
        "call_count": len(calls),
        "required_call_count": schedule["required_model_call_count"],
        "calls": calls,
        "equation_artifact_rematerialization_cpu_seconds": submission["equation_artifact_rematerialization_cpu_seconds"],
        "retry_count": 0,
        "fallback_count": 0,
        "generation_target_outcome_access_count": 0,
    }
    value["ledger_hash"] = scorer.digest(value)
    return value


def complete_rows(run_id: str = "forged-scorer-no-human") -> tuple[dict, dict, dict]:
    rows = mechanics(run_id)
    outcome_key, split_report = outcome_artifacts(rows["packet"])
    bind_private_hashes(rows, outcome_key, split_report)
    schedule, submission, validation = complete_mock_submission(rows)
    commitment = runner.build_prediction_commitment(submission, schedule, rows["lease"], validation)
    release = runner.build_scoring_release(commitment, submission, schedule, rows["lease"], validation)
    rows.update({
        "schedule": schedule,
        "submission": submission,
        "commitment": commitment,
        "release": release,
    })
    rows["call_ledger"] = build_ledger(rows)
    return rows, outcome_key, split_report


def rebuild_after_submission_change(rows: dict) -> None:
    submission = rows["submission"]
    submission.pop("submission_hash", None)
    submission["submission_hash"] = scorer.digest(submission)
    validation = runner.validate_formal_submission(
        submission, rows["schedule"], rows["packet"], rows["manifest"],
        rows["capsule"], rows["bundle"], rows["lease"],
    )
    if not validation["valid"]:
        raise AssertionError(validation["errors"])
    rows["commitment"] = runner.build_prediction_commitment(
        submission, rows["schedule"], rows["lease"], validation
    )
    rows["release"] = runner.build_scoring_release(
        rows["commitment"], submission, rows["schedule"], rows["lease"], validation
    )
    rows["call_ledger"] = build_ledger(rows)


def write_private_run(root: Path, run_id: str, rows: dict, outcome_key: dict, split_report: dict) -> Path:
    run_root = root / run_id
    for name in ("generation", "commitments", "scoring", "telemetry"):
        (run_root / name).mkdir(parents=True, exist_ok=True)
    files = {
        "commitments/activation_request.json": rows["request"],
        f"commitments/{runner.activation_m56.FORMAL_RECEIPT_FILENAME}": rows["receipt"],
        f"commitments/{runner.activation_m56.FORMAL_LEASE_FILENAME}": rows["lease"],
        f"commitments/{runner.COMMITMENT_FILENAME}": rows["commitment"],
        f"commitments/{runner.SCORING_RELEASE_FILENAME}": rows["release"],
        "generation/prediction_packet.json": rows["packet"],
        "generation/run_manifest.json": rows["manifest"],
        "generation/execution_capsule.json": rows["capsule"],
        "generation/equation_artifacts.json": rows["bundle"],
        "generation/runtime_snapshot.json": rows["snapshot"],
        f"generation/{runner.SCHEDULE_FILENAME}": rows["schedule"],
        f"generation/{runner.SUBMISSION_FILENAME}": rows["submission"],
        f"telemetry/{runner.CALL_LEDGER_FILENAME}": rows["call_ledger"],
        "scoring/private_outcome_key.json": outcome_key,
        "scoring/split_report.json": split_report,
    }
    for relative, value in files.items():
        (run_root / relative).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return run_root


class M564SeparateFormalScorerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.outcome_key, cls.split_report = complete_rows()

    def test_contract_and_frozen_bindings_validate(self):
        report = scorer.validate_contract()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["binding_count"], 7)

    def test_public_execution_accepts_only_run_id(self):
        signature = inspect.signature(scorer.execute_formal_scoring)
        self.assertEqual(list(signature.parameters), ["run_id"])

    def test_current_live_state_is_denied_and_zero(self):
        audit = scorer.build_live_audit()
        self.assertEqual(audit["status"], "formal_scoring_denied_waiting_for_human_chain")
        self.assertEqual(audit["counts"]["v7_slots_by_ledger"], [0, 0])
        self.assertFalse(audit["formal_scoring_authorized"])
        self.assertEqual(audit["scorer_target_outcome_access_count"], 0)
        self.assertFalse(audit["formal_result_commitment_created"])

    def test_missing_live_run_fails_without_creating_directory(self):
        with TemporaryDirectory() as temp:
            private = Path(temp) / "private"
            run_id = "must-not-exist-before-human-gate"
            with mock.patch.object(scorer, "PRIVATE_ROOT", private):
                with self.assertRaises(FileNotFoundError):
                    scorer.execute_formal_scoring(run_id)
            self.assertFalse((private / run_id).exists())

    def test_prescore_revalidates_full_210_rows_release_and_call_ledger_without_outcome(self):
        report = scorer.validate_prescore_inputs("forged-scorer-no-human", self.rows)
        self.assertTrue(report["valid"], report["errors"])
        self.assertTrue(report["scoring_ready"], report["blockers"])
        self.assertEqual(report["prediction_row_count"], 210)
        self.assertEqual(report["model_call_count"], 180)
        self.assertEqual(report["generation_target_outcome_access_count"], 0)

    def test_token_imbalance_blocks_before_outcome_and_has_no_boolean_bypass(self):
        rows, outcome_key, split_report = complete_rows("token-block")
        ours = next(row for row in rows["submission"]["prediction_rows"] if row["condition_id"] == scorer.PRIMARY_SYSTEM)
        ours["prompt_tokens"] = 400
        rebuild_after_submission_change(rows)
        report = scorer.validate_prescore_inputs("token-block", rows)
        self.assertTrue(report["valid"], report["errors"])
        self.assertFalse(report["scoring_ready"])
        self.assertTrue(report["exact_token_sensitivity_required"])
        with TemporaryDirectory() as temp:
            private = Path(temp) / "private"
            write_private_run(private, "token-block", rows, outcome_key, split_report)
            with mock.patch.object(scorer, "PRIVATE_ROOT", private), mock.patch.object(
                scorer, "load_outcome_inputs", side_effect=AssertionError("outcome must remain unopened")
            ):
                result = scorer.execute_formal_scoring("token-block")
        self.assertEqual(result["status"], "formal_scoring_blocked_before_outcome_access")
        self.assertEqual(result["scorer_target_outcome_access_count"], 0)

    def test_outcome_key_and_temporal_order_validate_only_after_prescore(self):
        report = scorer.validate_outcome_inputs(
            self.outcome_key, self.split_report, self.rows["packet"], self.rows["request"]
        )
        self.assertTrue(report["valid"], report["errors"])
        changed = deepcopy(self.outcome_key)
        changed["outcomes"][0]["actual_observed_at"] = self.rows["packet"]["model_inputs"][0]["model_input"]["prediction_time"]
        self.assertFalse(scorer.validate_outcome_inputs(
            changed, self.split_report, self.rows["packet"], self.rows["request"]
        )["valid"])
        changed_split = deepcopy(self.split_report)
        changed_split["model_call_count"] = 1
        changed_split["report_hash"] = scorer.digest({
            key: value for key, value in changed_split.items() if key != "report_hash"
        })
        self.assertFalse(scorer.validate_outcome_inputs(
            self.outcome_key, changed_split, self.rows["packet"], self.rows["request"]
        )["valid"])
        changed = deepcopy(self.outcome_key)
        changed["source_text"] = "forbidden extra field"
        self.assertFalse(scorer.validate_outcome_inputs(
            changed, self.split_report, self.rows["packet"], self.rows["request"]
        )["valid"])

    def test_mutated_release_commitment_submission_or_ledger_fails_closed(self):
        for name, mutate in (
            ("release", lambda rows: rows["release"].__setitem__("release_hash", "0" * 64)),
            ("commitment", lambda rows: rows["commitment"].__setitem__("commitment_hash", "0" * 64)),
            ("submission", lambda rows: rows["submission"]["prediction_rows"][0].__setitem__("brief_evidence", "mutated")),
            ("ledger", lambda rows: rows["call_ledger"]["calls"][0].__setitem__("prompt_tokens", 999)),
        ):
            with self.subTest(name=name):
                rows = deepcopy(self.rows)
                mutate(rows)
                self.assertFalse(scorer.validate_prescore_inputs("forged-scorer-no-human", rows)["valid"])

    def test_call_ledger_accounts_for_a_nonempty_b4_summary_before_predictions(self):
        rows = deepcopy(self.rows)
        summary = rows["submission"]["summary_artifacts"][0]
        source = next(row for row in rows["submission"]["prediction_rows"] if row["condition_id"] != "B0_PRIOR")
        summary["summary_text"] = "Test-only nonempty pre-cutoff history summary."
        summary["model_call_count"] = 1
        for name in scorer._RESOURCE_FIELDS:
            summary[name] = source[name]
        summary["model_name"] = source["model_name"]
        summary["model_artifact_digest"] = source["model_artifact_digest"]
        summary["hardware_fingerprint"] = source["hardware_fingerprint"]
        summary["provider_options"] = deepcopy(source["provider_options"])
        summary["summary_artifact_hash"] = scorer.digest({
            key: value for key, value in summary.items() if key != "summary_artifact_hash"
        })
        rows["schedule"]["summary_steps"][0]["model_call_required"] = True
        rows["schedule"]["required_model_call_count"] += 1
        rows["schedule"].pop("schedule_hash")
        rows["schedule"]["schedule_hash"] = scorer.digest(rows["schedule"])
        rows["commitment"]["model_call_count"] += 1
        rows["call_ledger"] = build_ledger(rows)
        report = scorer.validate_call_ledger(
            rows["call_ledger"], rows["schedule"], rows["submission"], rows["commitment"], rows["lease"]
        )
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["call_count"], 181)
        self.assertEqual(rows["call_ledger"]["calls"][0]["phase"], "b4_summary")

    def test_private_score_reports_all_conditions_and_frozen_primary(self):
        prescore = scorer.validate_prescore_inputs("forged-scorer-no-human", self.rows)
        audit = scorer.build_prescore_audit("forged-scorer-no-human", self.rows, prescore)
        access = scorer.build_scoring_access_receipt("forged-scorer-no-human", self.rows, audit)
        report = scorer.build_score_report(
            "forged-scorer-no-human", self.rows, prescore, access, self.outcome_key, self.split_report
        )
        validation = scorer.validate_score_report(report)
        self.assertTrue(validation["valid"], validation["errors"])
        self.assertEqual(set(report["condition_metrics"]), set(scorer.CONDITION_IDS))
        self.assertEqual(report["primary_comparison"]["control"], scorer.PRIMARY_CONTROL)
        self.assertEqual(report["primary_comparison"]["system"], scorer.PRIMARY_SYSTEM)
        self.assertIn(report["decision"], ("formal_gate_pass", "formal_gate_fail_retained"))
        self.assertFalse(report["broad_human_equation_claim_authorized"])

    def test_metrics_match_preexisting_frozen_scorer_mechanics(self):
        prescore = scorer.validate_prescore_inputs("forged-scorer-no-human", self.rows)
        audit = scorer.build_prescore_audit("forged-scorer-no-human", self.rows, prescore)
        access = scorer.build_scoring_access_receipt("forged-scorer-no-human", self.rows, audit)
        report = scorer.build_score_report(
            "forged-scorer-no-human", self.rows, prescore, access, self.outcome_key, self.split_report
        )
        outcomes = {row["sample_id"]: row for row in self.outcome_key["outcomes"]}
        joined = [{
            "sample_id": row["sample_id"],
            "condition_id": row["condition_id"],
            "probabilities": row["probabilities"],
            "actual_observed_behavior": outcomes[row["sample_id"]]["actual_observed_behavior"],
            "acceptable_behavior_labels": outcomes[row["sample_id"]]["acceptable_behavior_labels"],
        } for row in self.rows["submission"]["prediction_rows"]]
        expected = scorer.capsule_m56._paired_primary(joined, scorer.capsule_m56.load_contract())
        self.assertEqual(report["primary_comparison"], expected)

    def test_report_excludes_raw_source_reasoning_and_excess_authority(self):
        prescore = scorer.validate_prescore_inputs("forged-scorer-no-human", self.rows)
        audit = scorer.build_prescore_audit("forged-scorer-no-human", self.rows, prescore)
        access = scorer.build_scoring_access_receipt("forged-scorer-no-human", self.rows, audit)
        report = scorer.build_score_report(
            "forged-scorer-no-human", self.rows, prescore, access, self.outcome_key, self.split_report
        )
        encoded = scorer.canonical(report)
        for token in ("raw_response_text", "reasoning_trace", "completed_event_summary", "observable_input_paraphrase"):
            self.assertNotIn(token, encoded)
        self.assertEqual(report["scorer_model_call_count"], 0)
        self.assertFalse(report["production_memory_write_authorized"])
        changed = deepcopy(report)
        changed["extra_conclusion"] = "caller supplied"
        changed["score_report_hash"] = scorer.digest({key: value for key, value in changed.items() if key != "score_report_hash"})
        self.assertFalse(scorer.validate_score_report(changed)["valid"])

    def test_result_commitment_binds_report_and_retains_negative_or_positive_decision(self):
        prescore = scorer.validate_prescore_inputs("forged-scorer-no-human", self.rows)
        audit = scorer.build_prescore_audit("forged-scorer-no-human", self.rows, prescore)
        access = scorer.build_scoring_access_receipt("forged-scorer-no-human", self.rows, audit)
        report = scorer.build_score_report(
            "forged-scorer-no-human", self.rows, prescore, access, self.outcome_key, self.split_report
        )
        commitment = scorer.build_result_commitment(report)
        self.assertTrue(scorer.validate_result_commitment(commitment, report)["valid"])
        changed = deepcopy(report)
        changed["decision"] = "formal_gate_pass" if report["decision"] != "formal_gate_pass" else "formal_gate_fail_retained"
        changed["score_report_hash"] = scorer.digest({key: value for key, value in changed.items() if key != "score_report_hash"})
        self.assertFalse(scorer.validate_result_commitment(commitment, changed)["valid"])

    def test_full_isolated_file_mechanics_are_idempotent_and_immutable(self):
        rows, outcome_key, split_report = complete_rows("isolated-score")
        with TemporaryDirectory() as temp:
            private = Path(temp) / "private"
            run_root = write_private_run(private, "isolated-score", rows, outcome_key, split_report)
            with mock.patch.object(scorer, "PRIVATE_ROOT", private):
                first = scorer.execute_formal_scoring("isolated-score")
                second = scorer.execute_formal_scoring("isolated-score")
                self.assertEqual(first["result_commitment_hash"], second["result_commitment_hash"])
                self.assertEqual(second["score_report_write"], "validated_existing_identical")
                path = run_root / "scoring" / scorer.SCORE_REPORT_FILENAME
                changed = json.loads(path.read_text(encoding="utf-8"))
                changed["decision"] = "tampered"
                path.write_text(json.dumps(changed), encoding="utf-8")
                with self.assertRaises(ValueError):
                    scorer.execute_formal_scoring("isolated-score")
        self.assertTrue(first["formal_result_created"])
        self.assertEqual(first["scorer_model_call_count"], 0)

    def test_synthetic_rehearsal_is_distinct_and_cannot_authorize(self):
        rehearsal = scorer.build_synthetic_rehearsal()
        self.assertEqual(rehearsal["schema"], scorer.REHEARSAL_SCHEMA)
        self.assertEqual(rehearsal["human_evidence_count"], 0)
        self.assertEqual(rehearsal["target_outcome_access_count"], 0)
        self.assertFalse(rehearsal["formal_result_created"])

    def test_dashboard_is_graphical_read_only_and_explicitly_denied(self):
        page = scorer.render_dashboard()
        self.assertIn("M56.4 FORMAL SCORING · DENIED NOW", page)
        self.assertIn("資源 gate 在答案之前", page)
        self.assertIn("B5 vs Ours", page)
        self.assertIn("0/18 + 0/18", page)
        self.assertNotIn("<form", page)
        self.assertNotIn("overflow-x", page)

    def test_implementation_freeze_matches(self):
        freeze = scorer.load_json(
            ROOT / "research/m56_4_separate_formal_scorer_implementation_freeze_2026-09-02.json"
        )
        self.assertEqual(
            freeze["schema"],
            "uruha_m56_separate_formal_scorer_implementation_freeze_v1",
        )
        for row in freeze["files"]:
            self.assertEqual(scorer.sha256_file(ROOT / row["path"]), row["sha256"])


if __name__ == "__main__":
    unittest.main()
