#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path

from run_relation_authorized_action_compiler_v57_holdout import CANDIDATE, CONTROL


ROOT = Path(__file__).resolve().parent
CLOSURE_PATH = ROOT / "configs" / "relation_authorized_action_compiler_v57_holdout_closure.json"
RAW_PATH = ROOT / "reports" / "relation_authorized_action_compiler_v57_holdout_raw.json"
ANALYSIS_PATH = ROOT / "reports" / "relation_authorized_action_compiler_v57_holdout_analysis.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RelationAuthorizedCompilerV57HoldoutResultTests(unittest.TestCase):
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

    def test_run_started_from_merged_frozen_commit(self):
        self.assertEqual(self.raw["runner_commit"], self.closure["frozen_run_commit"])
        self.assertEqual(len(self.raw["target_rows"]), 85)
        self.assertEqual(len(self.raw["case_rows"]), 64)
        self.assertEqual(self.raw["model_calls_made"], 85)
        self.assertFalse(self.raw["paid_api_used"])

    def test_compilers_share_state_and_make_no_model_calls(self):
        self.assertEqual(self.raw["conditions"], [CONTROL, CANDIDATE])
        self.assertEqual(len(self.raw["target_rows"]), self.raw["model_calls_made"])
        for row in self.raw["case_rows"]:
            self.assertIn("frozen_v56_commitments", row)
            self.assertIn("control_compilation", row)
            self.assertIn("candidate_compilation", row)
        accounting = self.closure["execution_accounting"]
        self.assertFalse(accounting["compilers_called_model"])
        self.assertEqual(accounting["physical_vrm_actions_executed"], 0)

    def test_positive_gain_is_preserved_without_hiding_rejection(self):
        matched = self.analysis["matched_comparison"]
        control = self.analysis["conditions"][CONTROL]
        candidate = self.analysis["conditions"][CANDIDATE]
        self.assertEqual(control["ordered_exact_count"], 50)
        self.assertEqual(candidate["ordered_exact_count"], 54)
        self.assertEqual(matched["ordered_exact_count_delta"], 4)
        self.assertEqual(matched["fix_count"], 9)
        self.assertEqual(matched["regression_count"], 5)
        self.assertEqual(candidate["false_action_case_count"], 4)
        self.assertFalse(self.analysis["gates"]["candidate_compiler"]["passed"])
        self.assertFalse(self.analysis["gates"]["matched_comparison"]["passed"])

    def test_safety_and_coverage_failures_are_reported_separately(self):
        rejection = self.closure["rejection_evidence"]
        self.assertEqual(len(rejection["false_action_case_ids"]), 4)
        self.assertEqual(len(rejection["safe_fail_closed_action_miss_case_ids"]), 4)
        self.assertEqual(rejection["compiler_only_failure_case_count"], 3)
        self.assertIn("v57h_alternative_01", rejection["false_action_case_ids"])
        self.assertIn(
            "v57h_tatoeba_197186",
            rejection["safe_fail_closed_action_miss_case_ids"],
        )

    def test_state_prerequisite_failed_and_is_not_blurred_into_compiler(self):
        state = self.analysis["state_prerequisite"]
        self.assertEqual(state["correct_count"], 73)
        self.assertEqual(state["target_count"], 85)
        self.assertAlmostEqual(state["commitment_accuracy"], 73 / 85)
        self.assertFalse(self.analysis["gates"]["state_prerequisite"]["passed"])
        attribution = self.analysis["failure_attribution"]
        self.assertEqual(attribution["semantic_state_failure_count"], 10)
        self.assertEqual(attribution["compiler_only_failure_count"], 3)

    def test_failed_candidate_authorizes_no_deployment_or_broad_claim(self):
        self.assertEqual(
            self.analysis["decision"],
            "reject_v57_and_preregister_relation_or_authorization_repair",
        )
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
