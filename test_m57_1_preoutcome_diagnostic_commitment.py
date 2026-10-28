from __future__ import annotations

import inspect
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest
from unittest import mock

import m56_4_separate_formal_scorer as scorer
import m56_7_mac_full_sync_generation as durable
import m56_10_crash_safe_outcome_join as crash_safe
import m57_component_error_localization as localization
import m57_1_preoutcome_diagnostic_commitment as commitment
from test_m56_9_single_writer_formal_scoring import materialize_scoring_run
from test_m56_10_crash_safe_outcome_join import m5610_private_roots


class M571PreOutcomeDiagnosticCommitmentTests(unittest.TestCase):
    def test_contract_and_public_api_are_frozen_and_injection_free(self):
        report = commitment.validate_contract()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["binding_count"], 6)
        self.assertEqual(
            list(inspect.signature(commitment.commit_m57_preoutcome_diagnostic_mode).parameters),
            ["run_id"],
        )
        self.assertEqual(
            list(inspect.signature(commitment.validate_m57_preoutcome_diagnostic_mode).parameters),
            ["run_id"],
        )

    def test_live_state_remains_denied_and_zero(self):
        audit = commitment.build_live_audit()
        self.assertTrue(audit["contract_valid"])
        self.assertEqual(audit["counts"]["v7_slots_by_ledger"], [0, 0])
        self.assertEqual(audit["counts"]["real_temporal_rows"], 0)
        self.assertFalse(audit["live_m57_1_commitment_created"])
        self.assertFalse(audit["live_m56_result_created"])
        self.assertFalse(audit["formal_m57_execution_authorized"])
        self.assertEqual(audit["target_outcome_access_count"], 0)
        self.assertEqual(audit["formal_model_call_count"], 0)

    def test_first_commit_is_before_outcome_state_and_binds_exact_artifacts(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m571-first-preoutcome-commit"
            with m5610_private_roots(root):
                run_root = materialize_scoring_run(root, run_id)
                result = commitment.commit_m57_preoutcome_diagnostic_mode(run_id)
                mode = commitment.load_json(
                    run_root / "commitments" / commitment.MODE_FILENAME
                )
                authorization = commitment.gated_m56.validate_durable_scoring_authorization(run_id)
                validation = commitment.validate_mode_value(mode, run_id, authorization)
            self.assertEqual(result["status"], "preoutcome_diagnostic_mode_committed_full_sync")
            self.assertEqual(result["outcome_state_artifacts_now"], [])
            self.assertEqual(result["target_outcome_access_count"], 0)
            self.assertTrue(validation["valid"], validation["errors"])
            self.assertEqual(tuple(mode["stage_plans"]), localization.STAGE_IDS)
            self.assertEqual(
                mode["substitution_plan_commitment_hash"],
                localization.digest(mode["stage_plans"]),
            )
            self.assertEqual(mode["sample_count"], 30)
            self.assertEqual(mode["condition_count"], 7)
            self.assertFalse(mode["component_substitution_predictions_created"])
            self.assertFalse(mode["formal_m57_result_created"])

    def test_identical_commitment_replays_before_and_after_m56_result(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m571-post-result-revalidation"
            with m5610_private_roots(root):
                materialize_scoring_run(root, run_id)
                first = commitment.commit_m57_preoutcome_diagnostic_mode(run_id)
                second = commitment.commit_m57_preoutcome_diagnostic_mode(run_id)
                crash_safe.execute_crash_safe_outcome_join_formal_scoring(run_id)
                validation = commitment.validate_m57_preoutcome_diagnostic_mode(run_id)
                third = commitment.commit_m57_preoutcome_diagnostic_mode(run_id)
            self.assertEqual(first["mode_commitment_hash"], second["mode_commitment_hash"])
            self.assertEqual(first["mode_commitment_hash"], third["mode_commitment_hash"])
            self.assertTrue(validation["m56_result_present"])
            self.assertTrue(validation["m56_result_link_valid"], validation["m56_result_link_errors"])
            self.assertFalse(validation["formal_m57_execution_authorized"])
            self.assertFalse(validation["formal_m57_result_created"])

    def test_first_commit_after_m56_result_is_rejected_without_another_outcome_load(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m571-retroactive-denied"
            with m5610_private_roots(root):
                run_root = materialize_scoring_run(root, run_id)
                crash_safe.execute_crash_safe_outcome_join_formal_scoring(run_id)
                original_load = scorer.load_outcome_inputs
                with mock.patch.object(scorer, "load_outcome_inputs", wraps=original_load) as loader:
                    with self.assertRaisesRegex(PermissionError, "retroactively"):
                        commitment.commit_m57_preoutcome_diagnostic_mode(run_id)
                    self.assertEqual(loader.call_count, 0)
            self.assertFalse((run_root / "commitments" / commitment.MODE_FILENAME).exists())

    def test_first_commit_after_any_outcome_start_marker_is_rejected(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m571-outcome-marker-denied"
            with m5610_private_roots(root):
                run_root = materialize_scoring_run(root, run_id)
                marker = run_root / "telemetry" / crash_safe.MODE_FILENAME
                marker.write_text("{}", encoding="utf-8")
                with self.assertRaisesRegex(PermissionError, "outcome state"):
                    commitment.commit_m57_preoutcome_diagnostic_mode(run_id)

    def test_mutated_commitment_and_upstream_inputs_fail_closed(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m571-mutation-denied"
            with m5610_private_roots(root):
                run_root = materialize_scoring_run(root, run_id)
                commitment.commit_m57_preoutcome_diagnostic_mode(run_id)
                path = run_root / "commitments" / commitment.MODE_FILENAME
                mode = json.loads(path.read_text(encoding="utf-8"))
                mode["prediction_commitment_hash"] = "0" * 64
                path.write_text(json.dumps(mode), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "commitment invalid"):
                    commitment.validate_m57_preoutcome_diagnostic_mode(run_id)

    def test_dependency_drift_and_missing_run_fail_closed(self):
        contract = commitment.load_contract()
        contract["frozen_dependencies"]["m57_component_error_localization.py"] = "0" * 64
        report = commitment.validate_contract(contract)
        self.assertFalse(report["valid"])
        self.assertIn("dependency:m57_component_error_localization.py", report["errors"])
        with TemporaryDirectory() as temp:
            with m5610_private_roots(Path(temp)):
                with self.assertRaises(PermissionError):
                    commitment.commit_m57_preoutcome_diagnostic_mode("missing-m571-run")
                with self.assertRaises((PermissionError, ValueError)):
                    commitment.commit_m57_preoutcome_diagnostic_mode("../escape")

    def test_shared_lock_prevents_scoring_from_racing_first_commit(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m571-lock-order"
            with m5610_private_roots(root):
                materialize_scoring_run(root, run_id)
                original_write = durable._durable_atomic_write_json
                entered = threading.Event()
                release = threading.Event()
                owner_errors: list[BaseException] = []

                def held_write(path, value, *, exclusive=False):
                    result = original_write(path, value, exclusive=exclusive)
                    if Path(path).name == commitment.MODE_FILENAME:
                        entered.set()
                        if not release.wait(timeout=10):
                            raise TimeoutError("test did not release M57.1 writer")
                    return result

                def owner() -> None:
                    try:
                        commitment.commit_m57_preoutcome_diagnostic_mode(run_id)
                    except BaseException as exc:  # pragma: no cover - asserted below
                        owner_errors.append(exc)

                original_loader = scorer.load_outcome_inputs
                with mock.patch.object(
                    durable, "_durable_atomic_write_json", side_effect=held_write
                ), mock.patch.object(scorer, "load_outcome_inputs", wraps=original_loader) as loader:
                    thread = threading.Thread(target=owner)
                    thread.start()
                    self.assertTrue(entered.wait(timeout=10))
                    with self.assertRaisesRegex(PermissionError, "active local owner"):
                        crash_safe.execute_crash_safe_outcome_join_formal_scoring(run_id)
                    self.assertEqual(loader.call_count, 0)
                    release.set()
                    thread.join(timeout=15)
                    self.assertFalse(thread.is_alive())
            self.assertEqual(owner_errors, [])

    def test_partial_or_mismatched_m56_result_link_is_not_authorized(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m571-partial-result-link"
            with m5610_private_roots(root):
                run_root = materialize_scoring_run(root, run_id)
                commitment.commit_m57_preoutcome_diagnostic_mode(run_id)
                (run_root / "scoring" / scorer.SCORE_REPORT_FILENAME).write_text(
                    "{}", encoding="utf-8"
                )
                validation = commitment.validate_m57_preoutcome_diagnostic_mode(run_id)
            self.assertTrue(validation["m56_result_present"])
            self.assertFalse(validation["m56_result_link_valid"])
            self.assertFalse(validation["formal_m57_execution_authorized"])

    def test_legacy_m56_4_result_without_m56_10_chain_is_not_a_valid_link(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m571-legacy-result-chain-denied"
            with m5610_private_roots(root):
                materialize_scoring_run(root, run_id)
                commitment.commit_m57_preoutcome_diagnostic_mode(run_id)
                scorer.execute_formal_scoring(run_id)
                validation = commitment.validate_m57_preoutcome_diagnostic_mode(run_id)
            self.assertTrue(validation["m56_result_present"])
            self.assertFalse(validation["m56_result_link_valid"])
            self.assertTrue(
                any(
                    error.startswith("m56_10_chain.missing:")
                    for error in validation["m56_result_link_errors"]
                )
            )
            self.assertFalse(validation["formal_m57_execution_authorized"])

    def test_engineering_rehearsal_and_dashboard_are_bounded(self):
        rehearsal = commitment.build_engineering_rehearsal()
        report = commitment.validate_rehearsal(rehearsal)
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(rehearsal["first_commit_outcome_state_count"], 0)
        self.assertTrue(rehearsal["post_result_link_valid"])
        self.assertEqual(rehearsal["m57_1_model_call_count"], 0)
        self.assertEqual(rehearsal["real_target_outcome_access_count"], 0)
        self.assertFalse(rehearsal["formal_m57_result_created"])
        page = commitment.render_dashboard(rehearsal, commitment.build_live_audit())
        self.assertIn("先封存怎麼查錯，再開答案", page)
        self.assertIn("FORMAL M57 DENIED", page)
        self.assertIn("M58 仍禁止開始", page)

    def test_frozen_m57_analyzer_behavior_is_unchanged(self):
        clear = localization.analyze_component_substitution_bundle(
            localization.build_synthetic_bundle()
        )
        tied = localization.analyze_component_substitution_bundle(
            localization.build_synthetic_bundle(ambiguous_tie=True)
        )
        self.assertEqual(clear["leading_recoverable_stage"], "retrieval")
        self.assertIsNone(tied["leading_recoverable_stage"])
        self.assertFalse(clear["formal_result_created"])

    def test_saved_rehearsal_and_implementation_freeze_match_files(self):
        saved = commitment.load_saved_rehearsal()
        self.assertTrue(commitment.validate_rehearsal(saved)["valid"])
        freeze_path = (
            Path(__file__).resolve().parent
            / "research/m57_1_preoutcome_diagnostic_commitment_implementation_freeze_2026-09-04.json"
        )
        freeze = commitment.load_json(freeze_path)
        self.assertEqual(
            freeze["schema"],
            "uruha_m57_1_preoutcome_diagnostic_commitment_implementation_freeze_v1",
        )
        self.assertEqual(
            freeze["status"],
            "implementation_frozen_after_engineering_acceptance_before_any_real_m56_target_outcome_access",
        )
        for relative, expected_hash in freeze["files"].items():
            self.assertEqual(commitment.sha256_file(Path(__file__).resolve().parent / relative), expected_hash)


if __name__ == "__main__":
    unittest.main()
