import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class ProfileStateTransitionV69ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = json.loads(
            (ROOT / "reports/profile_state_transition_v69_raw.json").read_text(encoding="utf-8")
        )
        cls.analysis = json.loads(
            (ROOT / "reports/profile_state_transition_v69_analysis.json").read_text(encoding="utf-8")
        )
        cls.lock = json.loads(
            (ROOT / "configs/profile_state_transition_v69_result_lock.json").read_text(encoding="utf-8")
        )

    def test_run_integrity_and_all_preregistered_gates_pass(self):
        self.assertTrue(self.analysis["run_integrity"]["passed"])
        self.assertTrue(self.analysis["success_gates"]["passed"])
        self.assertTrue(all(self.analysis["success_gates"]["checks"].values()))
        self.assertEqual(self.raw["row_count"], 54)
        self.assertEqual(
            len({(row["case_id"], row["condition"]) for row in self.raw["rows"]}),
            54,
        )

    def test_primary_comparison_is_exact_and_has_no_regression(self):
        matched = self.analysis["metrics"]["matched_append_only_readback_control"]
        treatment = self.analysis["metrics"]["typed_state_resolution_treatment"]
        self.assertEqual(matched["exact_partition_count"], 6)
        self.assertEqual(matched["stale_active_record_count"], 12)
        self.assertEqual(treatment["exact_partition_count"], 18)
        self.assertEqual(treatment["stale_active_record_count"], 0)
        self.assertEqual(treatment["missed_active_record_count"], 0)
        self.assertEqual(treatment["history_preservation_rate"], 1.0)
        self.assertEqual(self.analysis["pairwise"]["newly_exact_vs_matched_control"], 12)
        self.assertEqual(self.analysis["pairwise"]["regressions_vs_matched_control"], 0)

    def test_raw_contains_no_gold_and_uses_only_temporary_chroma(self):
        self.assertFalse(self.raw["gold_in_raw"])
        self.assertFalse(self.raw["language_model_inference"])
        self.assertFalse(self.raw["production_runtime_changed"])
        self.assertFalse(self.raw["production_database_access"])
        self.assertTrue(self.raw["temporary_chroma_access"])
        self.assertTrue(all(row["temporary_chroma"] for row in self.raw["rows"]))

    def test_result_lock_binds_outputs_and_authorizes_only_shadow_integration(self):
        for name, artifact in self.lock["frozen_artifacts"].items():
            actual = hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
            self.assertEqual(actual, artifact["sha256"], name)
        self.assertTrue(self.lock["production_shadow_integration_authorized"])
        self.assertFalse(self.lock["production_database_migration_authorized"])
        self.assertFalse(self.lock["runtime_activation_authorized"])
        self.assertFalse(self.lock["post_run_case_editing_authorized"])
        self.assertFalse(self.lock["post_run_threshold_change_authorized"])


if __name__ == "__main__":
    unittest.main()
