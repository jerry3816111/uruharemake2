from __future__ import annotations

from copy import deepcopy
import inspect
from pathlib import Path
import unittest

import m56_11_process_death_scoring_crash_matrix as crash_matrix


ROOT = Path(__file__).resolve().parent


class M5611ProcessDeathScoringCrashMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrix = crash_matrix.run_process_death_crash_matrix()

    def test_contract_and_frozen_dependencies_validate(self):
        report = crash_matrix.validate_contract()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["binding_count"], 6)
        self.assertEqual(report["phase_count"], 4)

    def test_public_matrix_runner_accepts_no_injection(self):
        self.assertEqual(
            list(inspect.signature(crash_matrix.run_process_death_crash_matrix).parameters),
            [],
        )

    def test_all_four_actual_process_death_states_validate(self):
        validation = crash_matrix.validate_matrix(self.matrix)
        self.assertTrue(validation["valid"], validation["errors"])
        self.assertEqual(self.matrix["phase_count"], 4)
        self.assertEqual(self.matrix["child_process_count"], 4)
        self.assertTrue(self.matrix["all_children_reaped"])
        self.assertEqual(
            [row["observed_child_exit_code"] for row in self.matrix["scenarios"]],
            [70, 71, 72, 73],
        )
        self.assertEqual(
            [row["total_outcome_loader_returns"] for row in self.matrix["scenarios"]],
            [1, 1, 1, 1],
        )

    def test_ambiguous_state_is_terminal_but_checkpoint_states_recover(self):
        rows = {row["phase"]: row for row in self.matrix["scenarios"]}
        ambiguous = rows["after_outcome_load_before_checkpoint"]
        self.assertEqual(
            ambiguous["restart"]["status"],
            "terminal_rejected_without_outcome_reload",
        )
        self.assertEqual(ambiguous["restart"]["restart_outcome_loader_calls"], 0)
        self.assertTrue(ambiguous["state_after_restart"]["terminal_failure"])
        self.assertFalse(ambiguous["state_after_restart"]["result_commitment"])
        for phase in (
            "after_checkpoint_before_canonical_report",
            "after_canonical_report_before_result_commitment",
        ):
            self.assertEqual(rows[phase]["restart"]["restart_outcome_loader_calls"], 0)
            self.assertTrue(rows[phase]["restart"]["formal_result_created"])
            self.assertTrue(rows[phase]["state_after_restart"]["result_commitment"])
        self.assertTrue(
            rows["after_canonical_report_before_result_commitment"][
                "report_unchanged_when_preexisting"
            ]
        )

    def test_matrix_hash_and_exit_mutation_are_rejected(self):
        mutated = deepcopy(self.matrix)
        mutated["scenarios"][1]["observed_child_exit_code"] = 0
        report = crash_matrix.validate_matrix(mutated)
        self.assertFalse(report["valid"])
        self.assertIn("result.hash", report["errors"])
        self.assertIn(
            "scenario:after_outcome_load_before_checkpoint:exit_code",
            report["errors"],
        )

    def test_matrix_contains_no_private_outcome_or_raw_generation_payload(self):
        self.assertEqual(crash_matrix._find_forbidden_output_keys(self.matrix), [])
        self.assertEqual(self.matrix["configured_real_private_root_access_count"], 0)
        self.assertEqual(self.matrix["real_target_outcome_access_count"], 0)
        self.assertEqual(self.matrix["scorer_model_call_count"], 0)
        self.assertEqual(self.matrix["retry_count"], 0)
        self.assertEqual(self.matrix["fallback_count"], 0)

    def test_live_audit_and_dashboard_are_read_only_and_honest(self):
        audit = crash_matrix.build_live_audit()
        self.assertEqual(audit["counts"]["v7_slots_by_ledger"], [0, 0])
        self.assertEqual(audit["counts"]["real_temporal_rows"], 0)
        self.assertFalse(audit["formal_scoring_authorized"])
        self.assertFalse(audit["power_loss_tested"])
        page = crash_matrix.render_dashboard()
        self.assertIn("M56.11", page)
        self.assertIn("程序真的消失", page)
        self.assertIn("總讀取 1", page)
        self.assertIn("不完成", page)
        self.assertIn("不是拔電", page)
        self.assertIn("0 REAL OUTCOME READS", page)
        self.assertIn("頁面數字直接來自已驗證的封存矩陣", page)
        self.assertNotIn("<form", page)
        self.assertNotIn("overflow-x", page)

    def test_demo_loads_and_validates_the_saved_matrix_artifact(self):
        report = crash_matrix.build_demo_report()
        self.assertEqual(report["matrix"]["matrix_hash"], crash_matrix.load_saved_matrix()["matrix_hash"])
        mutated = deepcopy(report["matrix"])
        mutated["retry_count"] = 1
        with self.assertRaises(PermissionError):
            crash_matrix.build_demo_report(mutated)

    def test_implementation_freeze_matches_frozen_files(self):
        freeze_path = (
            ROOT
            / "research/m56_11_process_death_scoring_crash_matrix_implementation_freeze_2026-09-03.json"
        )
        if not freeze_path.exists():
            self.skipTest("implementation freeze is created after pre-freeze verification")
        freeze = crash_matrix.load_json(freeze_path)
        self.assertEqual(
            freeze["schema"],
            "uruha_m56_process_death_scoring_crash_matrix_implementation_freeze_v1",
        )
        self.assertEqual(freeze["status"], "frozen_before_any_real_m56_target_outcome_access")
        for row in freeze["files"]:
            self.assertEqual(crash_matrix.sha256_file(ROOT / row["path"]), row["sha256"], row["path"])


if __name__ == "__main__":
    unittest.main()
