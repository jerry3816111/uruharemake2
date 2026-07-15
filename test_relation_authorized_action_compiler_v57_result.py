#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CLOSURE_PATH = ROOT / "configs" / "relation_authorized_action_compiler_v57_closure.json"
RAW_PATH = ROOT / "reports" / "relation_authorized_action_compiler_v57_development_raw.json"
ANALYSIS_PATH = ROOT / "reports" / "relation_authorized_action_compiler_v57_development_analysis.json"
CONTROL = "v56_with_frozen_v48_compiler_control"
CANDIDATE = "v56_with_relation_authorized_v57_compiler_candidate"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RelationAuthorizedActionCompilerV57ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.closure = json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))
        cls.raw = json.loads(RAW_PATH.read_text(encoding="utf-8"))
        cls.analysis = json.loads(ANALYSIS_PATH.read_text(encoding="utf-8"))

    def test_every_result_artifact_is_hash_bound(self):
        for key, expected in self.closure["bound_artifacts"].items():
            if not key.endswith("_sha256"):
                continue
            path = ROOT / self.closure["bound_artifacts"][
                key.removesuffix("_sha256")
            ]
            self.assertEqual(_sha256(path), expected, path)

    def test_replay_used_merged_implementation_and_no_model(self):
        freeze = self.closure["implementation_freeze"]
        self.assertEqual(self.raw["runner_commit"], freeze["runner_commit"])
        self.assertTrue(freeze["implementation_merged_before_replay"])
        self.assertEqual(len(self.raw["case_rows"]), 64)
        self.assertEqual(self.raw["model_calls"], 0)
        self.assertFalse(self.raw["paid_api_used"])

    def test_candidate_fixes_all_calls_without_regression(self):
        control = self.analysis["conditions"][CONTROL]
        candidate = self.analysis["conditions"][CANDIDATE]
        comparison = self.analysis["comparison"]
        self.assertEqual(control["exact_call_count"], 60)
        self.assertEqual(candidate["exact_call_count"], 64)
        self.assertEqual(candidate["false_action_count"], 0)
        self.assertEqual(candidate["required_action_recall"], 1.0)
        self.assertEqual(comparison["fixed_call_count"], 4)
        self.assertEqual(comparison["call_regression_count"], 0)

    def test_every_accepted_call_is_grounded_and_authorized(self):
        candidate = self.analysis["conditions"][CANDIDATE]
        self.assertEqual(candidate["accepted_call_anchor_coverage"], 1.0)
        self.assertEqual(candidate["authorization_provenance_coverage"], 1.0)
        self.assertEqual(candidate["ungrounded_execution_count"], 0)
        self.assertEqual(candidate["unresolved_model_only_execution_count"], 0)
        self.assertEqual(candidate["commitment_mutation_count"], 0)

    def test_all_prespecified_gates_pass(self):
        self.assertTrue(self.analysis["gate"]["passed"])
        self.assertEqual(self.analysis["gate"]["failed_checks"], [])
        self.assertEqual(
            self.analysis["decision"],
            "authorize_independent_v57_compiler_holdout",
        )

    def test_only_new_holdout_not_runtime_is_authorized(self):
        self.assertFalse(self.analysis["fresh_holdout_claim_authorized"])
        self.assertFalse(self.analysis["runtime_change_authorized"])
        self.assertFalse(self.analysis["shadow_integration_authorized"])
        self.assertFalse(self.analysis["physical_vrm_execution_enabled"])
        self.assertFalse(self.analysis["broad_human_likeness_claim_authorized"])
        self.assertTrue(
            self.closure["next_experiment"]["fresh_holdout_required_before_shadow"]
        )


if __name__ == "__main__":
    unittest.main()
