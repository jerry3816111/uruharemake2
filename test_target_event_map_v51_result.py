#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CLOSURE_PATH = ROOT / "configs" / "target_event_map_v51_closure.json"
ANALYSIS_PATH = ROOT / "reports" / "target_event_map_v51_development_analysis.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TargetEventMapV51ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.closure = json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))
        cls.analysis = json.loads(ANALYSIS_PATH.read_text(encoding="utf-8"))

    def test_every_result_artifact_is_hash_bound(self):
        for key, expected in self.closure["bound_artifacts"].items():
            if key.endswith("_sha256"):
                path = ROOT / self.closure["bound_artifacts"][
                    key.removesuffix("_sha256")
                ]
                self.assertEqual(_sha256(path), expected)

    def test_candidate_absolute_result_is_strong_but_not_advanced(self):
        candidate = self.analysis["conditions"]["target_event_map_candidate"]
        self.assertEqual(candidate["commitment_correct_count"], 54)
        self.assertEqual(candidate["compiled_call_exact_count"], 46)
        self.assertEqual(candidate["false_action_count"], 0)
        self.assertTrue(self.analysis["candidate_absolute_gate"]["passed"])
        self.assertFalse(self.analysis["development_gate_passed"])

    def test_matched_gain_and_single_regression_are_preserved(self):
        comparison = self.analysis["matched_comparison"]
        self.assertEqual(comparison["commitment_correct_count_delta"], 4)
        self.assertEqual(comparison["compiled_call_exact_count_delta"], 4)
        self.assertEqual(comparison["false_action_count_delta"], -2)
        self.assertEqual(comparison["semantic_regression_count"], 1)
        self.assertEqual(comparison["call_regression_count"], 1)
        self.assertEqual(comparison["call_regression_case_ids"], ["v45h_negation_02"])

    def test_failed_comparison_cannot_authorize_holdout_or_runtime(self):
        self.assertFalse(self.analysis["matched_comparison_gate"]["passed"])
        self.assertFalse(self.analysis["fresh_holdout_authorized"])
        self.assertFalse(self.analysis["runtime_change_authorized"])
        self.assertFalse(self.analysis["physical_vrm_execution_enabled"])
        self.assertFalse(self.closure["runtime_change_authorized"])
        self.assertFalse(self.closure["shadow_integration_authorized"])


if __name__ == "__main__":
    unittest.main()
