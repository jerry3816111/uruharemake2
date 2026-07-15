#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path

from run_relation_safety_state_v58_holdout import CANDIDATE, CONTROL


ROOT = Path(__file__).resolve().parent
CLOSURE_PATH = ROOT / "configs" / "relation_safety_state_v58_holdout_closure.json"
RAW_PATH = ROOT / "reports" / "relation_safety_state_v58_holdout_raw.json"
ANALYSIS_PATH = ROOT / "reports" / "relation_safety_state_v58_holdout_analysis.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RelationSafetyStateV58HoldoutResultTests(unittest.TestCase):
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

    def test_run_started_from_merged_frozen_commit_and_used_local_model(self):
        self.assertEqual(self.raw["runner_commit"], self.closure["frozen_run_commit"])
        self.assertEqual(self.raw["conditions"], [CONTROL, CANDIDATE])
        self.assertEqual(len(self.raw["target_rows"]), 87)
        self.assertEqual(len(self.raw["case_rows"]), 64)
        self.assertEqual(self.raw["model_calls_made"], 87)
        self.assertFalse(self.raw["paid_api_used"])
        self.assertEqual(self.raw["physical_vrm_actions_executed"], 0)

    def test_positive_matched_effect_is_preserved_without_hiding_rejection(self):
        comparison = self.analysis["matched_comparison"]
        relation = self.analysis["relation_generalization"]
        candidate = self.analysis["candidate_compiler"]
        self.assertEqual(comparison["state_correct_count_delta"], 35)
        self.assertEqual(comparison["ordered_exact_count_delta"], 18)
        self.assertEqual(comparison["state_regression_count"], 0)
        self.assertEqual(comparison["case_regression_count"], 0)
        self.assertEqual(relation["expected_relation_coverage"], 1.0)
        self.assertEqual(relation["contrast_false_positive_target_count"], 0)
        self.assertEqual(candidate["source_groups"]["controlled_compositional"]["accuracy"], 1.0)
        self.assertFalse(self.analysis["gates"]["passed"])

    def test_three_false_actions_are_deterministic_state_not_model_size(self):
        expected_ids = {
            "v58h_tatoeba_120769",
            "v58h_tatoeba_13065884",
            "v58h_tatoeba_13070403",
        }
        self.assertEqual(
            set(self.analysis["candidate_compiler"]["false_action_case_ids"]),
            expected_ids,
        )
        rows = [
            row for row in self.raw["target_rows"] if row["case_id"] in expected_ids
        ]
        self.assertEqual(len(rows), 3)
        for row in rows:
            self.assertEqual(row["candidate_selection_source"], "deterministic_state_machine")
            self.assertEqual(
                row["candidate_state"]["resolution_rule"],
                "relation_bound_local_directive",
            )
            self.assertNotEqual(row["shared_fallback_commitment"], "requested")

    def test_compiler_only_miss_is_kept_separate(self):
        row = next(
            row
            for row in self.raw["target_rows"]
            if row["case_id"] == "v58h_tatoeba_201634"
        )
        self.assertEqual(row["shared_fallback_commitment"], "requested")
        self.assertEqual(row["candidate_commitment"], "requested")
        case = next(
            row
            for row in self.raw["case_rows"]
            if row["case_id"] == "v58h_tatoeba_201634"
        )
        blocked = case["candidate_compilation"]["blocked_frames"]
        self.assertEqual(blocked[0]["reasons"], ["unresolved_model_only_request"])

    def test_failed_candidate_authorizes_no_deployment_or_broad_claim(self):
        expected = "reject_v58_holdout_advancement_and_attribute_failure"
        self.assertEqual(self.analysis["decision"], expected)
        self.assertEqual(self.closure["decision"], expected)
        self.assertEqual(
            self.analysis["gates"]["failed_checks"],
            [
                "state_commitment_accuracy",
                "state_requested_precision",
                "compiler_no_action_specificity",
                "compiler_false_actions",
            ],
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
