import ast
import unittest
from pathlib import Path

import audit_rightbrain_gradient_reproducibility_v1 as audit
import build_rightbrain_role_curriculum_training_pilot_v1 as construction


ROOT = Path(__file__).resolve().parent


class RightBrainGradientReproducibilityV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preregistration = audit.load_json(audit.DEFAULT_PREREGISTRATION)
        cls.lock = audit.load_json(audit.DEFAULT_EXECUTION_LOCK)
        cls.result_lock_path = (
            ROOT / "configs/rightbrain_gradient_reproducibility_v1_result_lock.json"
        )

    def test_three_isolated_repeats_and_thresholds_are_frozen(self):
        probe = self.preregistration["exact_probe"]
        self.assertEqual(probe["repeat_ids"], [1, 2, 3])
        self.assertTrue(probe["fresh_python_process_per_repeat"])
        self.assertEqual(probe["micro_steps_per_repeat"], probe["gradient_accumulation"], 8)
        self.assertEqual(probe["optimizer_steps"], 0)
        hypothesis = self.preregistration["falsifiable_hypothesis"]
        self.assertEqual(
            hypothesis["stable_if_all"]["total_norm_max_to_min_ratio_maximum"],
            1.01,
        )
        self.assertEqual(
            hypothesis["unstable_if_any"]["total_norm_max_to_min_ratio_minimum"],
            1.2,
        )

    def test_harness_has_no_optimizer_clipping_generation_or_save(self):
        tree = ast.parse(Path(audit.__file__).read_text(encoding="utf-8"))
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

    def test_execution_lock_authorizes_only_three_gradient_repeats(self):
        authorization = self.lock["authorization"]
        self.assertTrue(authorization["gradient_only_repeats"])
        self.assertEqual(authorization["repeat_ids"], [1, 2, 3])
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

    def test_repeat_preflight_is_stage_aware(self):
        for repeat_id in (1, 2, 3):
            validation = audit.preflight_repeat(repeat_id)
            ignored = {"repeat_result_absent", "summary_absent"}
            invariant_checks = {
                name: passed
                for name, passed in validation["checks"].items()
                if name not in ignored
            }
            self.assertTrue(all(invariant_checks.values()))
            self.assertEqual(
                validation["checks"]["repeat_result_absent"],
                not audit.repeat_path(repeat_id).exists(),
            )
            self.assertEqual(
                validation["checks"]["summary_absent"],
                not audit.DEFAULT_SUMMARY_JSON.exists() and not audit.DEFAULT_SUMMARY_MD.exists(),
            )

    def test_classification_regions_are_deterministic(self):
        stable = audit.classify_summary(
            [2.87, 2.88, 2.879],
            [0.9999, 0.9999, 0.9999],
            self.preregistration,
        )
        self.assertEqual(stable["outcome"], "stable_matches_historical_2_878972")
        unstable = audit.classify_summary(
            [2.8, 40.0, 400.0],
            [0.95, 0.8, 0.9],
            self.preregistration,
        )
        self.assertEqual(
            unstable["outcome"],
            "gradient_reconstruction_unstable_across_processes",
        )

    def test_result_lock_when_available(self):
        if not self.result_lock_path.exists():
            self.skipTest("Gradient reproducibility result has not been completed yet")
        result_lock = audit.load_json(self.result_lock_path)
        for binding in result_lock["result_bindings"]:
            path = ROOT / binding["path"]
            self.assertTrue(path.is_file(), binding["path"])
            self.assertEqual(construction.sha256_file(path), binding["sha256"])
        summary = audit.load_json(audit.DEFAULT_SUMMARY_JSON)
        self.assertTrue(summary["decision"]["valid"])
        self.assertEqual(len(summary["total_gradient_norms"]), 3)
        self.assertTrue(summary["process_isolation"]["passed"])
        authorization = result_lock["authorization"]
        for forbidden in (
            "model_training",
            "training_parameter_change",
            "production_runtime_change",
            "persona_similarity_claim",
        ):
            self.assertFalse(authorization[forbidden])


if __name__ == "__main__":
    unittest.main()
