#!/usr/bin/env python3
"""Contract tests for Qwen3 LoRA-span localization."""

from __future__ import annotations

import unittest
from pathlib import Path

import build_rightbrain_qwen3_lora_span_repro_v1 as construction


ROOT = Path(__file__).resolve().parent


class RightBrainQwen3LoraSpanReproV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not construction.DEFAULT_PREREGISTRATION.exists():
            raise unittest.SkipTest("construction has not been generated")
        cls.prereg = construction.load_json(construction.DEFAULT_PREREGISTRATION)

    def test_lora_span_is_the_only_causal_variable(self):
        self.assertEqual(
            self.prereg["causal_variable"]["name"],
            "lora_enabled_transformer_layer_count",
        )
        self.assertEqual(self.prereg["causal_variable"]["levels"], [1, 36])
        self.assertTrue(self.prereg["causal_variable"]["only_intended_change"])
        self.assertEqual(self.prereg["exact_probe"]["fixed_transformer_layer_count"], 36)
        self.assertEqual(self.prereg["exact_probe"]["device"], "gpu_metal")

    def test_base_input_first_adapter_and_safety_are_frozen(self):
        self.assertEqual(self.prereg["base_contract"]["layer_count"], 36)
        self.assertEqual(self.prereg["base_contract"]["selected_weight_tensor_count"], 396)
        adapter = self.prereg["adapter_contract"]
        self.assertTrue(adapter["first_layer_initialization_exact_across_conditions"])
        self.assertEqual(adapter["by_span"]["1"]["tensor_count"], 14)
        self.assertEqual(adapter["by_span"]["36"]["tensor_count"], 504)
        self.assertEqual(
            adapter["by_span"]["1"]["first_layer_sha256"],
            adapter["by_span"]["36"]["first_layer_sha256"],
        )
        self.assertEqual(self.prereg["input_contract"]["shape"], [1, 64, 2560])
        boundaries = self.prereg["boundaries"]
        self.assertFalse(boundaries["persona_training"])
        self.assertFalse(boundaries["optimizer_update"])
        self.assertFalse(boundaries["production_runtime_change"])
        self.assertFalse(boundaries["lm_head_or_cross_entropy_included"])

    def test_parent_evidence_is_bound(self):
        parent = ROOT / self.prereg["evidence_parent"]["path"]
        self.assertEqual(construction.sha256_file(parent), self.prereg["evidence_parent"]["sha256"])
        self.assertEqual(
            self.prereg["evidence_parent"]["observed_outcome"],
            "depth_alone_does_not_reproduce_full_model_drift",
        )

    def test_execution_lock_when_available(self):
        if not construction.DEFAULT_EXECUTION_LOCK.exists():
            self.skipTest("execution lock not generated")
        lock = construction.load_json(construction.DEFAULT_EXECUTION_LOCK)
        self.assertEqual(lock["authorization"]["lora_enabled_layer_counts"], [1, 36])
        self.assertEqual(lock["authorization"]["fixed_transformer_layers"], 36)
        self.assertEqual(lock["authorization"]["optimizer_steps"], 0)
        for binding in lock["bindings"]:
            path = Path(binding["path"])
            if binding["scope"] == "repository":
                path = ROOT / path
            self.assertEqual(construction.sha256_file(path), binding["sha256"])

    def test_runner_has_backward_without_optimizer_or_generation(self):
        source = (ROOT / "run_rightbrain_qwen3_lora_span_repro_v1.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("nn.value_and_grad", source)
        self.assertNotIn("optimizer.update", source)
        self.assertNotIn("mlx_lm.generate", source)
        self.assertNotIn("save_safetensors", source)

    def test_result_lock_when_available(self):
        path = ROOT / self.prereg["result_paths"]["result_lock"]
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
