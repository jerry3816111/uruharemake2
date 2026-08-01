import ast
import unittest
from pathlib import Path

import build_rightbrain_gradient_float16_repro_v1 as construction
import run_rightbrain_gradient_float16_repro_v1 as runner


ROOT = Path(__file__).resolve().parent


class RightBrainGradientFloat16ReproV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preregistration = construction.load_json(construction.DEFAULT_PREREGISTRATION)

    def test_probe_changes_only_base_activation_dtype(self):
        probe = self.preregistration["exact_probe"]
        self.assertEqual(probe["base_activation_dtype"], "torch.float16")
        self.assertEqual(probe["trainable_adapter_dtype"], "torch.float32")
        self.assertEqual(probe["adapter_dropout"], 0.08)
        self.assertIs(probe["gradient_checkpointing"], True)
        self.assertIs(probe["norm_foreach"], False)
        self.assertEqual(probe["optimizer_steps"], 0)
        self.assertEqual(probe["row_indices"], [63, 50, 60, 77, 2, 59, 78, 36])
        self.assertEqual(probe["driver_allocated_memory_bytes_maximum"], 30 * 1024**3)

    def test_runner_uses_float16_with_checkpointing_and_zero_update_boundary(self):
        tree = ast.parse(Path(runner.__file__).read_text(encoding="utf-8"))
        calls = set()
        float16_build_calls = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
                if node.func.id == "build_model":
                    dtype_keywords = [
                        keyword.value
                        for keyword in node.keywords
                        if keyword.arg == "dtype_name"
                    ]
                    float16_build_calls.extend(dtype_keywords)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
        self.assertTrue(
            any(
                isinstance(value, ast.Constant) and value.value == "float16"
                for value in float16_build_calls
            )
        )
        self.assertNotIn("gradient_checkpointing_disable", calls)
        self.assertIn("backward", calls)
        self.assertIn("get_total_norm", calls)
        for forbidden in (
            "AdamW",
            "SGD",
            "step",
            "clip_grad_norm_",
            "clip_grad_value_",
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

    def test_lock_when_available(self):
        if not construction.DEFAULT_EXECUTION_LOCK.exists():
            self.skipTest("Float16 probe execution lock not written")
        validation = runner.validate_lock()
        self.assertTrue(validation["passed"], validation["bindings"])
        authorization = validation["lock"]["authorization"]
        self.assertEqual(authorization["base_activation_dtype"], "torch.float16")
        self.assertEqual(authorization["trainable_adapter_dtype"], "torch.float32")
        self.assertIs(authorization["gradient_checkpointing"], True)

    def test_result_lock_when_available(self):
        result_lock_path = ROOT / self.preregistration["result_paths"]["result_lock"]
        if not result_lock_path.exists():
            self.skipTest("Float16 probe result lock not available")
        lock = construction.load_json(result_lock_path)
        for binding in lock["result_bindings"]:
            path = ROOT / binding["path"]
            self.assertTrue(path.is_file(), binding["path"])
            self.assertEqual(construction.sha256_file(path), binding["sha256"])
        self.assertFalse(lock["authorization"]["model_training_in_this_experiment"])
        self.assertFalse(lock["authorization"]["production_runtime_change"])
        self.assertFalse(lock["authorization"]["persona_similarity_claim"])

    def test_result_rejects_float16_training_path_when_available(self):
        result_path = ROOT / self.preregistration["result_paths"]["aggregate_json"]
        if not result_path.exists():
            self.skipTest("Float16 probe aggregate not available")
        result = construction.load_json(result_path)
        self.assertFalse(result["decision"]["passed"])
        self.assertEqual(
            result["decision"]["outcome"],
            "float16_does_not_provide_a_usable_reproducible_path",
        )
        self.assertFalse(result["decision"]["authorize_model_training_now"])
        self.assertEqual(result["measurements"]["successful_repeat_count"], 1)
        self.assertEqual(len(result["measurements"]["failures"]), 2)
        self.assertTrue(
            all(failure["nonfinite"] for failure in result["measurements"]["failures"])
        )
        self.assertTrue(
            all(
                not failure["out_of_memory"]
                for failure in result["measurements"]["failures"]
            )
        )


if __name__ == "__main__":
    unittest.main()
