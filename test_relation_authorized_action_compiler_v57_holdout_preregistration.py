#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path

from audit_relation_authorized_action_compiler_v57_holdout import audit
from run_relation_authorized_action_compiler_v57_holdout import CONDITIONS


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "relation_authorized_action_compiler_v57_holdout_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "relation_authorized_action_compiler_v57_holdout.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RelationAuthorizedCompilerV57HoldoutPreregistrationTests(unittest.TestCase):
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

    def test_dataset_and_construction_audit_are_frozen(self):
        frozen = self.config["frozen_inputs"]
        self.assertEqual(frozen["case_count"], 64)
        self.assertEqual(frozen["external_exact_case_count"], 32)
        self.assertEqual(frozen["controlled_compositional_case_count"], 32)
        self.assertEqual(frozen["controlled_family_count"], 8)
        self.assertEqual(frozen["grounded_target_count"], 85)
        self.assertEqual(frozen["requested_target_count"], 39)
        self.assertEqual(frozen["not_requested_target_count"], 46)
        self.assertEqual(frozen["action_case_count"], 29)
        self.assertEqual(frozen["no_action_case_count"], 35)
        self.assertEqual(self.audit["target_count"], 85)
        self.assertTrue(self.audit["passed"], self.audit["failed_checks"])

    def test_two_compilers_share_one_fresh_state_and_fallback(self):
        self.assertEqual(tuple(self.config["conditions"]), CONDITIONS)
        self.assertEqual(self.config["model_call_budget"], 85)
        policy = self.config["model_usage_policy"]
        self.assertIn("exactly once per grounded target", policy)
        self.assertIn("frozen and shared by V48 and V57", policy)
        isolation = self.config["causal_isolation"]
        self.assertIn("Replace only", isolation["tested_variable"])
        self.assertFalse(isolation["gold_fields_passed_to_compilers"])
        self.assertFalse(isolation["memory_enabled"])
        self.assertFalse(isolation["rightbrain_generation_enabled"])
        self.assertFalse(isolation["vtuber_identity_prompt_enabled"])

    def test_external_and_controlled_evidence_are_not_conflated(self):
        construction = self.dataset["construction"]
        self.assertFalse(construction["external_exact_model_generation_used"])
        self.assertTrue(construction["controlled_model_assistance_used"])
        self.assertFalse(construction["evaluation_model_inference_used"])
        self.assertFalse(construction["base_model_pretraining_exclusion_guaranteed"])
        self.assertIn("not official corpus items", self.config["evidence_boundary"])

    def test_order_and_safety_are_both_required(self):
        gates = self.config["candidate_compiler_gates"]
        self.assertGreaterEqual(gates["action_ordered_exact_accuracy_at_least"], 0.85)
        self.assertGreaterEqual(gates["required_call_recall_at_least"], 0.9)
        self.assertGreaterEqual(gates["no_action_specificity_at_least"], 0.98)
        self.assertEqual(gates["false_action_case_count"], 0)
        self.assertTrue(self.config["causal_isolation"]["ordered_call_accuracy_required"])
        self.assertTrue(
            self.config["causal_isolation"][
                "safe_abstention_reported_separately_from_task_success"
            ]
        )

    def test_dataset_contains_ordered_plans_and_withhold_cases(self):
        ordered = [
            case for case in self.dataset["cases"] if "ordered_plan" in case["evaluation_tags"]
        ]
        withheld = [
            case
            for case in self.dataset["cases"]
            if case["expected_execution_policy"] == "withhold_action"
        ]
        self.assertGreaterEqual(len(ordered), 8)
        self.assertEqual(len(withheld), 35)
        self.assertTrue(all(len(case["expected_calls"]) >= 2 for case in ordered))
        self.assertTrue(all(not case["expected_calls"] for case in withheld))

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
