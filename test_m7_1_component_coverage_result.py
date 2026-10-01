from __future__ import annotations

import json
from pathlib import Path
import unittest

from longitudinal_human_model.registry import sha256_file


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis/m7_1_component_coverage_remediation_result.json"
LOCK = ROOT / "configs/m7_1_component_coverage_result_lock.json"


class FrozenM71ComponentCoverageResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = json.loads(RESULT.read_text(encoding="utf-8"))
        cls.lock = json.loads(LOCK.read_text(encoding="utf-8"))

    def test_result_hash_and_engineering_gate_are_frozen(self):
        self.assertEqual(self.lock["result_sha256"], sha256_file(RESULT))
        self.assertEqual("complete_component_coverage_remediation", self.result["status"])
        self.assertTrue(self.result["engineering_gate_pass"])
        self.assertTrue(self.result["component_coverage_complete"])

    def test_all_ten_components_are_independently_evaluated(self):
        self.assertEqual(10, len(self.result["ablations"]))
        self.assertTrue(all(row["status"] == "evaluated" for row in self.result["ablations"].values()))
        self.assertEqual(10, self.result["evaluated_ablation_metric_change_count"])
        self.assertEqual(28, len(self.result["feature_names"]))

    def test_preference_and_habit_are_visible_but_not_promoted_to_lift_evidence(self):
        self.assertTrue(self.result["ablations"]["preference"]["metric_changed"])
        self.assertTrue(self.result["ablations"]["habit"]["metric_changed"])
        self.assertFalse(self.result["predictive_lift_claim_authorized"])
        self.assertFalse(self.result["formal_target_claim"])

    def test_negative_findings_and_no_language_are_preserved(self):
        self.assertLess(self.result["ablations"]["temporal_dynamics"]["delta_vs_full"]["negative_log_likelihood"], 0)
        self.assertLess(self.result["ablations"]["relationship"]["delta_vs_full"]["negative_log_likelihood"], 0)
        self.assertEqual(0, self.result["model_calls"])
        self.assertFalse(self.result["language_realization_performed"])


if __name__ == "__main__":
    unittest.main()
