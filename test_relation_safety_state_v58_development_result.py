#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path

from run_relation_safety_state_v58_development import CANDIDATE, CONTROL


ROOT = Path(__file__).resolve().parent
CLOSURE_PATH = ROOT / "configs" / "relation_safety_state_v58_development_closure.json"
RAW_PATH = ROOT / "reports" / "relation_safety_state_v58_development_raw.json"
ANALYSIS_PATH = ROOT / "reports" / "relation_safety_state_v58_development_analysis.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RelationSafetyStateV58DevelopmentResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load = lambda path: json.loads(path.read_text(encoding="utf-8"))
        cls.closure = load(CLOSURE_PATH)
        cls.raw = load(RAW_PATH)
        cls.analysis = load(ANALYSIS_PATH)

    def test_every_result_artifact_is_hash_bound(self):
        bindings = self.closure["artifact_bindings"]
        for key, expected in bindings.items():
            if not key.endswith("_sha256"):
                continue
            path_key = key.removesuffix("_sha256")
            self.assertIn(path_key, bindings)
            self.assertEqual(_sha256(ROOT / bindings[path_key]), expected, path_key)

    def test_run_started_from_merged_frozen_harness(self):
        self.assertEqual(self.raw["runner_commit"], self.closure["frozen_run_commit"])
        self.assertEqual(self.raw["conditions"], [CONTROL, CANDIDATE])
        self.assertEqual(len(self.raw["target_rows"]), 85)
        self.assertEqual(len(self.raw["case_rows"]), 64)

    def test_replay_used_no_model_money_or_physical_action(self):
        self.assertEqual(self.raw["model_calls"], 0)
        self.assertFalse(self.raw["paid_api_used"])
        self.assertEqual(self.raw["physical_vrm_actions_executed"], 0)
        accounting = self.closure["execution_accounting"]
        self.assertEqual(accounting["model_calls_made"], 0)
        self.assertFalse(accounting["paid_api_used"])
        self.assertEqual(accounting["physical_vrm_actions_executed"], 0)

    def test_all_preregistered_safety_gates_passed(self):
        self.assertTrue(self.analysis["gates"]["passed"])
        self.assertEqual(self.analysis["gates"]["failed_checks"], [])
        self.assertTrue(all(self.analysis["gates"]["checks"].values()))
        self.assertTrue(all(row["passed"] for row in self.analysis["target_fix_results"]))
        self.assertTrue(all(row["passed"] for row in self.analysis["case_fix_results"]))

    def test_safety_improves_without_recall_loss_or_regression(self):
        control_state = self.analysis["control_state"]
        candidate_state = self.analysis["candidate_state"]
        control = self.analysis["control_compiler"]
        candidate = self.analysis["candidate_compiler"]
        comparison = self.analysis["comparison"]
        self.assertEqual((control_state["correct_count"], candidate_state["correct_count"]), (73, 79))
        self.assertEqual((control["ordered_exact_count"], candidate["ordered_exact_count"]), (54, 58))
        self.assertEqual((control["false_action_case_count"], candidate["false_action_case_count"]), (4, 0))
        self.assertAlmostEqual(control["required_call_recall"], 33 / 39)
        self.assertAlmostEqual(candidate["required_call_recall"], 33 / 39)
        self.assertEqual(comparison["state_regression_count"], 0)
        self.assertEqual(comparison["call_regression_count"], 0)

    def test_pass_only_authorizes_an_independent_holdout(self):
        expected = "authorize_independent_v58_safety_holdout"
        self.assertEqual(self.analysis["decision"], expected)
        self.assertEqual(self.closure["decision"], expected)
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
