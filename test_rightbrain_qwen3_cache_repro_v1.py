#!/usr/bin/env python3
"""Contract tests for the Qwen3 Metal free-cache probe."""

from __future__ import annotations

import unittest
from pathlib import Path

import build_rightbrain_qwen3_cache_repro_v1 as construction


ROOT = Path(__file__).resolve().parent


class RightBrainQwen3CacheReproV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not construction.DEFAULT_PREREGISTRATION.exists():
            raise unittest.SkipTest("construction has not been generated")
        cls.prereg = construction.load_json(construction.DEFAULT_PREREGISTRATION)

    def test_cache_mode_is_the_only_causal_variable(self):
        causal = self.prereg["causal_variable"]
        self.assertEqual(causal["name"], "metal_free_cache_mode")
        self.assertEqual(causal["levels"], list(construction.CACHE_MODES))
        self.assertTrue(causal["only_intended_change"])
        probe = self.prereg["exact_probe"]
        self.assertEqual(probe["base_compute_dtype"], "bfloat16")
        self.assertEqual(probe["allocated_sequence_length"], 640)
        self.assertEqual(probe["full_transformer_layers"], 36)
        self.assertEqual(probe["lora_enabled_layers"], 36)
        self.assertEqual(probe["adapter_dtype"], "mlx.core.float32")

    def test_batch_source_and_parent_are_frozen(self):
        batch = self.prereg["batch_contract"]
        self.assertEqual(batch["allocated_tokens"], 640)
        self.assertEqual(batch["shared_prefix_tokens"], 64)
        self.assertEqual(batch["labelled_tokens"], 16)
        source = self.prereg["batch_source"]
        self.assertFalse(source["contains_target_utterance"])
        self.assertFalse(source["contains_benchmark_item_or_answer"])
        parent = self.prereg["evidence_parent"]
        self.assertEqual(construction.sha256_file(ROOT / parent["path"]), parent["sha256"])
        self.assertFalse(parent["observed_bfloat16_stable"])

    def test_official_allocator_evidence_is_explicit(self):
        upstream = self.prereg["upstream_evidence"]
        self.assertEqual(upstream["mlx_version"], "0.32.0")
        self.assertIn("set_cache_limit", upstream["set_cache_limit_docs"])
        self.assertIn("/pull/3630", upstream["metal_war_fix_pr"])
        self.assertIn("does not establish", upstream["scope_note"])

    def test_repetitions_and_safety_are_frozen(self):
        self.assertEqual(
            self.prereg["exact_probe"]["isolated_repetitions_per_level"],
            list(construction.REPEATS),
        )
        boundaries = self.prereg["boundaries"]
        self.assertFalse(boundaries["persona_training"])
        self.assertFalse(boundaries["optimizer_update"])
        self.assertFalse(boundaries["cache_disabled_training_authorization"])

    def test_execution_lock_when_available(self):
        if not construction.DEFAULT_EXECUTION_LOCK.exists():
            self.skipTest("execution lock not generated")
        lock = construction.load_json(construction.DEFAULT_EXECUTION_LOCK)
        authorization = lock["authorization"]
        self.assertEqual(authorization["cache_modes"], list(construction.CACHE_MODES))
        self.assertEqual(authorization["base_compute_dtype"], "bfloat16")
        self.assertEqual(authorization["allocated_sequence_length"], 640)
        self.assertEqual(authorization["repetitions_each"], list(construction.REPEATS))
        for binding in lock["bindings"]:
            path = Path(binding["path"])
            if binding["scope"] == "repository":
                path = ROOT / path
            self.assertEqual(construction.sha256_file(path), binding["sha256"])

    def test_runner_changes_cache_before_model_load_and_never_trains(self):
        source = (ROOT / "run_rightbrain_qwen3_cache_repro_v1.py").read_text(
            encoding="utf-8"
        )
        configure = source.index("cache_contract = _configure_cache(cache_mode)")
        load_model = source.index("model, tokenizer = load(")
        self.assertLess(configure, load_model)
        self.assertIn("mx.set_cache_limit(0)", source)
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
        self.assertFalse(lock["authorization"]["cache_disabled_training"])
        self.assertFalse(lock["authorization"]["persona_training"])


if __name__ == "__main__":
    unittest.main()
