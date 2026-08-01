#!/usr/bin/env python3
"""Contract tests for Qwen3 1-layer versus 36-layer localization."""

from __future__ import annotations

import unittest
from pathlib import Path

import build_rightbrain_qwen3_depth_repro_v1 as construction


ROOT = Path(__file__).resolve().parent


class RightBrainQwen3DepthReproV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not construction.DEFAULT_PREREGISTRATION.exists():
            raise unittest.SkipTest("construction has not been generated")
        cls.preregistration = construction.load_json(construction.DEFAULT_PREREGISTRATION)

    def test_depth_is_the_only_causal_variable(self):
        prereg = self.preregistration
        self.assertEqual(prereg["causal_variable"]["name"], "active_transformer_layer_count")
        self.assertEqual(prereg["causal_variable"]["levels"], [1, 36])
        self.assertTrue(prereg["causal_variable"]["only_intended_change"])
        self.assertEqual(prereg["exact_probe"]["device"], "gpu_metal")
        self.assertEqual(prereg["exact_probe"]["optimizer_steps"], 0)
        self.assertFalse(prereg["exact_probe"]["gradient_checkpointing"])

    def test_model_adapter_input_and_parent_are_frozen(self):
        prereg = self.preregistration
        self.assertEqual(prereg["official_model_contract"]["total_transformer_layers"], 36)
        self.assertEqual(set(prereg["base_contracts"]), {"1", "36"})
        self.assertEqual(prereg["base_contracts"]["1"]["selected_weight_tensor_count"], 11)
        self.assertEqual(prereg["base_contracts"]["36"]["selected_weight_tensor_count"], 396)
        self.assertEqual(prereg["adapter_contract"]["rank"], 32)
        self.assertEqual(prereg["adapter_contract"]["dropout"], 0.0)
        self.assertEqual(
            prereg["adapter_contract"]["placement"],
            "same_first_transformer_layer_only",
        )
        one_adapter = prereg["adapter_contract"]["by_layer_count"]["1"]
        full_adapter = prereg["adapter_contract"]["by_layer_count"]["36"]
        self.assertEqual(one_adapter["tensor_count"], 14)
        self.assertEqual(full_adapter["tensor_count"], 14)
        self.assertEqual(one_adapter["parameter_count"], full_adapter["parameter_count"])
        self.assertEqual(one_adapter["sha256"], full_adapter["sha256"])
        self.assertEqual(prereg["input_contract"]["shape"], [1, 64, 2560])
        parent = ROOT / prereg["evidence_parent"]["path"]
        self.assertEqual(construction.sha256_file(parent), prereg["evidence_parent"]["sha256"])

    def test_safety_boundary_excludes_training_and_persona_claims(self):
        boundaries = self.preregistration["boundaries"]
        self.assertFalse(boundaries["persona_training"])
        self.assertFalse(boundaries["optimizer_update"])
        self.assertFalse(boundaries["text_generation"])
        self.assertFalse(boundaries["production_runtime_change"])
        self.assertFalse(boundaries["persona_similarity_claim"])
        self.assertFalse(boundaries["lm_head_or_cross_entropy_included"])

    def test_execution_lock_when_available(self):
        if not construction.DEFAULT_EXECUTION_LOCK.exists():
            self.skipTest("execution lock not generated")
        lock = construction.load_json(construction.DEFAULT_EXECUTION_LOCK)
        self.assertEqual(lock["authorization"]["layer_counts"], [1, 36])
        self.assertEqual(lock["authorization"]["optimizer_steps"], 0)
        self.assertFalse(lock["authorization"]["production_runtime_change"])
        for binding in lock["bindings"]:
            path = Path(binding["path"])
            if binding["scope"] == "repository":
                path = ROOT / path
            self.assertEqual(construction.sha256_file(path), binding["sha256"])

    def test_runner_has_backward_without_optimizer_or_generation(self):
        source = (ROOT / "run_rightbrain_qwen3_depth_repro_v1.py").read_text(encoding="utf-8")
        self.assertIn("nn.value_and_grad", source)
        self.assertNotIn("optimizer.update", source)
        self.assertNotIn("mlx_lm.generate", source)
        self.assertNotIn("save_safetensors", source)

    def test_result_lock_when_available(self):
        path = ROOT / self.preregistration["result_paths"]["result_lock"]
        if not path.exists():
            self.skipTest("result lock not generated")
        lock = construction.load_json(path)
        for binding in lock["result_bindings"]:
            bound = Path(binding["path"])
            if binding["scope"] == "repository":
                bound = ROOT / bound
            self.assertEqual(construction.sha256_file(bound), binding["sha256"])
        self.assertFalse(lock["authorization"]["persona_training"])


if __name__ == "__main__":
    unittest.main()
