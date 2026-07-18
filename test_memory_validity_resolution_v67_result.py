import hashlib
import json
import unittest
from pathlib import Path

import analyze_memory_validity_resolution_v67 as analyzer


ROOT = Path(__file__).resolve().parent


class MemoryValidityResolutionV67ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = json.loads(analyzer.RAW_PATH.read_text(encoding="utf-8"))
        cls.analysis = json.loads(analyzer.ANALYSIS_PATH.read_text(encoding="utf-8"))
        cls.prereg = json.loads(analyzer.PREREG_PATH.read_text(encoding="utf-8"))
        cls.dataset = json.loads(analyzer.DATASET_PATH.read_text(encoding="utf-8"))
        cls.harness_lock = json.loads(analyzer.LOCK_PATH.read_text(encoding="utf-8"))
        cls.result_lock = json.loads(analyzer.RESULT_LOCK_PATH.read_text(encoding="utf-8"))

    def test_result_lock_binds_every_formal_artifact(self):
        for name, artifact in self.result_lock["frozen_artifacts"].items():
            digest = hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
            self.assertEqual(digest, artifact["sha256"], name)

    def test_analysis_recomputes_exactly_from_frozen_raw(self):
        recomputed = analyzer.analyze_raw(self.raw, self.dataset, self.prereg, self.harness_lock)
        for key in (
            "decision",
            "run_integrity",
            "metrics",
            "family_exact_working_memory",
            "pairwise",
            "success_gates",
            "case_scores",
            "evidence_boundary",
        ):
            self.assertEqual(recomputed[key], self.analysis[key], key)

    def test_positive_result_has_no_hidden_runtime_or_gold_use(self):
        self.assertTrue(self.analysis["run_integrity"]["passed"])
        self.assertTrue(self.analysis["success_gates"]["passed"])
        self.assertFalse(self.analysis["production_runtime_changed"])
        self.assertFalse(self.result_lock["runtime_change_authorized"])
        self.assertFalse(self.raw["gold_in_raw"])
        self.assertNotIn('"expected"', analyzer.RAW_PATH.read_text(encoding="utf-8"))

    def test_claimed_gain_and_safety_metrics_match_raw_result(self):
        control = self.analysis["metrics"]["current_all_candidates_eligible_control"]
        treatment = self.analysis["metrics"]["generic_validity_resolver_treatment"]
        self.assertEqual(control["exact_working_memory_count"], 7)
        self.assertEqual(control["stale_or_inapplicable_intrusion_count"], 14)
        self.assertEqual(treatment["exact_working_memory_count"], 18)
        self.assertEqual(treatment["stale_or_inapplicable_intrusion_count"], 0)
        self.assertEqual(treatment["over_suppression_count"], 0)
        self.assertEqual(self.analysis["pairwise"]["newly_exact_working_memory_vs_control"], 11)
        self.assertEqual(self.analysis["pairwise"]["regressions_vs_control"], 0)


if __name__ == "__main__":
    unittest.main()
