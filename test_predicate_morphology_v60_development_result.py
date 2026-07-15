#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CLOSURE_PATH = ROOT / "configs" / "predicate_morphology_v60_development_closure.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PredicateMorphologyV60DevelopmentResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.closure = json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))
        cls.analysis = json.loads(
            (ROOT / cls.closure["artifact_bindings"]["analysis"]).read_text(
                encoding="utf-8"
            )
        )
        cls.raw = json.loads(
            (ROOT / cls.closure["artifact_bindings"]["raw"]).read_text(
                encoding="utf-8"
            )
        )

    def test_all_result_artifacts_match_closure_hashes(self):
        bindings = self.closure["artifact_bindings"]
        for key, expected in bindings.items():
            if not key.endswith("_sha256"):
                continue
            path_key = key.removesuffix("_sha256")
            self.assertEqual(_sha256(ROOT / bindings[path_key]), expected, path_key)

    def test_replay_used_no_model_or_physical_action(self):
        self.assertEqual(self.raw["model_calls"], 0)
        self.assertFalse(self.raw["paid_api_used"])
        self.assertEqual(self.raw["physical_vrm_actions_executed"], 0)
        self.assertEqual(len(self.raw["target_rows"]), 73)
        self.assertEqual(len(self.raw["case_rows"]), 72)

    def test_exact_preregistered_effect_passed(self):
        self.assertTrue(self.analysis["gates"]["passed"])
        self.assertEqual(self.analysis["gates"]["failed_checks"], [])
        self.assertEqual(self.analysis["candidate_state"]["correct_count"], 71)
        self.assertEqual(
            self.analysis["candidate_compiler"]["ordered_exact_count"], 72
        )
        self.assertEqual(
            self.analysis["candidate_compiler"]["false_action_case_count"], 0
        )
        self.assertEqual(
            self.analysis["event_role_replay"]["role_slot_correct_count"], 280
        )

    def test_matched_fixes_have_no_regressions(self):
        comparison = self.analysis["matched_comparison"]
        self.assertEqual(comparison["state_fix_count"], 4)
        self.assertEqual(comparison["state_regression_count"], 0)
        self.assertEqual(comparison["case_fix_count"], 4)
        self.assertEqual(comparison["case_regression_count"], 0)

    def test_only_prespecified_residuals_remain(self):
        observed = {
            row["case_id"] for row in self.analysis["residual_state_failures"]
        }
        expected = {row["case_id"] for row in self.closure["prespecified_residuals"]}
        self.assertEqual(observed, expected)

    def test_decision_authorizes_only_a_fresh_holdout(self):
        self.assertEqual(
            self.analysis["decision"],
            "authorize_second_fresh_v60_independent_holdout",
        )
        self.assertEqual(self.closure["decision"], self.analysis["decision"])
        for key in (
            "runtime_change_authorized",
            "shadow_integration_authorized",
            "physical_vrm_execution_enabled",
            "complete_rightbrain_claim_authorized",
            "broad_human_likeness_claim_authorized",
        ):
            self.assertFalse(self.closure[key], key)


if __name__ == "__main__":
    unittest.main()
