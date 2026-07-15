#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CLOSURE_PATH = ROOT / "configs" / "precise_target_mentions_v52_holdout_closure.json"
ANALYSIS_PATH = ROOT / "reports" / "precise_target_mentions_v52_holdout_analysis.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PreciseTargetMentionsV52HoldoutResultTests(unittest.TestCase):
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

    def test_frozen_holdout_completed_after_preregistration_commit(self):
        scope = self.closure["frozen_scope"]
        self.assertEqual(scope["case_count"], 64)
        self.assertEqual(scope["judgment_count"], 170)
        self.assertTrue(scope["construction_gate_passed"])
        self.assertTrue(scope["representation_gate_passed"])
        self.assertFalse(scope["paid_api"])

    def test_candidate_lost_calls_and_added_false_action(self):
        delta = self.closure["overall_result"]["candidate_delta"]
        self.assertEqual(delta["commitment_correct_count"], -1)
        self.assertEqual(delta["compiled_call_exact_count"], -2)
        self.assertEqual(delta["false_action_count"], 1)
        self.assertEqual(delta["semantic_regression_count"], 4)
        self.assertEqual(delta["call_regression_count"], 2)

    def test_prespecified_targeted_family_regressed(self):
        targeted = self.closure["subgroup_result"][
            "controlled_cross_target_precision"
        ]
        self.assertEqual(targeted["control_compiled_call_exact"], "4/5")
        self.assertEqual(targeted["candidate_compiled_call_exact"], "3/5")
        self.assertEqual(targeted["candidate_call_delta"], -1)

    def test_analysis_rejects_v52_and_authorizes_nothing(self):
        self.assertFalse(self.analysis["fresh_holdout_gate_passed"])
        self.assertEqual(
            self.analysis["decision"],
            "reject_v52_due_to_fresh_regression_preregister_state_machine",
        )
        self.assertFalse(self.analysis["fresh_project_generalization_claim_authorized"])
        self.assertFalse(self.analysis["shadow_integration_design_authorized"])
        self.assertFalse(self.analysis["runtime_change_authorized"])
        self.assertFalse(self.analysis["physical_vrm_execution_enabled"])

    def test_holdout_cannot_be_tuned_after_failure(self):
        next_architecture = self.closure["next_architecture"]
        self.assertFalse(next_architecture["frozen_holdout_may_be_used_for_tuning"])
        self.assertTrue(next_architecture["new_independent_holdout_required"])


if __name__ == "__main__":
    unittest.main()
