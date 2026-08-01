#!/usr/bin/env python3
"""Regression checks for the MLX single-step gradient localization probe."""

import ast
import unittest
from pathlib import Path

import build_rightbrain_mlx_single_step_repro_v1 as construction


ROOT = Path(__file__).resolve().parent
RUNNER = ROOT / "run_rightbrain_mlx_single_step_repro_v1.py"


class RightBrainMlxSingleStepReproV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preregistration = construction.load_json(construction.DEFAULT_PREREGISTRATION)
        cls.prior = construction.load_json(construction.PRIOR_PREREGISTRATION)

    def test_single_step_is_the_only_localization_change(self):
        report = construction.build_report()
        self.assertTrue(report["decision"]["passed"], report["checks"])
        self.assertTrue(report["checks"]["single_first_row_only"])
        self.assertTrue(report["checks"]["no_gradient_accumulation"])
        self.assertTrue(report["checks"]["only_localization_fields_changed"])
        self.assertEqual(
            set(report["observed_changed_probe_keys"]),
            {
                "gradient_accumulation",
                "micro_steps",
                "row_indices",
                "row_ids",
                "canonical_token_and_label_sha256",
            },
        )
        probe = self.preregistration["exact_probe"]
        self.assertEqual(probe["gradient_accumulation"], 1)
        self.assertEqual(probe["micro_steps"], 1)
        self.assertEqual(probe["row_indices"], [63])
        self.assertEqual(probe["row_ids"], ["rb_role_specialization_v1_0064"])

    def test_model_adapter_environment_and_safety_boundaries_are_fixed(self):
        self.assertEqual(
            self.preregistration["local_environment"], self.prior["local_environment"]
        )
        self.assertEqual(
            self.preregistration["local_model_contract"], self.prior["local_model_contract"]
        )
        self.assertEqual(
            self.preregistration["adapter_conversion_contract"],
            self.prior["adapter_conversion_contract"],
        )
        boundaries = self.preregistration["boundaries"]
        for key in (
            "optimizer_instantiation",
            "optimizer_step",
            "gradient_clipping",
            "parameter_mutation",
            "adapter_or_model_save",
            "text_generation",
            "production_runtime_change",
            "persona_similarity_claim",
        ):
            self.assertFalse(boundaries[key], key)

    def test_runner_delegates_to_audited_zero_update_probe(self):
        tree = ast.parse(RUNNER.read_text(encoding="utf-8"))
        calls = {
            node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, (ast.Attribute, ast.Name))
        }
        imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        source = RUNNER.read_text(encoding="utf-8")
        self.assertIn("run_repeat", calls)
        self.assertIn("_successful_measurements", calls)
        self.assertNotIn("mlx.optimizers", imports)
        for forbidden in ("Adam", "AdamW", "SGD", "save_weights", "generate"):
            self.assertNotIn(forbidden, source)

    def test_execution_lock_when_available(self):
        if not construction.DEFAULT_EXECUTION_LOCK.exists():
            self.skipTest("MLX single-step execution lock not written")
        lock = construction.load_json(construction.DEFAULT_EXECUTION_LOCK)
        for binding in lock["bindings"]:
            path = Path(binding["path"])
            if binding.get("scope") != "external_local" and not path.is_absolute():
                path = ROOT / path
            self.assertTrue(path.is_file(), str(path))
            self.assertEqual(construction.sha256_file(path), binding["sha256"])
        authorization = lock["authorization"]
        self.assertEqual(authorization["micro_steps_each"], 1)
        self.assertEqual(authorization["gradient_accumulation"], 1)
        self.assertEqual(authorization["adapter_dropout"], 0.0)
        self.assertEqual(authorization["optimizer_steps"], 0)
        self.assertFalse(authorization["production_runtime_change"])

    def test_result_lock_when_available(self):
        result_lock_path = ROOT / self.preregistration["result_paths"]["result_lock"]
        if not result_lock_path.exists():
            self.skipTest("MLX single-step result lock not available")
        lock = construction.load_json(result_lock_path)
        for binding in lock["result_bindings"]:
            path = Path(binding["path"])
            if binding.get("scope") != "external_local" and not path.is_absolute():
                path = ROOT / path
            self.assertTrue(path.is_file(), str(path))
            self.assertEqual(construction.sha256_file(path), binding["sha256"])
        self.assertFalse(lock["authorization"]["model_training_in_this_experiment"])
        self.assertFalse(lock["authorization"]["production_runtime_change"])
        self.assertFalse(lock["authorization"]["persona_similarity_claim"])


if __name__ == "__main__":
    unittest.main()
