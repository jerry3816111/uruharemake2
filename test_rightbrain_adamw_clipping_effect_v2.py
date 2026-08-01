import ast
import unittest
from pathlib import Path

import build_rightbrain_role_curriculum_training_pilot_v1 as construction
import diagnose_rightbrain_adamw_clipping_effect_v1 as v1
import diagnose_rightbrain_adamw_clipping_effect_v2 as v2


ROOT = Path(__file__).resolve().parent


class RightBrainAdamWClippingEffectV2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preregistration = v2.load_json(v2.DEFAULT_PREREGISTRATION)
        cls.lock = v2.load_json(v2.DEFAULT_EXECUTION_LOCK)
        cls.result_lock_path = (
            ROOT / "configs/rightbrain_adamw_clipping_effect_v2_result_lock.json"
        )

    def test_only_control_norm_changed_from_v1(self):
        self.assertEqual(
            self.preregistration["problem"]["valid_control_gradient_norm"],
            2.878972291946411,
        )
        v1_preregistration = v2.load_json(v1.DEFAULT_PREREGISTRATION)
        for key in ("near_equivalent_if_all", "material_effect_if_any"):
            self.assertEqual(
                self.preregistration["falsifiable_hypothesis"][key],
                v1_preregistration["falsifiable_hypothesis"][key],
            )
        self.assertEqual(
            self.preregistration["optimizer_contract"],
            v1_preregistration["optimizer_contract"],
        )

    def test_harness_has_no_optimizer_clipping_generation_or_save(self):
        tree = ast.parse(Path(v2.__file__).read_text(encoding="utf-8"))
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

    def test_execution_lock_authorizes_only_zero_update_simulation(self):
        authorization = self.lock["authorization"]
        self.assertTrue(authorization["zero_update_adamw_simulation"])
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
        validation = v2.preflight()
        invariant = {
            name: passed
            for name, passed in validation["checks"].items()
            if name != "result_absent"
        }
        self.assertTrue(all(invariant.values()))
        self.assertEqual(
            validation["checks"]["result_absent"],
            not v2.DEFAULT_RESULT_JSON.exists() and not v2.DEFAULT_RESULT_MD.exists(),
        )

    def test_result_lock_when_available(self):
        if not self.result_lock_path.exists():
            self.skipTest("AdamW v2 result has not been executed yet")
        result_lock = v2.load_json(self.result_lock_path)
        for binding in result_lock["result_bindings"]:
            path = ROOT / binding["path"]
            self.assertTrue(path.is_file(), binding["path"])
            self.assertEqual(construction.sha256_file(path), binding["sha256"])
        result = v2.load_json(v2.DEFAULT_RESULT_JSON)
        self.assertTrue(result["decision"]["valid"])
        self.assertTrue(result["decision"]["material_effect"])
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
