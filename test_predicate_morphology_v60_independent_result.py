#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CLOSURE_PATH = (
    ROOT / "configs" / "predicate_morphology_v60_independent_result_closure.json"
)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PredicateMorphologyV60IndependentResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.closure = json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))
        bindings = cls.closure["artifact_bindings"]
        cls.raw = json.loads((ROOT / bindings["raw"]).read_text(encoding="utf-8"))
        cls.analysis = json.loads(
            (ROOT / bindings["analysis"]).read_text(encoding="utf-8")
        )

    def test_all_frozen_artifacts_match_closure_hashes(self):
        bindings = self.closure["artifact_bindings"]
        for key, expected in bindings.items():
            if not key.endswith("_sha256"):
                continue
            path_key = key.removesuffix("_sha256")
            self.assertEqual(_sha256(ROOT / bindings[path_key]), expected, path_key)

    def test_run_used_exactly_the_authorized_local_budget(self):
        accounting = self.closure["execution_accounting"]
        self.assertEqual(len(self.raw["target_rows"]), accounting["target_count"])
        self.assertEqual(len(self.raw["case_rows"]), accounting["case_count"])
        self.assertEqual(self.raw["model_calls_made"], accounting["logical_model_calls"])
        self.assertEqual(
            self.raw["transport_attempts_made"], accounting["transport_attempts"]
        )
        self.assertEqual(
            self.raw["model_snapshot"]["digest"], accounting["model_digest"]
        )
        self.assertFalse(self.raw["paid_api_used"])
        self.assertEqual(self.raw["physical_vrm_actions_executed"], 0)

    def test_large_matched_gain_is_preserved_without_overclaiming(self):
        comparison = self.analysis["matched_comparison"]
        expected = self.closure["matched_effect"]
        self.assertEqual(comparison["state_correct_count_delta"], expected["state_correct_delta"])
        self.assertEqual(comparison["state_fix_count"], expected["state_fixes"])
        self.assertEqual(comparison["state_regression_count"], 0)
        self.assertEqual(comparison["ordered_exact_count_delta"], expected["ordered_exact_delta"])
        self.assertEqual(comparison["case_fix_count"], expected["case_fixes"])
        self.assertEqual(comparison["case_regression_count"], 0)
        self.assertEqual(
            comparison["false_action_case_count_delta"], expected["false_action_delta"]
        )
        self.assertEqual(
            comparison["two_sided_exact_mcnemar_p"],
            expected["two_sided_exact_mcnemar_p"],
        )

    def test_absolute_safety_gate_failed_and_decision_rejects_advancement(self):
        self.assertFalse(self.analysis["gates"]["passed"])
        self.assertEqual(
            self.analysis["gates"]["failed_checks"],
            self.closure["failed_absolute_gates"],
        )
        self.assertEqual(self.analysis["candidate_state"]["correct_count"], 113)
        self.assertEqual(self.analysis["candidate_compiler"]["ordered_exact_count"], 115)
        self.assertEqual(
            self.analysis["candidate_compiler"]["false_action_case_count"], 2
        )
        self.assertEqual(
            self.closure["decision"],
            "reject_v60_independent_advancement_and_close_vrm_action_workstream",
        )

    def test_morphology_was_not_the_remaining_failure_source(self):
        morphology = self.analysis["morphology_generalization"]
        self.assertEqual(morphology["controlled_slot_correct_count"], 588)
        self.assertEqual(morphology["controlled_slot_count"], 588)
        self.assertEqual(morphology["controlled_slot_accuracy"], 1.0)
        self.assertEqual(
            self.closure["residual_attribution"]["morphology_slot_failure_targets"],
            0,
        )

    def test_result_authorizes_no_tuning_or_deployment(self):
        for key in (
            "post_result_tuning_authorized",
            "runtime_change_authorized",
            "shadow_integration_authorized",
            "physical_vrm_execution_enabled",
            "complete_rightbrain_claim_authorized",
            "broad_human_likeness_claim_authorized",
        ):
            self.assertFalse(self.closure[key], key)


if __name__ == "__main__":
    unittest.main()
