#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "event_role_governor_v59_preregistration.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class EventRoleGovernorV59PreregistrationTests(unittest.TestCase):
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
        self.assertIn("Add only the V59 event-owner", isolation["tested_variable"])
        self.assertEqual(self.config["model_calls_authorized"], 0)
        self.assertFalse(isolation["memory_enabled"])
        self.assertFalse(isolation["rightbrain_generation_enabled"])
        self.assertFalse(isolation["vtuber_identity_prompt_enabled"])
        self.assertFalse(isolation["physical_actuation_enabled"])

    def test_contract_models_owner_governor_and_time_without_answers(self):
        contract = self.config["candidate_contract"]
        self.assertEqual(
            set(contract["graph_slots"]),
            {"event_owner", "directive_governor", "event_time"},
        )
        self.assertEqual(
            set(contract["nonexecution_relations"]),
            {
                "embedded_speech_content",
                "third_party_habitual_description",
                "past_experiential_description",
            },
        )
        self.assertFalse(contract["answer_fields_visible"])
        self.assertTrue(contract["sentence_id_or_case_id_rules_forbidden"])
        self.assertTrue(contract["gold_or_expected_call_fields_forbidden"])
        self.assertFalse(contract["compiler_mutation_authorized"])
        self.assertFalse(contract["fallback_model_mutation_authorized"])

    def test_exact_three_target_and_case_fixes_are_prespecified(self):
        target_fixes = self.config["prespecified_target_fixes"]
        self.assertEqual(len(target_fixes), 3)
        self.assertEqual(
            {row["case_id"] for row in target_fixes},
            set(self.config["prespecified_case_fixes"]),
        )
        self.assertEqual({row["from"] for row in target_fixes}, {"requested"})
        self.assertEqual({row["to"] for row in target_fixes}, {"mentioned"})

    def test_gates_require_exact_safety_gain_without_coverage_loss(self):
        gates = self.config["development_gates"]
        self.assertGreaterEqual(gates["state_correct_count_at_least"], 85)
        self.assertGreaterEqual(gates["ordered_exact_count_at_least"], 63)
        self.assertEqual(gates["false_action_case_count"], 0)
        self.assertEqual(gates["no_action_specificity"], 1.0)
        self.assertEqual(gates["requested_precision"], 1.0)
        self.assertGreaterEqual(gates["required_call_recall_at_least"], 16 / 17)
        self.assertEqual(gates["state_regression_count"], 0)
        self.assertEqual(gates["call_regression_count"], 0)
        self.assertEqual(gates["contrast_regression_count"], 0)

    def test_known_compiler_and_model_residuals_remain_separate(self):
        protected = self.config["protected_nonfixes"]
        self.assertEqual(
            protected["known_compiler_only_miss"], "v58h_tatoeba_201634"
        )
        self.assertEqual(
            protected["known_shared_fallback_label_error_case"],
            "v58h_tatoeba_10784018",
        )

    def test_no_implementation_or_advancement_is_authorized_before_merge(self):
        self.assertFalse((ROOT / self.config["candidate_contract"]["module"]).exists())
        for key in (
            "implementation_before_preregistration_merge_authorized",
            "post_run_tuning_authorized",
            "fresh_generalization_claim_authorized",
            "runtime_change_authorized",
            "shadow_integration_authorized",
            "physical_vrm_execution_enabled",
            "complete_rightbrain_claim_authorized",
            "broad_human_likeness_claim_authorized",
        ):
            self.assertFalse(self.config[key], key)


if __name__ == "__main__":
    unittest.main()
