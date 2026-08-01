import ast
import unittest
from pathlib import Path

import build_rightbrain_max_norm_training_pilot_v2 as construction
import run_rightbrain_max_norm_training_pilot_v2 as runner


ROOT = Path(__file__).resolve().parent


class RightBrainMaxNormTrainingPilotV2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preregistration = construction.load_json(construction.DEFAULT_PREREGISTRATION)

    def test_v2_changes_only_common_norm_reduction_method(self):
        schedule = self.preregistration["controlled_training_schedule"]
        self.assertIs(schedule["clip_grad_norm_foreach"], False)
        self.assertEqual(schedule["dataset_rows"], 80)
        self.assertEqual(schedule["micro_steps_exact"], 80)
        self.assertEqual(schedule["optimizer_updates_exact"], 10)
        self.assertEqual(
            self.preregistration["conditions"]["control_0_3"]["maximum_gradient_norm"],
            0.3,
        )
        self.assertEqual(
            self.preregistration["conditions"]["treatment_3_0"]["maximum_gradient_norm"],
            3.0,
        )

    def test_runner_forces_foreach_false(self):
        tree = ast.parse(Path(runner.__file__).read_text(encoding="utf-8"))
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "clip_grad_norm_"
        ]
        self.assertEqual(len(calls), 1)
        keywords = {keyword.arg: keyword.value for keyword in calls[0].keywords}
        self.assertIn("foreach", keywords)
        self.assertIsInstance(keywords["foreach"], ast.Constant)
        self.assertIs(keywords["foreach"].value, False)

    def test_construction_passes_before_execution(self):
        if construction.DEFAULT_REPORT_JSON.exists():
            frozen = construction.load_json(construction.DEFAULT_REPORT_JSON)
            self.assertTrue(frozen["decision"]["passed"])
        current = construction.build_report()
        invariant = {
            key: value
            for key, value in current["checks"].items()
            if key not in {"temporary_outputs_absent", "generated_results_absent"}
        }
        self.assertTrue(all(invariant.values()), invariant)
        if not any(
            (ROOT / self.preregistration["conditions"][condition]["output_directory"]).exists()
            for condition in construction.CONDITIONS
        ):
            self.assertTrue(current["decision"]["passed"], current["checks"])

    def test_lock_when_available(self):
        if not construction.DEFAULT_EXECUTION_LOCK.exists():
            self.skipTest("v2 execution lock not written")
        validation = runner.validate_execution_lock()
        self.assertTrue(validation["passed"], validation["bindings"])
        self.assertIs(validation["lock"]["authorization"]["clip_grad_norm_foreach"], False)

    def test_training_pair_gate_when_available(self):
        paths = [
            runner._training_report_path(self.preregistration, condition)
            for condition in construction.CONDITIONS
        ]
        if not all(path.exists() for path in paths):
            self.skipTest("v2 training pair not complete")
        integrity = runner.validate_training_pair(write_lock=False)
        self.assertTrue(integrity["checks"]["first_eight_losses_exact_match"])
        self.assertTrue(integrity["checks"]["first_preclip_norm_reproducible"])
        self.assertTrue(integrity["decision"]["passed"])

    def test_result_lock_when_available(self):
        result_lock_path = ROOT / self.preregistration["result_paths"]["result_lock"]
        if not result_lock_path.exists():
            self.skipTest("v2 result lock not available")
        result_lock = construction.load_json(result_lock_path)
        for binding in result_lock["result_bindings"]:
            path = ROOT / binding["path"]
            self.assertTrue(path.is_file(), binding["path"])
            self.assertEqual(construction.sha256_file(path), binding["sha256"])
        self.assertFalse(result_lock["authorization"]["production_runtime_change"])
        self.assertFalse(result_lock["authorization"]["production_adapter_replacement"])
        self.assertFalse(result_lock["authorization"]["persona_similarity_claim"])


if __name__ == "__main__":
    unittest.main()
