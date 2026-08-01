import ast
import json
import unittest
from pathlib import Path

import audit_rightbrain_current_contract_curriculum_v1 as audit


ROOT = Path(__file__).resolve().parent


class RightBrainCurrentContractCurriculumAuditV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preregistration = json.loads(
            audit.DEFAULT_PREREGISTRATION.read_text(encoding="utf-8")
        )
        cls.report = audit.build_report()

    def test_preregistration_was_frozen_before_auditor(self):
        self.assertEqual(
            self.preregistration["status"], "frozen_before_auditor_implementation"
        )
        self.assertEqual(
            self.preregistration["authoring_parent_commit"],
            "8363a92168674bc8e20e47ae3042cd4ae81c399a",
        )

    def test_documented_contract_sources_reconstruct_exactly(self):
        source = self.report["source_reconstruction"]
        self.assertTrue(source["passed"])
        self.assertEqual(len(source["sources"]), 3)
        self.assertEqual(
            source["lineage"]["documented_contract_stage_rows"], 2086
        )
        self.assertFalse(
            source["lineage"]["pre_contract_ancestor_curriculum_reconstructable"]
        )

    def test_current_reference_is_generation_free_and_balanced(self):
        accounting = self.report["accounting"]
        self.assertEqual(accounting["current_reference_payload_count"], 10)
        self.assertEqual(accounting["actual_model_generation_call_count"], 0)
        self.assertEqual(accounting["model_training_run_count"], 0)
        self.assertEqual(accounting["production_memory_write_count"], 0)
        self.assertEqual(accounting["documented_contract_stage_exposure_count"], 2086)
        self.assertEqual(accounting["unique_underlying_training_unit_count"], 1061)

    def test_audit_detects_current_conditional_persona_contract_gap(self):
        coverage = self.report["coverage"]
        missing = set(coverage["persona_policy_path_coverage"]["missing_paths"])
        self.assertIn(
            "context.persona_expression_brief.conditional_context", missing
        )
        self.assertIn(
            "context.persona_expression_brief.expression_policy.operations[]", missing
        )
        self.assertIn(
            "context.persona_expression_brief.expression_policy.avoid[]", missing
        )
        self.assertEqual(coverage["current_joint_contract_row_count"], 10)
        self.assertEqual(coverage["documented_training_joint_contract_row_count"], 0)
        self.assertGreater(coverage["documented_static_persona_row_count"], 0)

    def test_instruction_contract_exposes_retired_first_person_rule(self):
        contract = self.report["instruction_contract"]
        self.assertFalse(contract["current_system_instruction_seen_in_training"])
        self.assertEqual(contract["training_rows_with_current_system_instruction"], 0)
        self.assertEqual(contract["rows_still_teaching_no_first_person_private"], 2086)
        self.assertIn(
            "no first person 私",
            contract["retired_training_only_reply_requirements"],
        )

    def test_audit_does_not_confuse_existing_failure_rows_with_success(self):
        failure = self.report["observed_failure_alignment"]
        self.assertEqual(failure["strict_valid_count"], 6)
        self.assertEqual(failure["generation_count"], 10)
        self.assertEqual(failure["covered_family_count"], 3)
        self.assertEqual(failure["observed_family_count"], 3)

    def test_development_cases_are_separated_from_training(self):
        separation = self.report["development_separation"]
        self.assertTrue(separation["passed"])
        self.assertTrue(
            all(
                value == 0
                for key, value in separation["checks"].items()
                if key.endswith("_count")
            )
        )

    def test_decision_is_construction_only(self):
        decision = self.report["decision"]
        self.assertTrue(decision["authorize_curriculum_construction"])
        self.assertFalse(decision["authorize_model_training"])
        self.assertFalse(decision["authorize_production_change"])
        self.assertFalse(decision["authorize_persona_similarity_claim"])
        self.assertFalse(decision["causal_claim_supported"])

    def test_auditor_has_no_model_or_training_call(self):
        tree = ast.parse(Path(audit.__file__).read_text(encoding="utf-8"))
        called_names = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        for forbidden in ("generate", "chat", "fit", "backward", "train"):
            self.assertNotIn(forbidden, called_names)


if __name__ == "__main__":
    unittest.main()
