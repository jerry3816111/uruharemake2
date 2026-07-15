#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RAW_PATH = ROOT / "reports" / "metalinguistic_nonrequest_v54_holdout_raw.json"
ANALYSIS_PATH = ROOT / "reports" / "metalinguistic_nonrequest_v54_holdout_analysis.json"
CLOSURE_PATH = ROOT / "configs" / "metalinguistic_nonrequest_v54_holdout_closure.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class MetalinguisticNonrequestV54HoldoutResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = json.loads(RAW_PATH.read_text(encoding="utf-8"))
        cls.analysis = json.loads(ANALYSIS_PATH.read_text(encoding="utf-8"))
        cls.closure = json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))

    def test_report_is_complete_and_uses_only_local_budget(self):
        self.assertIsNotNone(self.raw["completed_at"])
        self.assertEqual(len(self.raw["target_rows"]), 76)
        self.assertEqual(self.raw["model_calls_made"], 76)
        self.assertFalse(self.raw["paid_api_used"])

    def test_closure_hash_binds_raw_and_analysis(self):
        self.assertEqual(_sha256(RAW_PATH), self.closure["raw_report_sha256"])
        self.assertEqual(
            _sha256(ANALYSIS_PATH), self.closure["analysis_report_sha256"]
        )

    def test_v54_improves_aggregate_but_has_locked_regressions(self):
        comparison = self.analysis["hybrid_vs_fresh_v51"]
        self.assertEqual(comparison["commitment_correct_count_delta"], 10)
        self.assertEqual(comparison["compiled_call_exact_count_delta"], 4)
        self.assertEqual(comparison["semantic_regression_count"], 1)
        self.assertEqual(comparison["call_regression_count"], 1)

    def test_failure_attribution_remains_explicit(self):
        failures = self.analysis["failure_attribution"]
        self.assertEqual(failures["resolved_state_error_count"], 4)
        self.assertEqual(failures["fallback_model_error_count"], 2)
        self.assertEqual(failures["compiler_only_failure_count"], 1)

    def test_no_gate_or_runtime_claim_is_overstated(self):
        self.assertFalse(self.analysis["state_component_gate"]["passed"])
        self.assertFalse(self.analysis["matched_comparison_gate"]["passed"])
        self.assertFalse(self.analysis["end_to_end_gate"]["passed"])
        self.assertFalse(self.analysis["runtime_change_authorized"])
        self.assertFalse(self.analysis["shadow_integration_authorized"])
        self.assertFalse(self.analysis["physical_vrm_execution_enabled"])

    def test_smaller_model_test_is_diagnostic_not_a_complete_fix(self):
        self.assertTrue(self.analysis["smaller_model_experiment_triggered"])
        self.assertIn("94.74%", self.closure["decision_boundary"])


if __name__ == "__main__":
    unittest.main()
