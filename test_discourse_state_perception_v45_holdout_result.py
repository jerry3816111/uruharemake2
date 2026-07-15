#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CLOSURE_PATH = ROOT / "configs" / "discourse_state_perception_v45_holdout_closure.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DiscourseStatePerceptionV45HoldoutResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.closure = json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))
        cls.raw = json.loads(
            (ROOT / cls.closure["raw_report"]).read_text(encoding="utf-8")
        )
        cls.analysis = json.loads(
            (ROOT / cls.closure["analysis_report"]).read_text(encoding="utf-8")
        )

    def test_closure_binds_raw_analysis_markdown_and_original_lock(self):
        bindings = (
            ("frozen_holdout_lock", "frozen_holdout_lock_sha256"),
            ("raw_report", "raw_report_sha256"),
            ("analysis_report", "analysis_report_sha256"),
            ("markdown_report", "markdown_report_sha256"),
        )
        for path_key, hash_key in bindings:
            self.assertEqual(_sha256(ROOT / self.closure[path_key]), self.closure[hash_key])

    def test_raw_report_is_complete_and_uses_the_preinference_runner_commit(self):
        self.assertEqual(len(self.raw["judgment_rows"]), 126)
        self.assertIsNotNone(self.raw["completed_at"])
        self.assertEqual(self.raw["runner_commit"], self.closure["runner_commit"])

    def test_negative_result_cannot_be_relabelled_as_runtime_authorization(self):
        observed = self.closure["observed_result"]
        comparison = self.analysis["matched_comparison"]
        candidate = self.analysis["conditions"]["v45_discourse_candidate"]
        self.assertEqual(comparison["commitment_accuracy_delta_vs_control"], 0.0164)
        self.assertEqual(comparison["fixed_count"], 4)
        self.assertEqual(comparison["semantic_regression_count"], 3)
        self.assertEqual(candidate["extra_candidate_requested_count"], 1)
        self.assertEqual(candidate["compiled_call_exact_count"], 41)
        self.assertEqual(observed["semantic_regression_count"], 3)
        self.assertFalse(self.analysis["holdout_gate_passed"])
        self.assertTrue(self.analysis["holdout_consumed"])
        self.assertFalse(self.analysis["post_holdout_tuning_on_this_dataset_authorized"])
        self.assertFalse(self.closure["runtime_change_authorized"])
        self.assertFalse(self.closure["shadow_integration_authorized"])
        self.assertFalse(self.closure["physical_vrm_execution_enabled"])


if __name__ == "__main__":
    unittest.main()
