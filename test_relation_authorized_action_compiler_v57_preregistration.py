#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "relation_authorized_action_compiler_v57_preregistration.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RelationAuthorizedActionCompilerV57PreregistrationTests(unittest.TestCase):
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

    def test_one_variable_and_zero_model_calls(self):
        self.assertEqual(
            self.config["conditions"],
            [
                "v56_with_frozen_v48_compiler_control",
                "v56_with_relation_authorized_v57_compiler_candidate",
            ],
        )
        self.assertFalse(self.config["model_calls_authorized"])
        tested = self.config["tested_variable"]
        self.assertIn("Replace only V48 call authorization", tested)
        self.assertIn("Reuse frozen V56 commitments", tested)

    def test_contract_separates_semantics_from_compilation(self):
        contract = self.config["authorization_contract"]
        self.assertFalse(contract["commitment_mutation_allowed"])
        self.assertFalse(contract["gold_fields_visible_to_compiler"])
        self.assertIn("local_directive", contract["primary_authorization_relations"])
        self.assertIn("shared_directive", contract["primary_authorization_relations"])
        self.assertIn("execution_prohibition", contract["blocking_relations"])
        self.assertIn("fail closed", contract["unresolved_model_request_policy"])

    def test_four_failures_and_regression_guards_are_prespecified(self):
        repairs = self.config["prespecified_failure_repairs"]
        self.assertEqual(len(repairs), 4)
        self.assertEqual(
            {row["case_id"] for row in repairs},
            {
                "v56h_tatoeba_125613",
                "v56h_idle_01",
                "v56h_idle_04",
                "v56h_description_02",
            },
        )
        guards = self.config["prespecified_regression_guards"]
        self.assertIn("v56h_tatoeba_9177039", {row.get("case_id") for row in guards})

    def test_development_gate_requires_perfect_calls_without_semantic_mutation(self):
        gates = self.config["development_gates"]
        self.assertEqual(gates["frozen_commitment_correct_count"], 80)
        self.assertEqual(gates["frozen_commitment_mutation_count"], 0)
        self.assertEqual(gates["candidate_exact_call_count"], 64)
        self.assertEqual(gates["candidate_exact_call_accuracy"], 1.0)
        self.assertEqual(gates["candidate_false_action_count"], 0)
        self.assertEqual(gates["targeted_fixed_call_count"], 4)
        self.assertEqual(gates["call_regression_count"], 0)
        self.assertEqual(gates["unresolved_model_only_execution_count"], 0)

    def test_no_implementation_or_advancement_is_authorized(self):
        self.assertFalse(self.config["implementation_started"])
        for key in (
            "fresh_holdout_claim_authorized",
            "runtime_change_authorized",
            "shadow_integration_authorized",
            "physical_vrm_execution_enabled",
            "broad_human_likeness_claim_authorized",
        ):
            self.assertFalse(self.config[key], key)


if __name__ == "__main__":
    unittest.main()
