#!/usr/bin/env python3
"""Contract tests for full-Qwen3 LM sequence-length localization."""

from __future__ import annotations

import unittest
from pathlib import Path

import build_rightbrain_qwen3_lm_length_repro_v1 as construction


ROOT = Path(__file__).resolve().parent


class RightBrainQwen3LmLengthReproV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not construction.DEFAULT_PREREGISTRATION.exists():
            raise unittest.SkipTest("construction has not been generated")
        cls.prereg = construction.load_json(construction.DEFAULT_PREREGISTRATION)

    def test_allocated_length_is_the_only_causal_variable(self):
        self.assertEqual(self.prereg["causal_variable"]["name"], "allocated_sequence_length")
        self.assertEqual(self.prereg["causal_variable"]["levels"], [64, 800])
        self.assertTrue(self.prereg["causal_variable"]["only_intended_change"])
        self.assertEqual(self.prereg["exact_probe"]["full_transformer_layers"], 36)
        self.assertEqual(self.prereg["exact_probe"]["lora_enabled_layers"], 36)
        self.assertEqual(self.prereg["exact_probe"]["device"], "gpu_metal")

    def test_prefix_labels_model_and_safety_are_frozen(self):
        short = self.prereg["batch_contracts"]["64"]
        long = self.prereg["batch_contracts"]["800"]
        self.assertEqual(short["shared_prefix_tokens"], 64)
        self.assertEqual(long["shared_prefix_tokens"], 64)
        self.assertEqual(short["labelled_tokens"], long["labelled_tokens"])
        self.assertEqual(short["ignored_suffix_tokens"], 0)
        self.assertEqual(long["ignored_suffix_tokens"], 736)
        self.assertTrue(self.prereg["batch_source"]["same_labelled_prefix_across_conditions"])
        self.assertFalse(self.prereg["batch_source"]["contains_target_utterance"])
        self.assertFalse(self.prereg["batch_source"]["contains_benchmark_item_or_answer"])
        self.assertEqual(
            self.prereg["adapter_initialization_contract"]["trainable_tensor_count"],
            504,
        )
        boundaries = self.prereg["boundaries"]
        self.assertFalse(boundaries["persona_training"])
        self.assertFalse(boundaries["optimizer_update"])
        self.assertFalse(boundaries["production_runtime_change"])

    def test_parent_evidence_is_bound(self):
        for parent in self.prereg["evidence_parents"]:
            path = ROOT / parent["path"]
            self.assertEqual(construction.sha256_file(path), parent["sha256"])

    def test_execution_lock_when_available(self):
        if not construction.DEFAULT_EXECUTION_LOCK.exists():
            self.skipTest("execution lock not generated")
        lock = construction.load_json(construction.DEFAULT_EXECUTION_LOCK)
        self.assertEqual(lock["authorization"]["allocated_sequence_lengths"], [64, 800])
        self.assertEqual(lock["authorization"]["fixed_shared_prefix_tokens"], 64)
        self.assertTrue(lock["authorization"]["full_language_model_path"])
        self.assertEqual(lock["authorization"]["optimizer_steps"], 0)
        for binding in lock["bindings"]:
            path = Path(binding["path"])
            if binding["scope"] == "repository":
                path = ROOT / path
            self.assertEqual(construction.sha256_file(path), binding["sha256"])

    def test_runner_has_full_lm_backward_without_training_or_generation(self):
        source = (ROOT / "run_rightbrain_qwen3_lm_length_repro_v1.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("common._completion_loss", source)
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
