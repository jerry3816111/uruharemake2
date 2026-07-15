#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path

from audit_relation_bound_event_graph_v56_holdout import audit
from run_relation_bound_event_graph_v56_holdout import CONDITIONS


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "relation_bound_event_graph_v56_holdout_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "relation_bound_event_graph_v56_holdout.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RelationBoundEventGraphV56HoldoutPreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        cls.dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
        cls.audit = audit(cls.dataset, cls.config["target_mention_patterns"])

    def test_every_frozen_file_matches_its_hash(self):
        frozen = self.config["frozen_inputs"]
        for key, expected in frozen.items():
            if not key.endswith("_sha256"):
                continue
            path_key = key.removesuffix("_sha256")
            self.assertIn(path_key, frozen)
            self.assertEqual(_sha256(ROOT / frozen[path_key]), expected, path_key)

    def test_dataset_counts_and_model_budget_are_frozen(self):
        frozen = self.config["frozen_inputs"]
        self.assertEqual(frozen["case_count"], 64)
        self.assertEqual(frozen["external_exact_case_count"], 32)
        self.assertEqual(frozen["controlled_compositional_case_count"], 32)
        self.assertEqual(frozen["controlled_relation_family_count"], 8)
        self.assertEqual(frozen["grounded_target_count"], 81)
        self.assertEqual(frozen["requested_target_count"], 34)
        self.assertEqual(frozen["not_requested_target_count"], 47)
        self.assertEqual(self.config["model_call_budget"], 81)
        self.assertEqual(self.audit["target_count"], 81)
        self.assertTrue(self.audit["passed"], self.audit["failed_checks"])

    def test_exact_four_conditions_share_one_fallback(self):
        self.assertEqual(tuple(self.config["conditions"]), CONDITIONS)
        policy = self.config["model_usage_policy"]
        self.assertIn("exactly once per grounded target", policy)
        self.assertIn("reuse that identical output", policy)
        self.assertIn("neither architecture may make a second model call", policy)

    def test_external_and_controlled_evidence_are_not_conflated(self):
        construction = self.dataset["construction"]
        isolation = self.config["causal_isolation"]
        self.assertFalse(construction["external_exact_model_generation_used"])
        self.assertTrue(construction["controlled_model_assistance_used"])
        self.assertFalse(construction["evaluation_model_inference_used"])
        self.assertFalse(construction["base_model_pretraining_exclusion_guaranteed"])
        self.assertTrue(isolation["external_and_controlled_results_reported_separately"])
        self.assertIn("not official corpus items", self.config["evidence_boundary"])

    def test_only_relation_representation_changes(self):
        isolation = self.config["causal_isolation"]
        self.assertIn("V54", isolation["tested_variable"])
        self.assertIn("V56", isolation["tested_variable"])
        self.assertIn("one shared fallback result per grounded target", isolation["held_constant"])
        self.assertFalse(isolation["memory_enabled"])
        self.assertFalse(isolation["rightbrain_generation_enabled"])
        self.assertFalse(isolation["runtime_integration_enabled"])
        self.assertFalse(isolation["physical_actuation_enabled"])

    def test_gates_require_quality_safety_and_no_matched_regression(self):
        state = self.config["state_component_gates"]
        matched = self.config["matched_comparison_gates"]
        end_to_end = self.config["end_to_end_gates"]
        self.assertGreaterEqual(state["hybrid_commitment_accuracy_at_least"], 0.95)
        self.assertGreaterEqual(state["requested_commitment_precision_at_least"], 0.95)
        self.assertGreaterEqual(state["requested_commitment_recall_at_least"], 0.95)
        self.assertEqual(matched["semantic_regression_count_at_most"], 0)
        self.assertEqual(matched["false_action_count_delta_at_most"], 0)
        self.assertEqual(end_to_end["false_action_count"], 0)
        self.assertEqual(end_to_end["negation_violation_count"], 0)
        self.assertEqual(end_to_end["ungrounded_execution_count"], 0)
        self.assertEqual(end_to_end["call_regression_count_at_most"], 0)

    def test_no_advancement_is_authorized_before_results(self):
        for key in (
            "post_run_tuning_authorized",
            "fresh_holdout_claim_authorized",
            "runtime_change_authorized",
            "shadow_integration_authorized",
            "physical_vrm_execution_enabled",
            "broad_human_likeness_claim_authorized",
        ):
            self.assertFalse(self.config[key], key)


if __name__ == "__main__":
    unittest.main()
