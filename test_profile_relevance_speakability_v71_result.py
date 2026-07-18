import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class ProfileRelevanceSpeakabilityV71ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = json.loads(
            (ROOT / "reports/profile_relevance_speakability_v71_raw.json").read_text(encoding="utf-8")
        )
        cls.analysis = json.loads(
            (ROOT / "reports/profile_relevance_speakability_v71_analysis.json").read_text(encoding="utf-8")
        )
        cls.lock = json.loads(
            (ROOT / "configs/profile_relevance_speakability_v71_result_lock.json").read_text(encoding="utf-8")
        )

    def test_run_is_complete_isolated_and_gold_free(self):
        self.assertTrue(self.analysis["run_integrity"]["passed"])
        self.assertEqual(self.raw["row_count"], 72)
        self.assertEqual(len(self.raw["rows"]), 72)
        self.assertFalse(self.raw["gold_in_raw"])
        self.assertEqual(self.raw["production_database_access_count"], 0)
        self.assertEqual(self.raw["physical_action_count"], 0)
        self.assertTrue(all(row["temporary_database"] for row in self.raw["rows"]))

    def test_selector_passes_but_answer_and_cost_gates_do_not(self):
        self.assertTrue(self.analysis["selector_gates"]["passed"])
        self.assertFalse(self.analysis["ability_gates"]["passed"])
        self.assertFalse(self.analysis["cost_gates"]["passed"])
        treatment = self.analysis["metrics"]["typed_active_provenance_selection_treatment"]
        self.assertEqual(treatment["selector_exact_case_count"], 23)
        self.assertEqual(treatment["selector_false_positive_count"], 0)
        self.assertEqual(treatment["selector_false_negative_count"], 1)
        self.assertEqual(treatment["overall_pass_count"], 12)
        self.assertEqual(treatment["relevant_pass_count"], 6)
        self.assertEqual(treatment["irrelevant_profile_intrusion_count"], 0)
        self.assertEqual(treatment["abstention_pass_count"], 2)

    def test_result_freezes_answer_use_and_preserves_pairwise_effect(self):
        self.assertEqual(self.analysis["decision"], "freeze_answer_use_and_move_downstream")
        self.assertEqual(self.analysis["pairwise"]["newly_passed_vs_bare_key"], 1)
        self.assertEqual(self.analysis["pairwise"]["regressions_vs_bare_key"], 0)
        self.assertEqual(self.analysis["pairwise"]["newly_passed_vs_full_projection"], 2)
        self.assertFalse(self.lock["answer_path_shadow_authorized"])
        self.assertFalse(self.lock["runtime_activation_authorized"])
        self.assertFalse(self.lock["post_run_case_editing_authorized"])
        self.assertFalse(self.lock["post_run_threshold_change_authorized"])

    def test_result_lock_binds_every_formal_artifact(self):
        for name, artifact in self.lock["frozen_artifacts"].items():
            actual = hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
            self.assertEqual(actual, artifact["sha256"], name)


if __name__ == "__main__":
    unittest.main()
