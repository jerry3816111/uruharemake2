#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CLOSURE_PATH = ROOT / "configs" / "relation_bound_event_graph_v56_holdout_closure.json"
RAW_PATH = ROOT / "reports" / "relation_bound_event_graph_v56_holdout_raw.json"
ANALYSIS_PATH = ROOT / "reports" / "relation_bound_event_graph_v56_holdout_analysis.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RelationBoundEventGraphV56HoldoutResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.closure = json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))
        cls.raw = json.loads(RAW_PATH.read_text(encoding="utf-8"))
        cls.analysis = json.loads(ANALYSIS_PATH.read_text(encoding="utf-8"))

    def test_result_artifacts_are_hash_bound(self):
        bound = self.closure["bound_artifacts"]
        for key, expected in bound.items():
            if not key.endswith("_sha256"):
                continue
            path = ROOT / bound[key.removesuffix("_sha256")]
            self.assertEqual(_sha256(path), expected, path)

    def test_frozen_commit_precedes_complete_local_run(self):
        scope = self.closure["frozen_scope"]
        self.assertEqual(self.raw["runner_commit"], self.closure["freeze_proof"]["runner_commit"])
        self.assertIsNotNone(self.raw["completed_at"])
        self.assertEqual(len(self.raw["target_rows"]), 81)
        self.assertEqual(self.raw["model_calls_made"], 81)
        self.assertEqual(scope["model_calls"], 81)
        self.assertFalse(self.raw["paid_api_used"])
        self.assertTrue(scope["shared_fallback_reused_by_v54_and_v56"])

    def test_v56_generalizes_over_matched_v54_without_regression(self):
        comparison = self.analysis["v56_vs_v54_matched"]
        self.assertEqual(comparison["commitment_correct_count_delta"], 7)
        self.assertEqual(comparison["compiled_call_exact_count_delta"], 7)
        self.assertEqual(comparison["false_action_count_delta"], -6)
        self.assertEqual(comparison["semantic_regression_count"], 0)
        self.assertEqual(comparison["call_regression_count"], 0)

    def test_external_and_controlled_results_remain_separate(self):
        subgroups = self.analysis["subgroups"]
        external = subgroups["external_exact"][
            "v56_relation_graph_with_shared_fresh_v51_fallback"
        ]
        controlled = subgroups["controlled_compositional"][
            "v56_relation_graph_with_shared_fresh_v51_fallback"
        ]
        self.assertEqual(external["commitment_correct_count"], 37)
        self.assertEqual(external["target_count"], 37)
        self.assertEqual(controlled["commitment_correct_count"], 43)
        self.assertEqual(controlled["target_count"], 44)
        self.assertFalse(self.closure["frozen_scope"]["controlled_cases_official_corpus"])

    def test_remaining_failures_are_attributed_not_hidden(self):
        failures = self.analysis["failure_attribution"]
        self.assertEqual(len(failures["resolved_state_errors"]), 1)
        self.assertEqual(failures["fallback_model_errors"], [])
        self.assertEqual(len(failures["compiler_only_failure_case_ids"]), 3)
        self.assertEqual(
            failures["mixed_semantic_and_compiler_failure_case_ids"],
            ["v56h_description_02"],
        )

    def test_state_and_matched_pass_but_end_to_end_does_not(self):
        gates = self.analysis["gates"]
        self.assertTrue(gates["state"]["passed"])
        self.assertTrue(gates["matched"]["passed"])
        self.assertFalse(gates["end_to_end"]["passed"])
        self.assertEqual(gates["end_to_end"]["failed_checks"], ["false_action_count"])
        self.assertEqual(
            self.analysis["decision"],
            "freeze_v56_state_preregister_compiler_repair",
        )

    def test_no_runtime_or_broad_claim_is_authorized(self):
        self.assertFalse(self.analysis["runtime_change_authorized"])
        self.assertFalse(self.analysis["shadow_integration_authorized"])
        self.assertFalse(self.analysis["physical_vrm_execution_enabled"])
        self.assertFalse(self.analysis["broad_human_likeness_claim_authorized"])
        self.assertFalse(self.closure["runtime_change_authorized"])
        self.assertFalse(self.closure["shadow_integration_authorized"])
        self.assertFalse(self.closure["physical_vrm_execution_enabled"])


if __name__ == "__main__":
    unittest.main()
