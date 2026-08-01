import ast
import unittest
from pathlib import Path

import build_rightbrain_gradient_dropout_repro_v1 as construction
import run_rightbrain_gradient_dropout_repro_v1 as runner


ROOT = Path(__file__).resolve().parent


class RightBrainGradientDropoutReproV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preregistration = construction.load_json(construction.DEFAULT_PREREGISTRATION)

    def test_probe_changes_only_dropout(self):
        probe = self.preregistration["exact_probe"]
        self.assertEqual(probe["adapter_dropout"], 0.0)
        self.assertIs(probe["gradient_checkpointing"], True)
        self.assertEqual(probe["dtype"], "torch.bfloat16")
        self.assertIs(probe["norm_foreach"], False)
        self.assertEqual(probe["optimizer_steps"], 0)
        self.assertEqual(probe["row_indices"], [63, 50, 60, 77, 2, 59, 78, 36])

    def test_runner_has_no_optimizer_step_clip_save_or_generation(self):
        tree = ast.parse(Path(runner.__file__).read_text(encoding="utf-8"))
        calls = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
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
        self.assertIn("backward", calls)
        self.assertIn("get_total_norm", calls)

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
            self.skipTest("Dropout probe execution lock not written")
        validation = runner.validate_lock()
        self.assertTrue(validation["passed"], validation["bindings"])
        self.assertEqual(
            validation["lock"]["authorization"]["exact_zero_update_repetitions"],
            [1, 2, 3],
        )

    def test_result_lock_when_available(self):
        result_lock_path = ROOT / self.preregistration["result_paths"]["result_lock"]
        if not result_lock_path.exists():
            self.skipTest("Dropout probe result lock not available")
        lock = construction.load_json(result_lock_path)
        for binding in lock["result_bindings"]:
            path = ROOT / binding["path"]
            self.assertTrue(path.is_file(), binding["path"])
            self.assertEqual(construction.sha256_file(path), binding["sha256"])
        self.assertFalse(lock["authorization"]["model_training_in_this_experiment"])
        self.assertFalse(lock["authorization"]["production_runtime_change"])
        self.assertFalse(lock["authorization"]["persona_similarity_claim"])


if __name__ == "__main__":
    unittest.main()
