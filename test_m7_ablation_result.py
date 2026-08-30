from __future__ import annotations

import json
from pathlib import Path
import unittest

from longitudinal_human_model.registry import sha256_file


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis/m7_ablation_intervention_diagnostic_first_result.json"
LOCK = ROOT / "configs/m7_ablation_intervention_result_lock.json"


class FrozenM7ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = json.loads(RESULT.read_text(encoding="utf-8"))
        cls.lock = json.loads(LOCK.read_text(encoding="utf-8"))

    def test_hash_and_bounded_status_are_frozen(self):
        self.assertEqual(self.lock["result_sha256"], sha256_file(RESULT))
        self.assertEqual("complete_diagnostic_run", self.result["status"])
        self.assertTrue(self.result["engineering_gate_pass"])
        self.assertFalse(self.result["component_coverage_complete"])
        self.assertFalse(self.result["formal_target_claim"])

    def test_both_missing_components_remain_not_identifiable(self):
        self.assertEqual("not_identifiable", self.result["ablations"]["preference"]["status"])
        self.assertEqual("not_identifiable", self.result["ablations"]["habit"]["status"])

    def test_negative_ablation_findings_are_preserved(self):
        temporal = self.result["ablations"]["temporal_dynamics"]["delta_vs_full"]
        relationship = self.result["ablations"]["relationship"]["delta_vs_full"]
        self.assertGreater(temporal["top1_accuracy"], 0)
        self.assertLess(temporal["brier_score"], 0)
        self.assertLess(relationship["brier_score"], 0)

    def test_quiet_success_support_intervention_flips_to_correct_label(self):
        best = self.result["quiet_success_diagnostic"]["best_named_intervention"]
        self.assertEqual("event_support_max", best["intervention_id"])
        self.assertEqual("acknowledge_then_continue", best["intervened_selected_behavior"])
        self.assertGreater(best["delta_actual_probability"], 0.77)
        self.assertEqual(1.0, self.result["explanation_faithfulness"]["nonzero_probability_effect_rate"])


if __name__ == "__main__":
    unittest.main()
