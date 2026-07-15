#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CLOSURE_PATH = ROOT / "configs" / "precise_target_mentions_v52_closure.json"
ANALYSIS_PATH = ROOT / "reports" / "precise_target_mentions_v52_development_analysis.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PreciseTargetMentionsV52ResultTests(unittest.TestCase):
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

    def test_representation_and_model_gates_passed(self):
        self.assertTrue(self.analysis["representation_gate"]["passed"])
        self.assertTrue(self.analysis["candidate_absolute_gate"]["passed"])
        self.assertTrue(self.analysis["matched_comparison_gate"]["passed"])
        self.assertTrue(self.analysis["development_gate_passed"])

    def test_candidate_improved_one_call_without_regression(self):
        candidate = self.analysis["conditions"]["precise_target_mentions_candidate"]
        comparison = self.analysis["matched_comparison"]
        self.assertEqual(candidate["commitment_correct_count"], 55)
        self.assertEqual(candidate["compiled_call_exact_count"], 47)
        self.assertEqual(candidate["false_action_count"], 0)
        self.assertEqual(comparison["compiled_call_exact_count_delta"], 1)
        self.assertEqual(comparison["semantic_regression_count"], 0)
        self.assertEqual(comparison["call_regression_count"], 0)

    def test_development_pass_authorizes_only_holdout_construction(self):
        self.assertTrue(self.analysis["fresh_holdout_construction_authorized"])
        self.assertFalse(self.analysis["fresh_holdout_claim_authorized"])
        self.assertFalse(self.analysis["runtime_change_authorized"])
        self.assertFalse(self.analysis["physical_vrm_execution_enabled"])
        self.assertFalse(self.closure["runtime_change_authorized"])
        self.assertFalse(self.closure["shadow_integration_authorized"])


if __name__ == "__main__":
    unittest.main()
