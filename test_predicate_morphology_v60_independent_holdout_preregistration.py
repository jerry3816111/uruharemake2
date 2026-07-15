#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "predicate_morphology_v60_independent_holdout_preregistration.json"
)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PredicateMorphologyV60IndependentHoldoutPreregistrationTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def test_all_frozen_inputs_match_hashes(self):
        frozen = self.config["frozen_inputs"]
        for key, expected in frozen.items():
            if not key.endswith("_sha256"):
                continue
            path_key = key.removesuffix("_sha256")
            self.assertIn(path_key, frozen)
            self.assertEqual(_sha256(ROOT / frozen[path_key]), expected, path_key)

    def test_model_and_call_budget_are_local_and_fixed(self):
        model = self.config["fixed_model"]
        self.assertEqual(model["ollama_tag"], "qwen3.5:4b")
        self.assertEqual(
            model["digest"],
            "2a654d98e6fba55d452b7043684e9b57a947e393bbffa62485a7aac05ee4eefd",
        )
        self.assertEqual(model["temperature"], 0.0)
        self.assertFalse(model["thinking"])
        self.assertFalse(model["paid_api"])
        self.assertEqual(self.config["model_call_budget"], 120)

    def test_dataset_counts_and_action_balance_are_frozen(self):
        frozen = self.config["frozen_inputs"]
        self.assertEqual(frozen["case_count"], 117)
        self.assertEqual(frozen["grounded_target_count"], 120)
        self.assertEqual(frozen["external_exact_case_count"], 19)
        self.assertEqual(frozen["controlled_case_count"], 98)
        self.assertEqual(frozen["action_case_count"], 29)
        self.assertEqual(frozen["no_action_case_count"], 88)

    def test_all_seven_controlled_families_have_morphology_contracts(self):
        contracts = self.config["expected_morphology_by_family"]
        self.assertEqual(len(contracts), 7)
        for contract in contracts.values():
            self.assertEqual(
                set(contract),
                {
                    "predicate_force",
                    "event_aspect",
                    "event_owner",
                    "request_governor",
                    "direct_focus_request",
                    "relation_types",
                },
            )

    def test_absolute_and_matched_gates_cannot_hide_external_failures(self):
        state = self.config["candidate_state_gates"]
        compiler = self.config["candidate_compiler_gates"]
        matched = self.config["matched_comparison_gates"]
        self.assertGreaterEqual(state["external_target_accuracy_at_least"], 18 / 22)
        self.assertGreaterEqual(compiler["external_exact_accuracy_at_least"], 17 / 19)
        self.assertEqual(compiler["false_action_case_count"], 0)
        self.assertGreaterEqual(matched["state_correct_count_delta_at_least"], 14)
        self.assertEqual(matched["state_regression_count_at_most"], 0)
        self.assertEqual(matched["case_regression_count_at_most"], 0)
        self.assertLessEqual(matched["two_sided_exact_mcnemar_p_at_most"], 0.05)

    def test_no_early_inference_tuning_or_deployment_is_authorized(self):
        for key in (
            "holdout_inference_before_harness_freeze_authorized",
            "post_run_tuning_authorized",
            "post_run_threshold_change_authorized",
            "post_run_case_exclusion_authorized",
            "runtime_change_authorized",
            "shadow_integration_authorized",
            "physical_vrm_execution_enabled",
            "complete_rightbrain_claim_authorized",
            "broad_human_likeness_claim_authorized",
        ):
            self.assertFalse(self.config[key], key)


if __name__ == "__main__":
    unittest.main()
