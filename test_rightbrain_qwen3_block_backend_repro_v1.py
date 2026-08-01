#!/usr/bin/env python3
"""Contract tests for the Qwen3 block CPU-versus-Metal localization."""

from __future__ import annotations

import unittest
from pathlib import Path

import build_rightbrain_qwen3_block_backend_repro_v1 as construction


ROOT = Path(__file__).resolve().parent


class RightBrainQwen3BlockBackendReproV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not construction.DEFAULT_PREREGISTRATION.exists():
            raise unittest.SkipTest("construction has not been generated")
        cls.preregistration = construction.load_json(construction.DEFAULT_PREREGISTRATION)

    def test_single_causal_variable_and_safety_boundary(self):
        prereg = self.preregistration
        self.assertEqual(prereg["causal_variable"]["name"], "mlx_execution_device")
        self.assertEqual(prereg["causal_variable"]["levels"], ["cpu", "gpu_metal"])
        self.assertTrue(prereg["causal_variable"]["only_intended_change"])
        self.assertEqual(prereg["exact_probe"]["optimizer_steps"], 0)
        self.assertFalse(prereg["exact_probe"]["gradient_checkpointing"])
        self.assertFalse(prereg["boundaries"]["persona_training"])
        self.assertFalse(prereg["boundaries"]["production_runtime_change"])
        self.assertFalse(prereg["boundaries"]["persona_similarity_claim"])

    def test_real_qwen3_block_adapter_and_input_are_frozen(self):
        prereg = self.preregistration
        model = prereg["official_model_contract"]
        self.assertEqual(model["base_model"], "Qwen/Qwen3-4B-Instruct-2507")
        self.assertEqual(model["revision"], "cdbee75f17c01a7cc42f958dc650907174af0554")
        self.assertEqual(prereg["block_contract"]["layer_index"], 0)
        self.assertEqual(prereg["block_contract"]["selected_weight_tensor_count"], 11)
        self.assertEqual(prereg["adapter_contract"]["converted_layers"], 1)
        self.assertEqual(prereg["adapter_contract"]["rank"], 32)
        self.assertEqual(prereg["adapter_contract"]["dropout"], 0.0)
        self.assertEqual(prereg["input_contract"]["shape"], [1, 64, 2560])
        self.assertIn("no_persona_or_benchmark", prereg["input_contract"]["source"])

    def test_falsifiable_outcomes_cover_all_device_states(self):
        classes = self.preregistration["falsifiable_outcomes"]["classifications"]
        self.assertEqual(
            set(classes),
            {
                "cpu_stable_gpu_unstable",
                "cpu_unstable_gpu_unstable",
                "cpu_stable_gpu_stable",
                "cpu_unstable_gpu_stable",
            },
        )

    def test_execution_lock_when_available(self):
        if not construction.DEFAULT_EXECUTION_LOCK.exists():
            self.skipTest("execution lock not generated")
        lock = construction.load_json(construction.DEFAULT_EXECUTION_LOCK)
        self.assertEqual(lock["authorization"]["devices"], ["cpu", "gpu"])
        self.assertEqual(lock["authorization"]["exact_zero_update_repetitions_each"], [1, 2, 3])
        self.assertEqual(lock["authorization"]["optimizer_steps"], 0)
        self.assertFalse(lock["authorization"]["production_runtime_change"])
        for binding in lock["bindings"]:
            path = Path(binding["path"])
            if binding["scope"] == "repository":
                path = ROOT / path
            self.assertTrue(path.is_file(), path)
            self.assertEqual(construction.sha256_file(path), binding["sha256"])

    def test_runner_contains_backward_but_no_training_or_generation(self):
        source = (ROOT / "run_rightbrain_qwen3_block_backend_repro_v1.py").read_text(
            encoding="utf-8"
        )
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
        self.assertFalse(lock["authorization"]["production_runtime_change"])


if __name__ == "__main__":
    unittest.main()
