#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "relation_safety_state_v58_preregistration.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RelationSafetyStateV58PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def test_every_consumed_input_is_hash_bound(self):
        frozen = self.config["frozen_inputs"]
        for key, expected in frozen.items():
            if not key.endswith("_sha256"):
                continue
            path_key = key.removesuffix("_sha256")
            self.assertIn(path_key, frozen)
            self.assertEqual(_sha256(ROOT / frozen[path_key]), expected, path_key)

    def test_one_state_variable_and_zero_model_calls(self):
        isolation = self.config["causal_isolation"]
        self.assertIn("Replace only V56 state resolution", isolation["tested_variable"])
        self.assertEqual(self.config["model_calls_authorized"], 0)
        self.assertFalse(isolation["memory_enabled"])
        self.assertFalse(isolation["rightbrain_generation_enabled"])
        self.assertFalse(isolation["vtuber_identity_prompt_enabled"])
        self.assertFalse(isolation["runtime_integration_enabled"])
        self.assertFalse(isolation["physical_actuation_enabled"])

    def test_contract_has_three_general_relations_and_no_case_rules(self):
        contract = self.config["candidate_contract"]
        self.assertEqual(
            set(contract["relation_types"]),
            {
                "exclusive_alternative",
                "deferred_preference",
                "past_benefactive_description",
            },
        )
        self.assertTrue(contract["sentence_id_or_case_id_rules_forbidden"])
        self.assertFalse(contract["compiler_mutation_authorized"])
        self.assertFalse(contract["fallback_model_mutation_authorized"])
        self.assertIn("てから", contract["sequence_exclusion"])

    def test_exact_six_target_and_four_case_fixes_are_prespecified(self):
        targets = self.config["prespecified_target_fixes"]
        cases = self.config["prespecified_case_fixes"]
        self.assertEqual(len(targets), 6)
        self.assertEqual(len({(row["case_id"], row["target_id"]) for row in targets}), 6)
        self.assertEqual(len(cases), 4)
        self.assertEqual(len(set(cases)), 4)
        self.assertTrue(all(row["from"] == "requested" for row in targets))
        self.assertEqual(
            {row["relation_type"] for row in targets},
            {
                "exclusive_alternative",
                "deferred_preference",
                "past_benefactive_description",
            },
        )

    def test_gates_require_safety_gain_without_regression_or_extra_suppression(self):
        gates = self.config["development_gates"]
        self.assertEqual(gates["state_correct_count_at_least"], 79)
        self.assertEqual(gates["ordered_exact_count_at_least"], 58)
        self.assertEqual(gates["false_action_case_count"], 0)
        self.assertEqual(gates["no_action_specificity"], 1.0)
        self.assertGreaterEqual(gates["requested_precision_at_least"], 0.95)
        self.assertEqual(gates["state_regression_count"], 0)
        self.assertEqual(gates["call_regression_count"], 0)
        self.assertAlmostEqual(
            gates["required_call_recall_at_least"],
            self.config["frozen_inputs"]["baseline_required_call_recall_numerator"]
            / self.config["frozen_inputs"]["baseline_required_call_recall_denominator"],
        )

    def test_no_advancement_or_implementation_before_merge_is_authorized(self):
        for key in (
            "implementation_before_preregistration_merge_authorized",
            "post_run_tuning_authorized",
            "fresh_generalization_claim_authorized",
            "runtime_change_authorized",
            "shadow_integration_authorized",
            "physical_vrm_execution_enabled",
            "broad_human_likeness_claim_authorized",
        ):
            self.assertFalse(self.config[key], key)


if __name__ == "__main__":
    unittest.main()
