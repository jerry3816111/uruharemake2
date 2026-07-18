import hashlib
import json
import unittest
from pathlib import Path

import analyze_profile_assertion_boundary_v68 as analyzer


ROOT = Path(__file__).resolve().parent


class ProfileAssertionBoundaryV68ResultTests(unittest.TestCase):
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
        for key in ("decision", "run_integrity", "metrics", "family_exact", "language_exact", "pairwise", "success_gates", "case_scores", "evidence_boundary"):
            self.assertEqual(recomputed[key], self.analysis[key], key)

    def test_result_authorizes_only_guard_not_stateful_persistence(self):
        self.assertTrue(self.analysis["run_integrity"]["passed"])
        self.assertTrue(self.analysis["success_gates"]["passed"])
        self.assertTrue(self.result_lock["runtime_change_authorized"])
        self.assertFalse(self.result_lock["stateful_writer_authorized"])
        self.assertFalse(self.raw["persistent_memory_read_or_write"])
        self.assertNotIn('"expected"', analyzer.RAW_PATH.read_text(encoding="utf-8"))

    def test_claimed_precision_recall_and_pairwise_gain_match(self):
        control = self.analysis["metrics"]["current_unguarded_extractor_control"]
        treatment = self.analysis["metrics"]["assertion_scope_guard_treatment"]
        self.assertEqual(control["exact_case_count"], 12)
        self.assertEqual(control["non_assertion_false_write_count"], 12)
        self.assertEqual(treatment["exact_case_count"], 24)
        self.assertEqual(treatment["non_assertion_false_write_count"], 0)
        self.assertEqual(treatment["direct_assertion_exact_count"], 12)
        self.assertEqual(treatment["fact_precision"], 1.0)
        self.assertEqual(treatment["fact_recall"], 1.0)
        self.assertEqual(self.analysis["pairwise"], {"newly_exact_vs_control": 12, "regressions_vs_control": 0})


if __name__ == "__main__":
    unittest.main()
