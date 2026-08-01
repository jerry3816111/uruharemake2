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

    def test_preflight_passes_before_execution(self):
        validation = telemetry.preflight()
        self.assertTrue(validation["passed"])
        self.assertTrue(all(validation["checks"].values()))


if __name__ == "__main__":
    unittest.main()
