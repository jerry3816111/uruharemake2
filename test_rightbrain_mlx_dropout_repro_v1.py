import ast
import unittest
from pathlib import Path

import build_rightbrain_mlx_dropout_repro_v1 as construction


ROOT = Path(__file__).resolve().parent
RUNNER = ROOT / "run_rightbrain_mlx_dropout_repro_v1.py"


class RightBrainMlxDropoutReproV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preregistration = construction.load_json(construction.DEFAULT_PREREGISTRATION)

    def test_dropout_is_the_only_probe_change(self):
        report = construction.build_report()
        self.assertTrue(report["checks"]["only_probe_change_is_dropout"])
        self.assertTrue(report["checks"]["only_adapter_change_is_dropout"])
        adapter = self.preregistration["adapter_conversion_contract"]
        probe = self.preregistration["exact_probe"]
        self.assertEqual(adapter["dropout"], 0.0)
        self.assertIs(probe["gradient_checkpointing"], True)
        self.assertEqual(probe["optimizer_steps"], 0)

    def test_official_runtime_sources_are_bound(self):
        report = construction.build_report()
        self.assertTrue(report["checks"]["official_runtime_sources_bound"])
        self.assertEqual(
            self.preregistration["causal_basis"]["official_source_commit"],
            "7a1d4f5c12ac82f4b4d0a6e71538d89ca0605247",
        )

    def test_runner_delegates_zero_update_probe_without_optimizer(self):
        tree = ast.parse(RUNNER.read_text(encoding="utf-8"))
        calls = set()
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add(node.module or "")
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.add(node.func.attr)
        self.assertIn("run_repeat", calls)
        self.assertIn("_successful_measurements", calls)
        self.assertNotIn("mlx.optimizers", imports)
        for forbidden in ("Adam", "AdamW", "SGD", "save_weights", "generate"):
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
            self.skipTest("MLX dropout-zero execution lock not written")
        lock = construction.load_json(construction.DEFAULT_EXECUTION_LOCK)
        for binding in lock["bindings"]:
            path = Path(binding["path"])
            if binding.get("scope") != "external_local" and not path.is_absolute():
                path = ROOT / path
            self.assertTrue(path.is_file(), str(path))
            self.assertEqual(construction.sha256_file(path), binding["sha256"])
        authorization = lock["authorization"]
        self.assertEqual(authorization["adapter_dropout"], 0.0)
        self.assertEqual(authorization["optimizer_steps"], 0)
        self.assertFalse(authorization["production_runtime_change"])

    def test_result_lock_when_available(self):
        result_lock_path = ROOT / self.preregistration["result_paths"]["result_lock"]
        if not result_lock_path.exists():
            self.skipTest("MLX dropout-zero result lock not available")
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

    def test_observed_result_rejects_dropout_as_sufficient_cause(self):
        result_path = ROOT / self.preregistration["result_paths"]["aggregate_json"]
        if not result_path.exists():
            self.skipTest("MLX dropout-zero aggregate not available")
        result = construction.load_json(result_path)
        self.assertFalse(result["decision"]["passed"])
        self.assertFalse(result["decision"]["mechanism_supported"])
        self.assertFalse(result["decision"]["authorize_training_now"])
        self.assertEqual(
            result["decision"]["outcome"],
            "mlx_dropout_zero_does_not_restore_gradient_reproducibility",
        )
        measurements = result["measurements"]
        checks = result["checks"]
        self.assertTrue(checks["all_three_repetitions_complete"])
        self.assertTrue(checks["all_losses_and_gradients_finite"])
        self.assertTrue(checks["loss_vectors_exact_across_repetitions"])
        self.assertFalse(checks["gradient_norm_coefficient_of_variation"])
        self.assertFalse(checks["gradient_norm_max_to_min_ratio"])
        self.assertFalse(checks["minimum_pairwise_group_profile_cosine"])
        self.assertFalse(measurements["gradient_hashes_identical"])
        thresholds = self.preregistration["falsifiable_hypothesis"]["confirm_if_all"]
        self.assertGreater(
            measurements["gradient_norm_coefficient_of_variation"],
            thresholds["gradient_norm_coefficient_of_variation_maximum"],
        )
        self.assertGreater(
            measurements["gradient_norm_max_to_min_ratio"],
            thresholds["gradient_norm_max_to_min_ratio_maximum"],
        )
        self.assertLess(
            measurements["minimum_pairwise_group_profile_cosine"],
            thresholds["minimum_pairwise_group_profile_cosine"],
        )


if __name__ == "__main__":
    unittest.main()
