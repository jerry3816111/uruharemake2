import ast
import unittest
from pathlib import Path

import build_rightbrain_role_curriculum_training_pilot_v1 as construction
import diagnose_rightbrain_training_signal_telemetry_v1 as telemetry


ROOT = Path(__file__).resolve().parent


class RightBrainTrainingSignalTelemetryV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preregistration = telemetry.load_json(telemetry.DEFAULT_PREREGISTRATION)
        cls.lock = telemetry.load_json(telemetry.DEFAULT_EXECUTION_LOCK)
        cls.result_lock_path = (
            ROOT / "configs/rightbrain_training_signal_telemetry_v1_result_lock.json"
        )

    def test_hypothesis_and_single_batch_are_frozen(self):
        self.assertEqual(
            self.preregistration["status"],
            "frozen_before_any_telemetry_backward_pass",
        )
        hypothesis = self.preregistration["falsifiable_hypothesis"]
        self.assertEqual(hypothesis["severe_clipping_ratio_minimum"], 100.0)
        self.assertEqual(hypothesis["configured_maximum_gradient_norm"], 0.3)
        probe = self.preregistration["exact_probe"]
        self.assertEqual(probe["micro_steps"], probe["gradient_accumulation"], 8)
        self.assertEqual(probe["optimizer_updates"], 0)
        self.assertEqual(len(probe["row_indices"]), len(probe["row_ids"]), 8)

    def test_exact_first_training_batch_is_reconstructed(self):
        rows = telemetry.load_json(construction.DEFAULT_TREATMENT)
        probe = self.preregistration["exact_probe"]
        order = telemetry.exact_row_order(rows, probe["random_seed"])
        actual_indices = order[: probe["micro_steps"]]
        self.assertEqual(actual_indices, probe["row_indices"])
        self.assertEqual([rows[index]["id"] for index in actual_indices], probe["row_ids"])

    def test_harness_has_no_optimizer_clipping_generation_or_save_call(self):
        tree = ast.parse(Path(telemetry.__file__).read_text(encoding="utf-8"))
        names = set()
        attributes = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name):
                names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                attributes.add(node.func.attr)
        for forbidden in (
            "AdamW",
            "SGD",
            "step",
            "clip_grad_norm_",
            "clip_grad_value_",
            "save_pretrained",
            "generate",
        ):
            self.assertNotIn(forbidden, names)
            self.assertNotIn(forbidden, attributes)

    def test_execution_lock_authorizes_only_zero_update_telemetry(self):
        authorization = self.lock["authorization"]
        self.assertTrue(authorization["exact_zero_update_telemetry"])
        self.assertEqual(authorization["backward_micro_steps"], 8)
        for forbidden in (
            "optimizer_instantiation",
            "optimizer_step",
            "gradient_clipping_call",
            "model_or_adapter_save",
            "text_generation",
            "production_runtime_change",
        ):
            self.assertFalse(authorization[forbidden])

    def test_preflight_is_stage_aware(self):
        validation = telemetry.preflight()
        non_result_checks = {
            name: passed
            for name, passed in validation["checks"].items()
            if name != "result_absent"
        }
        self.assertTrue(all(non_result_checks.values()))
        if telemetry.DEFAULT_RESULT_JSON.exists() or telemetry.DEFAULT_RESULT_MD.exists():
            self.assertFalse(validation["passed"])
            self.assertFalse(validation["checks"]["result_absent"])
        else:
            self.assertTrue(validation["passed"])
            self.assertTrue(validation["checks"]["result_absent"])

    def test_result_is_locked_and_authorizes_no_training(self):
        if not self.result_lock_path.exists():
            self.skipTest("Telemetry result has not been executed yet")
        result_lock = telemetry.load_json(self.result_lock_path)
        for binding in result_lock["result_bindings"]:
            path = ROOT / binding["path"]
            self.assertTrue(path.is_file(), binding["path"])
            self.assertEqual(construction.sha256_file(path), binding["sha256"])
        result = telemetry.load_json(telemetry.DEFAULT_RESULT_JSON)
        self.assertTrue(result["decision"]["valid"])
        self.assertTrue(result["decision"]["hypothesis_confirmed"])
        self.assertEqual(len(result["losses"]), 8)
        self.assertEqual(result["telemetry"]["gradient_element_count"], 80740352)
        self.assertTrue(result["telemetry"]["all_gradient_elements_finite"])
        self.assertTrue(result["parameter_integrity"]["unchanged"])
        authorization = result_lock["authorization"]
        for forbidden in (
            "model_training",
            "max_norm_change",
            "learning_rate_change",
            "production_runtime_change",
            "persona_similarity_claim",
        ):
            self.assertFalse(authorization[forbidden])


if __name__ == "__main__":
    unittest.main()
