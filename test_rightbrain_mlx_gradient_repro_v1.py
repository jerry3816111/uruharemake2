import ast
import unittest
from pathlib import Path

import build_rightbrain_mlx_gradient_repro_v1 as construction


ROOT = Path(__file__).resolve().parent
RUNNER = ROOT / "run_rightbrain_mlx_gradient_repro_v1.py"


class RightBrainMlxGradientReproV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preregistration = construction.load_json(construction.DEFAULT_PREREGISTRATION)

    def test_probe_changes_only_training_backend(self):
        probe = self.preregistration["exact_probe"]
        adapter = self.preregistration["adapter_conversion_contract"]
        self.assertEqual(probe["base_activation_dtype"], "mlx.core.bfloat16")
        self.assertEqual(probe["trainable_adapter_dtype"], "mlx.core.float32")
        self.assertIs(probe["gradient_checkpointing"], True)
        self.assertEqual(adapter["dropout"], 0.08)
        self.assertEqual(adapter["rank"], 32)
        self.assertEqual(adapter["alpha"], 24)
        self.assertEqual(adapter["scale"], 0.75)
        self.assertEqual(probe["optimizer_steps"], 0)
        self.assertEqual(probe["row_indices"], [63, 50, 60, 77, 2, 59, 78, 36])
        self.assertEqual(probe["fixed_allocated_sequence_length"], 800)

    def test_adapter_and_token_contracts_are_frozen(self):
        adapter = self.preregistration["adapter_conversion_contract"]
        probe = self.preregistration["exact_probe"]
        self.assertEqual(adapter["source_tensor_count"], 392)
        self.assertEqual(adapter["target_tensor_count"], 392)
        self.assertEqual(adapter["trainable_parameter_count"], 80740352)
        self.assertEqual(
            adapter["canonical_mapped_sha256"],
            "2464cdaa110cf90f919f692e8275f4a1f8935131e9b580258b44d7f081f1c953",
        )
        self.assertEqual(
            probe["canonical_token_and_label_sha256"],
            "8095c1cb234d713f358b389e58a85dacaec9c3a9c7bf78d960862a79195e136a",
        )

    def test_runner_has_backward_but_no_optimizer_update_save_or_generation(self):
        tree = ast.parse(RUNNER.read_text(encoding="utf-8"))
        calls = set()
        imported_modules = set()
        optimizer_update_calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported_modules.add(node.module or "")
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.add(node.func.attr)
                    if (
                        node.func.attr == "update"
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id in {"optimizer", "opt"}
                    ):
                        optimizer_update_calls.append(node)
        self.assertNotIn("mlx.optimizers", imported_modules)
        self.assertIn("value_and_grad", calls)
        self.assertIn("grad_checkpoint", calls)
        self.assertIn("linear_to_lora_layers", calls)
        self.assertIn("load_weights", calls)
        self.assertEqual(optimizer_update_calls, [])
        for forbidden in (
            "Adam",
            "AdamW",
            "SGD",
            "step",
            "save_weights",
            "save_pretrained",
            "generate",
        ):
            self.assertNotIn(forbidden, calls)

    def test_construction_invariants(self):
        report = construction.build_report()
        invariant = {
            key: value for key, value in report["checks"].items() if key != "outputs_absent"
        }
        self.assertTrue(all(invariant.values()), invariant)
        if not construction.DEFAULT_REPORT_JSON.exists():
            self.assertTrue(report["decision"]["passed"], report["checks"])

    def test_execution_lock_when_available(self):
        if not construction.DEFAULT_EXECUTION_LOCK.exists():
            self.skipTest("MLX execution lock not written")
        lock = construction.load_json(construction.DEFAULT_EXECUTION_LOCK)
        for binding in lock["bindings"]:
            path = Path(binding["path"])
            if binding.get("scope") != "external_local" and not path.is_absolute():
                path = ROOT / path
            self.assertTrue(path.is_file(), str(path))
            self.assertEqual(construction.sha256_file(path), binding["sha256"])
        authorization = lock["authorization"]
        self.assertEqual(authorization["training_backend"], "mlx")
        self.assertEqual(authorization["optimizer_steps"], 0)
        self.assertFalse(authorization["adapter_or_model_save"])
        self.assertFalse(authorization["production_runtime_change"])

    def test_result_lock_when_available(self):
        result_lock_path = ROOT / self.preregistration["result_paths"]["result_lock"]
        if not result_lock_path.exists():
            self.skipTest("MLX result lock not available")
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

    def test_result_rejects_training_despite_finite_memory_safe_gradients(self):
        result_path = ROOT / self.preregistration["result_paths"]["aggregate_json"]
        if not result_path.exists():
            self.skipTest("MLX aggregate not available")
        result = construction.load_json(result_path)
        self.assertFalse(result["decision"]["passed"])
        self.assertEqual(
            result["decision"]["outcome"],
            "mlx_does_not_provide_a_usable_reproducible_gradient_path",
        )
        self.assertFalse(result["decision"]["authorize_training_now"])
        self.assertTrue(result["checks"]["all_losses_and_gradients_finite"])
        self.assertTrue(result["checks"]["peak_memory_within_limit"])
        self.assertTrue(result["checks"]["loss_vectors_exact_across_repetitions"])
        self.assertTrue(result["checks"]["minimum_pairwise_group_profile_cosine"])
        self.assertFalse(result["checks"]["gradient_norm_coefficient_of_variation"])
        self.assertFalse(result["checks"]["gradient_norm_max_to_min_ratio"])
        self.assertGreater(
            result["measurements"]["gradient_norm_max_to_min_ratio"], 2.0
        )


if __name__ == "__main__":
    unittest.main()
