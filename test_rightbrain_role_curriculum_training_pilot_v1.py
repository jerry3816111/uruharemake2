import ast
import json
import unittest
from collections import Counter
from pathlib import Path

import build_rightbrain_role_curriculum_training_pilot_v1 as construction
import run_rightbrain_role_curriculum_training_pilot_v1 as runner


ROOT = Path(__file__).resolve().parent


def torch_equal_padding_masks(item):
    padding = item["attention_mask"] == 0
    return bool((item["labels"][padding] == -100).all())


class RightBrainRoleCurriculumTrainingPilotV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preregistration = construction.load_json(construction.DEFAULT_PREREGISTRATION)
        cls.amendment = construction.load_json(
            ROOT / "configs/rightbrain_role_curriculum_training_pilot_v1_protocol_amendment_01.json"
        )
        cls.treatment = construction.load_json(construction.DEFAULT_TREATMENT)
        cls.control = construction.load_json(construction.DEFAULT_CONTROL)
        cls.holdout = construction.load_json(construction.DEFAULT_HOLDOUT)
        cls.report = construction.load_json(construction.DEFAULT_REPORT_JSON)
        cls.lock = construction.load_json(runner.DEFAULT_EXECUTION_LOCK)

    def test_token_capacity_change_is_disclosed_before_training(self):
        self.assertIn("amended_after_token_capacity_preflight", self.preregistration["status"])
        self.assertEqual(self.amendment["observations"]["training_rows_over_original_720_limit"], 34)
        self.assertEqual(self.amendment["observations"]["heldout_prompts_over_original_640_budget"], 38)
        schedule = self.preregistration["training_schedule"]
        self.assertEqual(schedule["maximum_sequence_length"], 800)
        self.assertEqual(schedule["fixed_allocated_sequence_length"], 800)
        self.assertTrue(schedule["padding_attention_masked"])
        self.assertEqual(
            self.preregistration["fresh_generation_evaluation"]["prompt_allocation_budget_tokens"],
            800,
        )

    def test_control_changes_only_policy_alignment(self):
        rebuilt = construction.build_policy_permuted_control(self.treatment)
        self.assertEqual(rebuilt, self.control)
        self.assertEqual(len(self.treatment), len(self.control), 80)
        for role in ("system", "user"):
            self.assertEqual(
                Counter(construction.role_message(row, role) for row in self.treatment),
                Counter(construction.role_message(row, role) for row in self.control),
            )
        self.assertEqual(
            Counter(construction.assistant_target(row) for row in self.treatment),
            Counter(construction.assistant_target(row) for row in self.control),
        )
        self.assertEqual(
            sum(row["control_assignment"]["policy_aligned"] for row in self.control),
            40,
        )

    def test_construction_report_passes_every_integrity_boundary(self):
        self.assertEqual(self.report["status"], "construction_passed")
        self.assertTrue(self.report["frozen_input_validation"]["passed"])
        self.assertTrue(self.report["matched_training_data"]["passed"])
        self.assertTrue(self.report["heldout_evaluation"]["passed"])
        self.assertTrue(self.report["builder_source_boundary"]["passed"])
        self.assertEqual(
            self.report["decision"]["outcome"],
            "authorize_execution_harness_lock_construction_only",
        )
        self.assertFalse(self.report["decision"]["authorize_model_training"])

    def test_holdout_is_full_balanced_open_ended_matrix(self):
        cases = self.holdout["cases"]
        self.assertEqual(len(cases), 20)
        matrix = Counter((case["context"], case["memory_mode"]) for case in cases)
        self.assertEqual(len(matrix), 20)
        self.assertEqual(set(matrix.values()), {1})
        self.assertEqual(
            sum(len(case["policy_references"]) for case in cases),
            40,
        )
        self.assertFalse(self.holdout["contains_target_person_utterances"])
        self.assertFalse(self.holdout["contains_official_benchmark_items"])
        self.assertFalse(self.holdout["contains_exact_expected_chat_reply"])
        heldout = self.report["heldout_evaluation"]
        self.assertEqual(heldout["counts"]["normalized_user_input_overlap_count"], 0)
        self.assertEqual(heldout["counts"]["normalized_reference_overlap_count"], 0)
        self.assertEqual(heldout["counts"]["runtime_candidate_gate_pass_count"], 40)
        self.assertEqual(
            heldout["counts"]["historical_training_target_row_count_checked"],
            1061,
        )
        self.assertGreater(
            heldout["counts"]["prior_target_or_model_output_count_checked"],
            400,
        )

    def test_execution_lock_binds_all_behavior_critical_repo_inputs(self):
        validation = runner.validate_lock()
        self.assertTrue(validation["passed"])
        bound = {row["path"] for row in self.lock["bindings"]}
        for path in (
            "configs/rightbrain_role_curriculum_training_pilot_v1_preregistration.json",
            "configs/rightbrain_role_curriculum_training_pilot_v1_protocol_amendment_01.json",
            "datasets/rightbrain_role_specialization_curriculum_v1_policy_permuted_control.json",
            "configs/rightbrain_role_curriculum_training_pilot_v1_holdout.json",
            "run_rightbrain_role_curriculum_training_pilot_v1.py",
            "uruha_brain_mac.py",
        ):
            self.assertIn(path, bound)
        self.assertTrue(self.lock["authorization"]["exact_locked_pilot_execution"])
        self.assertFalse(self.lock["authorization"]["production_default_change"])

    def test_preflight_allocates_identical_fixed_training_shapes_without_model_load(self):
        report = runner.preflight()
        non_output_checks = {
            name: passed
            for name, passed in report["checks"].items()
            if name != "output_directories_absent"
        }
        self.assertTrue(all(non_output_checks.values()))
        output_directories_exist = any(
            (ROOT / output).exists()
            for output in self.preregistration["training_schedule"][
                "output_directories"
            ].values()
        )
        if output_directories_exist:
            self.assertFalse(report["passed"])
            self.assertFalse(report["checks"]["output_directories_absent"])
        else:
            self.assertTrue(report["passed"])
            self.assertTrue(report["checks"]["output_directories_absent"])
        self.assertEqual(report["fixed_allocated_sequence_length"], 800)

        tokenizer = runner.load_tokenizer(self.preregistration)
        dataset = runner.FixedLengthContractDataset(
            self.control[:1], tokenizer, report["fixed_allocated_sequence_length"]
        )
        item = dataset[0]
        self.assertEqual(tuple(item["input_ids"].shape), (800,))
        self.assertEqual(tuple(item["attention_mask"].shape), (800,))
        self.assertTrue(torch_equal_padding_masks(item))

    def test_builder_cannot_train_or_generate(self):
        tree = ast.parse(Path(construction.__file__).read_text(encoding="utf-8"))
        calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        for forbidden in ("backward", "fit", "generate", "train"):
            self.assertNotIn(forbidden, calls)

    def test_success_can_only_authorize_a_small_blind_review(self):
        authorization = self.lock["authorization"]
        self.assertEqual(
            authorization["maximum_positive_outcome"],
            "authorize_small_source_blind_human_policy_direction_review_only",
        )
        self.assertFalse(authorization["persona_similarity_claim"])
        self.assertFalse(authorization["human_likeness_claim"])
        self.assertFalse(authorization["public_impersonation"])


if __name__ == "__main__":
    unittest.main()
