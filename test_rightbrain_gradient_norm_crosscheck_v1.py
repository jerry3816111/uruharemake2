import ast
import unittest
from pathlib import Path

import audit_rightbrain_gradient_norm_crosscheck_v1 as crosscheck
import build_rightbrain_role_curriculum_training_pilot_v1 as construction
import diagnose_rightbrain_training_signal_telemetry_v1 as source_telemetry


ROOT = Path(__file__).resolve().parent


class RightBrainGradientNormCrosscheckV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preregistration = crosscheck.load_json(crosscheck.DEFAULT_PREREGISTRATION)
        cls.lock = crosscheck.load_json(crosscheck.DEFAULT_EXECUTION_LOCK)
        cls.result_lock_path = (
            ROOT / "configs/rightbrain_gradient_norm_crosscheck_v1_result_lock.json"
        )

    def test_control_values_and_measurements_are_frozen(self):
        problem = self.preregistration["problem"]
        self.assertEqual(problem["superseded_candidate_norm"], 403.7281799316406)
        self.assertEqual(problem["reproducible_control_norm"], 2.878972291946411)
        probe = self.preregistration["exact_probe"]
        self.assertEqual(probe["mps_official_norm_repetitions"], 5)
        self.assertEqual(probe["micro_steps"], probe["gradient_accumulation"], 8)
        self.assertEqual(probe["optimizer_steps"], 0)

    def test_old_result_is_internally_recomposable(self):
        old = crosscheck.load_json(source_telemetry.DEFAULT_RESULT_JSON)["telemetry"]
        group = crosscheck.recompose_norm(old["norm_by_projection_and_lora_side"])
        layer = crosscheck.recompose_norm(old["norm_by_layer"])
        self.assertLess(crosscheck.relative_error(old["total_gradient_norm"], group), 1e-6)
        self.assertLess(crosscheck.relative_error(old["total_gradient_norm"], layer), 1e-6)

    def test_harness_has_no_optimizer_clipping_generation_or_save(self):
        tree = ast.parse(Path(crosscheck.__file__).read_text(encoding="utf-8"))
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

    def test_execution_lock_authorizes_only_zero_update_crosscheck(self):
        authorization = self.lock["authorization"]
        self.assertTrue(authorization["zero_update_norm_crosscheck"])
        self.assertEqual(authorization["backward_micro_steps"], 8)
        for forbidden in (
            "optimizer_instantiation",
            "optimizer_step",
            "gradient_clipping_call",
            "parameter_mutation",
            "model_or_adapter_save",
            "text_generation",
            "production_runtime_change",
        ):
            self.assertFalse(authorization[forbidden])

    def test_preflight_is_stage_aware(self):
        validation = crosscheck.preflight()
        invariant = {
            name: passed
            for name, passed in validation["checks"].items()
            if name != "result_absent"
        }
        self.assertTrue(all(invariant.values()))
        self.assertEqual(
            validation["checks"]["result_absent"],
            not crosscheck.DEFAULT_RESULT_JSON.exists() and not crosscheck.DEFAULT_RESULT_MD.exists(),
        )

    def test_result_lock_when_available(self):
        if not self.result_lock_path.exists():
            self.skipTest("Gradient norm crosscheck result has not been executed yet")
        result_lock = crosscheck.load_json(self.result_lock_path)
        for binding in result_lock["result_bindings"]:
            path = ROOT / binding["path"]
            self.assertTrue(path.is_file(), binding["path"])
            self.assertEqual(construction.sha256_file(path), binding["sha256"])
        result = crosscheck.load_json(crosscheck.DEFAULT_RESULT_JSON)
        self.assertTrue(result["decision"]["valid"])
        self.assertTrue(result["decision"]["hypothesis_confirmed"])
        self.assertTrue(result["parameter_integrity"]["unchanged"])
        for forbidden in (
            "model_training",
            "training_parameter_change",
            "production_runtime_change",
            "persona_similarity_claim",
        ):
            self.assertFalse(result_lock["authorization"][forbidden])


if __name__ == "__main__":
    unittest.main()
