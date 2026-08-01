import ast
import unittest
from pathlib import Path

import torch

import build_rightbrain_role_curriculum_training_pilot_v1 as construction
import diagnose_rightbrain_adamw_clipping_effect_v1 as diagnostic
import diagnose_rightbrain_training_signal_telemetry_v1 as source_telemetry


ROOT = Path(__file__).resolve().parent


class RightBrainAdamWClippingEffectV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preregistration = diagnostic.load_json(diagnostic.DEFAULT_PREREGISTRATION)
        cls.lock = diagnostic.load_json(diagnostic.DEFAULT_EXECUTION_LOCK)
        cls.result_lock_path = (
            ROOT / "configs/rightbrain_adamw_clipping_effect_v1_result_lock.json"
        )

    def test_single_variable_and_effect_regions_are_frozen(self):
        contract = self.preregistration["optimizer_contract"]
        self.assertEqual(contract["learning_rate"], 3e-7)
        self.assertEqual(contract["weight_decay"], 0.02)
        self.assertEqual(contract["epsilon"], 1e-6)
        self.assertEqual(contract["maximum_gradient_norm"], 0.3)
        hypothesis = self.preregistration["falsifiable_hypothesis"]
        self.assertEqual(
            hypothesis["near_equivalent_if_all"]["relative_l2_difference_maximum"],
            0.01,
        )
        self.assertEqual(
            hypothesis["material_effect_if_any"]["relative_l2_difference_minimum"],
            0.05,
        )

    def test_exact_source_batch_is_preserved(self):
        rows = diagnostic.load_json(construction.DEFAULT_TREATMENT)
        probe = self.preregistration["exact_probe"]
        order = source_telemetry.exact_row_order(rows, probe["random_seed"])
        actual_indices = order[: probe["micro_steps"]]
        self.assertEqual(actual_indices, probe["row_indices"])
        self.assertEqual([rows[index]["id"] for index in actual_indices], probe["row_ids"])

    def test_analytic_first_step_matches_torch_adamw(self):
        initial = torch.tensor([1.0, -2.0, 0.5, -0.25], dtype=torch.float64)
        gradient = torch.tensor([0.2, -0.03, 1e-8, -0.7], dtype=torch.float64)
        parameter = initial.clone().requires_grad_(True)
        parameter.grad = gradient.clone()
        optimizer = torch.optim.AdamW(
            [parameter],
            lr=3e-7,
            betas=(0.9, 0.999),
            eps=1e-6,
            weight_decay=0.02,
            amsgrad=False,
            maximize=False,
            foreach=False,
        )
        expected_delta = diagnostic.adamw_first_step_delta(
            initial,
            gradient,
            scale=1.0,
            learning_rate=3e-7,
            weight_decay=0.02,
            epsilon=1e-6,
        )
        optimizer.step()
        torch.testing.assert_close(parameter.detach(), initial + expected_delta, rtol=0, atol=1e-15)

    def test_harness_has_no_optimizer_step_clipping_generation_or_save(self):
        tree = ast.parse(Path(diagnostic.__file__).read_text(encoding="utf-8"))
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

    def test_decision_regions_are_deterministic(self):
        hypothesis = self.preregistration["falsifiable_hypothesis"]
        near = diagnostic.classify(
            {
                "overall": {
                    "relative_l2_difference": 0.005,
                    "cosine_similarity": 0.99995,
                    "clipped_to_unclipped_l2_ratio": 0.995,
                }
            },
            hypothesis,
        )
        self.assertEqual(near["outcome"], "first_step_updates_near_equivalent")
        material = diagnostic.classify(
            {
                "overall": {
                    "relative_l2_difference": 0.06,
                    "cosine_similarity": 0.99999,
                    "clipped_to_unclipped_l2_ratio": 1.0,
                }
            },
            hypothesis,
        )
        self.assertEqual(material["outcome"], "first_step_clipping_has_material_effect")
        inconclusive = diagnostic.classify(
            {
                "overall": {
                    "relative_l2_difference": 0.02,
                    "cosine_similarity": 0.9995,
                    "clipped_to_unclipped_l2_ratio": 0.98,
                }
            },
            hypothesis,
        )
        self.assertEqual(inconclusive["outcome"], "first_step_clipping_effect_inconclusive")

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
        validation = diagnostic.preflight()
        non_result_checks = {
            name: passed
            for name, passed in validation["checks"].items()
            if name != "result_absent"
        }
        self.assertTrue(all(non_result_checks.values()))
        if diagnostic.DEFAULT_RESULT_JSON.exists() or diagnostic.DEFAULT_RESULT_MD.exists():
            self.assertFalse(validation["passed"])
            self.assertFalse(validation["checks"]["result_absent"])
        else:
            self.assertTrue(validation["passed"])
            self.assertTrue(validation["checks"]["result_absent"])

    def test_result_lock_when_available(self):
        if not self.result_lock_path.exists():
            self.skipTest("AdamW clipping-effect result has not been executed yet")
        result_lock = diagnostic.load_json(self.result_lock_path)
        for binding in result_lock["result_bindings"]:
            path = ROOT / binding["path"]
            self.assertTrue(path.is_file(), binding["path"])
            self.assertEqual(construction.sha256_file(path), binding["sha256"])
        result = diagnostic.load_json(diagnostic.DEFAULT_RESULT_JSON)
        self.assertTrue(result["decision"]["valid"])
        self.assertEqual(result["probe"]["optimizer_steps"], 0)
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
