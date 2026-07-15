#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CLOSURE_PATH = ROOT / "configs" / "selective_discourse_state_v53_closure.json"
ANALYSIS_PATH = ROOT / "reports" / "selective_discourse_state_v53_development_analysis.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SelectiveDiscourseStateV53ResultTests(unittest.TestCase):
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

    def test_hybrid_improved_calls_and_removed_false_actions(self):
        result = self.closure["development_result"]
        self.assertEqual(result["hybrid_commitment_delta"], 15)
        self.assertEqual(result["hybrid_call_delta"], 6)
        self.assertEqual(
            result["selective_state_machine_with_v51_fallback"]["false_action_count"],
            0,
        )
        self.assertEqual(result["call_regression_count"], 0)

    def test_gate_still_fails_due_to_two_semantic_regressions(self):
        self.assertFalse(self.analysis["development_gate"]["passed"])
        self.assertEqual(self.analysis["development_gate"]["failed_checks"], ["semantic_regressions"])
        self.assertEqual(self.closure["failed_gate"]["observed"], 2)
        self.assertEqual(self.closure["failed_gate"]["allowed_at_most"], 1)

    def test_failure_is_concentrated_in_one_rule(self):
        failure = self.closure["failure_concentration"]
        self.assertEqual(failure["rule"], "quoted_data_with_explicit_nonexecution")
        self.assertEqual(failure["rule_correct"], "1/4")

    def test_nothing_advances_from_failed_development(self):
        self.assertFalse(self.closure["fresh_holdout_construction_authorized"])
        self.assertFalse(self.closure["runtime_change_authorized"])
        self.assertFalse(self.closure["shadow_integration_authorized"])
        self.assertFalse(self.closure["physical_vrm_execution_enabled"])
        self.assertFalse(self.analysis["fresh_holdout_construction_authorized"])


if __name__ == "__main__":
    unittest.main()
