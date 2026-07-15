#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path

from run_event_role_governor_v59_development import CANDIDATE, CONTROL


ROOT = Path(__file__).resolve().parent
CLOSURE_PATH = ROOT / "configs" / "event_role_governor_v59_development_closure.json"
RAW_PATH = ROOT / "reports" / "event_role_governor_v59_development_raw.json"
ANALYSIS_PATH = ROOT / "reports" / "event_role_governor_v59_development_analysis.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class EventRoleGovernorV59DevelopmentResultTests(unittest.TestCase):
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

    def test_run_started_from_frozen_merged_commit_with_zero_model_calls(self):
        self.assertEqual(self.raw["runner_commit"], self.closure["frozen_run_commit"])
        self.assertEqual(self.raw["conditions"], [CONTROL, CANDIDATE])
        self.assertEqual(len(self.raw["target_rows"]), 87)
        self.assertEqual(len(self.raw["case_rows"]), 64)
        self.assertEqual(self.raw["model_calls"], 0)
        self.assertFalse(self.raw["paid_api_used"])
        self.assertEqual(self.raw["physical_vrm_actions_executed"], 0)

    def test_preregistered_effect_arrived_without_regression(self):
        control_state = self.analysis["control_state"]
        candidate_state = self.analysis["candidate_state"]
        control_compiler = self.analysis["control_compiler"]
        candidate_compiler = self.analysis["candidate_compiler"]
        comparison = self.analysis["comparison"]
        self.assertEqual((control_state["correct_count"], candidate_state["correct_count"]), (82, 85))
        self.assertEqual((control_compiler["ordered_exact_count"], candidate_compiler["ordered_exact_count"]), (60, 63))
        self.assertEqual((control_compiler["false_action_case_count"], candidate_compiler["false_action_case_count"]), (3, 0))
        self.assertEqual(candidate_compiler["no_action_specificity"], 1.0)
        self.assertEqual(candidate_state["requested_precision"], 1.0)
        self.assertEqual(candidate_state["requested_recall"], 1.0)
        self.assertEqual(candidate_compiler["required_call_recall"], 16 / 17)
        self.assertEqual(comparison["state_regression_count"], 0)
        self.assertEqual(comparison["call_regression_count"], 0)
        self.assertEqual(comparison["contrast_regression_count"], 0)

    def test_exact_three_role_relations_fixed_the_exact_three_cases(self):
        self.assertEqual(len(self.analysis["target_fix_results"]), 3)
        self.assertEqual(len(self.analysis["case_fix_results"]), 3)
        self.assertTrue(all(row["passed"] for row in self.analysis["target_fix_results"]))
        self.assertTrue(all(row["passed"] for row in self.analysis["case_fix_results"]))
        self.assertEqual(
            {row["relation_type"] for row in self.analysis["target_fix_results"]},
            {
                "embedded_speech_content",
                "third_party_habitual_description",
                "past_experiential_description",
            },
        )

    def test_separate_model_and_compiler_residuals_were_not_hidden(self):
        state_failures = {
            (row["case_id"], row["target_id"])
            for row in self.analysis["candidate_state"]["failure_rows"]
        }
        self.assertEqual(
            state_failures,
            {
                ("v58h_tatoeba_10784018", "gaze.left"),
                ("v58h_tatoeba_10784018", "gaze.right"),
            },
        )
        self.assertEqual(
            self.analysis["candidate_compiler"]["failure_case_ids"],
            ["v58h_tatoeba_201634"],
        )

    def test_pass_authorizes_only_an_independent_holdout(self):
        expected = "authorize_independent_v59_event_role_holdout"
        self.assertTrue(self.analysis["gates"]["passed"])
        self.assertEqual(self.analysis["gates"]["failed_checks"], [])
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
