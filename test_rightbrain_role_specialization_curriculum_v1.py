import ast
import copy
import json
import unittest
from collections import Counter
from pathlib import Path

import build_rightbrain_role_specialization_curriculum_v1 as curriculum


ROOT = Path(__file__).resolve().parent


class RightBrainRoleSpecializationCurriculumV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preregistration = curriculum.load_json(curriculum.DEFAULT_PREREGISTRATION)
        cls.specs = curriculum.load_json(curriculum.DEFAULT_SPECS)
        cls.rows, cls.report = curriculum.build_report(cls.preregistration, cls.specs)

    def test_preregistration_was_frozen_before_builder(self):
        self.assertEqual(
            self.preregistration["status"],
            "frozen_before_curriculum_builder_implementation",
        )
        self.assertEqual(
            self.preregistration["authoring_parent_commit"],
            "0040248bfdf3a7bb80086893a8605599718f7ce1",
        )

    def test_previous_audit_authorized_only_curriculum_construction(self):
        frozen = self.report["frozen_input_validation"]
        self.assertTrue(frozen["passed"])
        self.assertTrue(frozen["previous_authorization_match"])
        self.assertEqual(
            frozen["previous_authorization"],
            "authorize_person_independent_role_specialization_curriculum_construction_only",
        )

    def test_curriculum_is_balanced_across_policy_context_and_memory(self):
        self.assertEqual(len(self.specs["cases"]), 20)
        self.assertEqual(len(self.rows), 80)
        self.assertTrue(self.report["balance"]["passed"])
        self.assertEqual(
            set(self.report["balance"]["provider_counts"].values()),
            {40},
        )
        self.assertEqual(
            set(self.report["balance"]["context_counts"].values()),
            {16},
        )
        self.assertEqual(
            set(self.report["balance"]["memory_mode_counts"].values()),
            {20},
        )

    def test_only_persona_policy_changes_between_matched_payloads(self):
        by_case = {}
        for spec in self.specs["cases"]:
            logic = curriculum.logic_from_spec(spec)
            by_case[spec["case_id"]] = {}
            for provider_id in curriculum.PROVIDERS:
                payload, instruction = curriculum.build_payload(
                    logic,
                    spec["context"],
                    provider_id,
                )
                by_case[spec["case_id"]][provider_id] = (payload, instruction)
        for case_id, conditions in by_case.items():
            target, target_instruction = conditions[curriculum.persona_policy.TARGET_PROVIDER]
            neutral, neutral_instruction = conditions[curriculum.persona_policy.NEUTRAL_PROVIDER]
            target = copy.deepcopy(target)
            neutral = copy.deepcopy(neutral)
            target_persona = target["context"].pop("persona_expression_brief")
            neutral_persona = neutral["context"].pop("persona_expression_brief")
            self.assertNotEqual(target_persona, neutral_persona, case_id)
            self.assertEqual(target, neutral, case_id)
            self.assertEqual(target_instruction, neutral_instruction, case_id)

    def test_current_joint_contract_and_policy_coverage_are_complete(self):
        quality = self.report["quality"]
        self.assertTrue(quality["passed"])
        for key in (
            "joint_contract_coverage",
            "current_persona_policy_path_coverage",
            "current_persona_policy_value_coverage",
            "exact_current_system_instruction_coverage",
            "semantic_contract_pass_rate",
            "forbidden_marker_pass_rate",
            "maximum_length_pass_rate",
            "casual_japanese_surface_pass_rate",
            "memory_policy_pass_rate",
            "runtime_candidate_gate_pass_rate",
            "provider_pair_output_difference_rate",
        ):
            self.assertEqual(quality["rates"][key], 1.0, key)
        self.assertEqual(quality["counts"]["unique_normalized_target_count"], 80)
        self.assertEqual(quality["counts"]["retired_no_first_person_rule_row_count"], 0)

    def test_training_rows_are_examples_not_runtime_reply_lookup(self):
        self.assertEqual(
            set(Counter(row["source_id"] for row in self.rows).values()),
            {4},
        )
        for row in self.rows:
            self.assertTrue(row["provenance"]["synthetic"])
            self.assertTrue(row["provenance"]["source_independent"])
            self.assertFalse(row["provenance"]["contains_target_utterance"])
            self.assertFalse(row["provenance"]["contains_benchmark_item"])
            self.assertFalse(row["provenance"]["runtime_fixed_reply"])
            self.assertFalse(row["provenance"]["training_authorized"])
            self.assertEqual(
                [message["role"] for message in row["messages"]],
                ["system", "user", "assistant"],
            )

    def test_development_training_and_identity_separation_is_zero_overlap(self):
        separation = self.report["separation"]
        self.assertTrue(separation["passed"])
        self.assertTrue(all(value == 0 for value in separation["checks"].values()))
        self.assertTrue(all(separation["provenance_checks"].values()))

    def test_builder_reads_no_persona_transcript_and_calls_no_model_or_trainer(self):
        self.assertTrue(self.report["builder_source_boundary"]["passed"])
        tree = ast.parse(Path(curriculum.__file__).read_text(encoding="utf-8"))
        called_attributes = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        for forbidden in ("chat", "generate", "fit", "backward", "train"):
            self.assertNotIn(forbidden, called_attributes)

    def test_result_authorizes_only_preregistering_a_matched_training_pilot(self):
        decision = self.report["decision"]
        self.assertEqual(
            decision["outcome"],
            "authorize_matched_local_training_pilot_preregistration_only",
        )
        self.assertTrue(decision["authorize_training_pilot_preregistration"])
        self.assertFalse(decision["authorize_model_training"])
        self.assertFalse(decision["authorize_production_change"])
        self.assertFalse(decision["authorize_persona_similarity_claim"])
        self.assertFalse(decision["authorize_generalization_claim"])
        self.assertFalse(decision["causal_claim_supported"])


if __name__ == "__main__":
    unittest.main()
