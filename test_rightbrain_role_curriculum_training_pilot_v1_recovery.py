import ast
import unittest
from pathlib import Path

import build_rightbrain_role_curriculum_training_pilot_v1 as construction
import run_rightbrain_role_curriculum_training_pilot_v1 as original
import run_rightbrain_role_curriculum_training_pilot_v1_recovery as recovery


ROOT = Path(__file__).resolve().parent


class RightBrainRoleCurriculumTrainingPilotV1RecoveryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.amendment = construction.load_json(recovery.DEFAULT_AMENDMENT)
        cls.lock = construction.load_json(recovery.DEFAULT_RECOVERY_LOCK)
        cls.result_lock = construction.load_json(
            ROOT / "configs/rightbrain_role_curriculum_training_pilot_v1_result_lock.json"
        )
        cls.preregistration = construction.load_json(original.DEFAULT_PREREGISTRATION)

    def test_amendment_preserves_failed_execution_and_evidence_boundary(self):
        failure = self.amendment["observed_failure"]
        self.assertTrue(failure["original_process_exited_without_formal_result"])
        self.assertEqual(failure["durable_per_condition_evaluation_results_written"], 0)
        self.assertEqual(failure["root_cause"], "unconfirmed")
        protocol = self.amendment["recovery_protocol"]
        self.assertFalse(protocol["model_training"])
        self.assertTrue(protocol["rerun_all_three_evaluation_conditions_from_the_first_item"])
        self.assertTrue(protocol["one_fresh_python_process_per_condition"])

    def test_recovery_source_has_no_training_path(self):
        tree = ast.parse(Path(recovery.__file__).read_text(encoding="utf-8"))
        called_names = set()
        called_attributes = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name):
                called_names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called_attributes.add(node.func.attr)
        for forbidden in ("train_condition", "backward", "step", "zero_grad"):
            self.assertNotIn(forbidden, called_names)
            self.assertNotIn(forbidden, called_attributes)

    def test_recovery_lock_keeps_original_authorization_ceiling(self):
        authorization = self.lock["authorization"]
        self.assertTrue(authorization["condition_isolated_evaluation_recovery"])
        self.assertFalse(authorization["additional_model_training"])
        self.assertFalse(authorization["production_default_change"])
        self.assertFalse(authorization["persona_similarity_claim"])
        self.assertFalse(authorization["public_impersonation"])
        self.assertEqual(
            authorization["maximum_positive_outcome"],
            "authorize_small_source_blind_human_policy_direction_review_only",
        )

    def test_recovery_lock_matches_completed_local_artifacts_when_available(self):
        adapter_paths = recovery._adapter_paths(self.preregistration)
        if not all((path / "adapter_model.safetensors").is_file() for path in adapter_paths.values()):
            self.skipTest("Local adapter artifacts are intentionally not committed")
        validation = recovery.validate_recovery_lock()
        self.assertTrue(validation["passed"])
        self.assertTrue(
            all(row["training_report_match"] for row in validation["adapter_bindings"])
        )

    def test_written_condition_results_are_complete(self):
        for condition, path in recovery.CONDITION_RESULTS.items():
            if not path.exists():
                continue
            result = construction.load_json(path)
            self.assertEqual(result["condition"], condition)
            evaluation = result["evaluation"]
            self.assertEqual(
                evaluation["policy_discrimination"]["comparison_count"],
                40,
            )
            self.assertEqual(evaluation["fresh_generation"]["generation_count"], 80)
            self.assertFalse(result["boundaries"]["model_training"])
            self.assertFalse(result["boundaries"]["persona_similarity_claim"])

    def test_result_lock_binds_complete_rejected_result(self):
        for binding in self.result_lock["result_bindings"]:
            path = ROOT / binding["path"]
            self.assertTrue(path.is_file(), binding["path"])
            self.assertEqual(construction.sha256_file(path), binding["sha256"])
        result = construction.load_json(original.DEFAULT_RESULT_JSON)
        self.assertFalse(result["decision"]["passed"])
        self.assertEqual(
            result["decision"]["outcome"],
            "reject_role_curriculum_promotion",
        )
        self.assertTrue(all(result["decision"]["integrity_checks"].values()))
        self.assertEqual(
            sum(
                row["policy_discrimination"]["comparison_count"]
                for row in result["evaluations"].values()
            ),
            120,
        )
        self.assertEqual(
            sum(
                row["fresh_generation"]["generation_count"]
                for row in result["evaluations"].values()
            ),
            240,
        )

    def test_failed_pilot_authorizes_no_promotion_or_claim(self):
        decision = self.result_lock["decision"]
        self.assertFalse(decision["passed"])
        self.assertEqual(decision["policy_aligned_treatment_bidirectional_accuracy"], 0.5)
        self.assertEqual(
            decision["policy_aligned_treatment_strict_candidate_gate_pass_rate"],
            0.125,
        )
        authorization = self.result_lock["authorization"]
        for forbidden in (
            "production_default_change",
            "production_memory_access",
            "formal_chat_adapter_promotion",
            "source_blind_human_review",
            "persona_similarity_claim",
            "human_likeness_claim",
            "public_impersonation",
        ):
            self.assertFalse(authorization[forbidden])


if __name__ == "__main__":
    unittest.main()
