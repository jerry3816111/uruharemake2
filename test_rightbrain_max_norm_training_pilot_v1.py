import ast
import unittest
from pathlib import Path

import build_rightbrain_max_norm_training_pilot_v1 as construction
import audit_rightbrain_max_norm_training_pilot_v1 as audit
import run_rightbrain_max_norm_training_pilot_v1 as runner


ROOT = Path(__file__).resolve().parent


class RightBrainMaxNormTrainingPilotV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preregistration = construction.load_json(construction.DEFAULT_PREREGISTRATION)

    def test_exact_single_training_variable(self):
        conditions = self.preregistration["conditions"]
        self.assertEqual(tuple(conditions), construction.CONDITIONS)
        self.assertEqual(conditions["control_0_3"]["maximum_gradient_norm"], 0.3)
        self.assertEqual(conditions["treatment_3_0"]["maximum_gradient_norm"], 3.0)
        schedule = self.preregistration["controlled_training_schedule"]
        self.assertEqual(schedule["dataset_rows"], 80)
        self.assertEqual(schedule["micro_steps_exact"], 80)
        self.assertEqual(schedule["gradient_accumulation"], 8)
        self.assertEqual(schedule["optimizer_updates_exact"], 10)

    def test_construction_contract_passes_before_execution(self):
        frozen = construction.load_json(construction.DEFAULT_REPORT_JSON)
        self.assertTrue(frozen["decision"]["passed"], frozen["checks"])
        report = construction.build_report()
        invariant_checks = {
            key: value
            for key, value in report["checks"].items()
            if key
            not in {
                "temporary_output_directories_absent",
                "result_outputs_absent",
            }
        }
        self.assertTrue(all(invariant_checks.values()), invariant_checks)
        self.assertTrue(report["holdout_audit"]["passed"])
        self.assertTrue(report["checks"]["no_production_authorization"])

    def test_runner_contains_real_training_and_fresh_evaluation(self):
        tree = ast.parse(Path(runner.__file__).read_text(encoding="utf-8"))
        called = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name):
                called.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called.add(node.func.attr)
        for required in ("AdamW", "backward", "clip_grad_norm_", "step", "save_pretrained"):
            self.assertIn(required, called)
        self.assertIn("evaluate_adapter", called)

    def test_exact_mcnemar_pairing(self):
        control = [
            {"id": "a", "correct": True},
            {"id": "b", "correct": False},
            {"id": "c", "correct": False},
        ]
        treatment = [
            {"id": "a", "correct": False},
            {"id": "b", "correct": True},
            {"id": "c", "correct": True},
        ]
        result = runner._exact_mcnemar(control, treatment, ("id",), "correct")
        self.assertEqual(result["control_only_correct"], 1)
        self.assertEqual(result["treatment_only_correct"], 2)
        self.assertEqual(result["discordant_pairs"], 3)
        self.assertEqual(result["two_sided_exact_p_value"], 1.0)

    def test_lock_and_result_when_available(self):
        if not construction.DEFAULT_EXECUTION_LOCK.exists():
            self.skipTest("Execution lock has not been written yet")
        validation = runner.validate_execution_lock()
        self.assertTrue(validation["passed"], validation["bindings"])
        lock = validation["lock"]
        self.assertFalse(lock["authorization"]["production_runtime_change"])
        self.assertFalse(lock["authorization"]["production_adapter_replacement"])
        result_path = ROOT / self.preregistration["result_paths"]["aggregate_json"]
        if not result_path.exists():
            return
        result = construction.load_json(result_path)
        self.assertEqual(set(result["training"]), set(construction.CONDITIONS))
        self.assertEqual(set(result["evaluations"]), set(construction.CONDITIONS))
        self.assertFalse(result["decision"]["authorize_production"])
        self.assertFalse(result["decision"]["authorize_persona_similarity_claim"])

    def test_invalidating_audit_when_training_reports_available(self):
        paths = [
            runner._training_report_path(self.preregistration, condition)
            for condition in construction.CONDITIONS
        ]
        if not all(path.exists() for path in paths):
            self.skipTest("Both condition training reports are not available")
        result = audit.audit()
        self.assertFalse(result["decision"]["valid_causal_comparison"])
        self.assertEqual(
            result["decision"]["outcome"],
            "invalidate_v1_due_nonreproducible_preclip_norm",
        )
        self.assertTrue(result["causal_integrity"]["checks"]["first_eight_losses_identical"])
        self.assertFalse(
            result["causal_integrity"]["checks"]["first_preclip_norm_reproducible"]
        )


if __name__ == "__main__":
    unittest.main()
