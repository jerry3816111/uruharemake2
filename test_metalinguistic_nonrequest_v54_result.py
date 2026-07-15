#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CLOSURE_PATH = ROOT / "configs" / "metalinguistic_nonrequest_v54_closure.json"
ANALYSIS_PATH = ROOT / "reports" / "metalinguistic_nonrequest_v54_development_analysis.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class MetalinguisticNonrequestV54ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.closure = json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))
        cls.analysis = json.loads(ANALYSIS_PATH.read_text(encoding="utf-8"))

    def test_every_result_artifact_is_hash_bound(self):
        bound = self.closure["bound_artifacts"]
        for key, expected in bound.items():
            if not key.endswith("_sha256"):
                continue
            path = ROOT / bound[key.removesuffix("_sha256")]
            self.assertEqual(_sha256(path), expected, path)

    def test_all_inherited_and_specific_gates_pass(self):
        self.assertTrue(self.analysis["inherited_development_gate"]["passed"])
        self.assertTrue(self.analysis["v54_specific_gate"]["passed"])
        self.assertTrue(self.analysis["development_gate"]["passed"])
        self.assertEqual(self.analysis["development_gate"]["failed_checks"], [])

    def test_exactly_three_targets_changed_and_all_were_corrected(self):
        comparison = self.analysis["v54_specific_comparison"]
        self.assertEqual(comparison["changed_target_count"], 3)
        self.assertEqual(comparison["corrected_target_count"], 3)
        self.assertEqual(comparison["previously_correct_target_regression_count"], 0)
        self.assertEqual(comparison["previously_correct_call_regression_count"], 0)

    def test_hybrid_is_perfect_at_state_level_and_has_zero_false_action(self):
        hybrid = self.closure["development_result"]["v54_selective_hybrid"]
        self.assertEqual(hybrid["commitment_correct"], "85/85")
        self.assertEqual(hybrid["false_action_count"], 0)
        self.assertEqual(self.closure["development_result"]["semantic_regression_count"], 0)
        self.assertEqual(self.closure["development_result"]["call_regression_count"], 0)

    def test_pass_authorizes_only_new_holdout_construction(self):
        self.assertEqual(
            self.analysis["decision"],
            "authorize_independent_v54_holdout_construction",
        )
        self.assertTrue(self.closure["fresh_holdout"]["construction_authorized"])
        self.assertFalse(self.closure["fresh_generalization_claim_authorized"])
        self.assertFalse(self.closure["runtime_change_authorized"])
        self.assertFalse(self.closure["shadow_integration_authorized"])
        self.assertFalse(self.closure["physical_vrm_execution_enabled"])


if __name__ == "__main__":
    unittest.main()
