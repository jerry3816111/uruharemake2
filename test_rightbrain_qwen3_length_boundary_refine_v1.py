#!/usr/bin/env python3
"""Contract tests for the Qwen3 640-704 length-boundary refinement."""

from __future__ import annotations

import unittest
from pathlib import Path

import build_rightbrain_qwen3_length_boundary_refine_v1 as construction


ROOT = Path(__file__).resolve().parent


class RightBrainQwen3LengthBoundaryRefineV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not construction.DEFAULT_PREREGISTRATION.exists():
            raise unittest.SkipTest("construction has not been generated")
        cls.prereg = construction.load_json(construction.DEFAULT_PREREGISTRATION)

    def test_length_is_the_only_causal_variable(self):
        causal = self.prereg["causal_variable"]
        self.assertEqual(causal["name"], "allocated_sequence_length")
        self.assertEqual(causal["levels"], list(construction.LENGTH_LEVELS))
        self.assertTrue(causal["only_intended_change"])
        self.assertEqual(self.prereg["exact_probe"]["full_transformer_layers"], 36)
        self.assertEqual(self.prereg["exact_probe"]["lora_enabled_layers"], 36)

    def test_contracts_share_prefix_labels_and_ignored_suffix(self):
        contracts = self.prereg["batch_contracts"]
        self.assertEqual({row["labelled_tokens"] for row in contracts.values()}, {16})
        for length in construction.LENGTH_LEVELS:
            row = contracts[str(length)]
            self.assertEqual(row["allocated_tokens"], length)
            self.assertEqual(row["shared_prefix_tokens"], 64)
            self.assertEqual(row["ignored_suffix_tokens"], length - 64)
        source = self.prereg["batch_source"]
        self.assertTrue(source["same_labelled_prefix_across_all_levels"])
        self.assertFalse(source["contains_target_utterance"])
        self.assertFalse(source["contains_benchmark_item_or_answer"])

    def test_ten_isolated_repetitions_and_boundaries_are_frozen(self):
        self.assertEqual(
            self.prereg["exact_probe"]["isolated_repetitions_per_level"],
            list(construction.REPEATS),
        )
        self.assertEqual(self.prereg["exact_probe"]["optimizer_steps"], 0)
        boundaries = self.prereg["boundaries"]
        self.assertFalse(boundaries["persona_training"])
        self.assertFalse(boundaries["safe_training_length_claim"])
        self.assertFalse(boundaries["production_runtime_change"])

    def test_parent_evidence_is_bound_and_authorized(self):
        parent = self.prereg["evidence_parent"]
        self.assertEqual(construction.sha256_file(ROOT / parent["path"]), parent["sha256"])
        self.assertEqual(parent["authorized_next_step"], "refine_allocated_length_bracket")
        self.assertEqual(
            parent["bracket"],
            {
                "highest_tested_stable_length": 640,
                "lowest_tested_unstable_length": 704,
            },
        )

    def test_execution_lock_when_available(self):
        if not construction.DEFAULT_EXECUTION_LOCK.exists():
            self.skipTest("execution lock not generated")
        lock = construction.load_json(construction.DEFAULT_EXECUTION_LOCK)
        authorization = lock["authorization"]
        self.assertEqual(
            authorization["allocated_sequence_lengths"],
            list(construction.LENGTH_LEVELS),
        )
        self.assertEqual(authorization["repetitions_each"], list(construction.REPEATS))
        self.assertEqual(authorization["optimizer_steps"], 0)
        for binding in lock["bindings"]:
            path = Path(binding["path"])
            if binding["scope"] == "repository":
                path = ROOT / path
            self.assertEqual(construction.sha256_file(path), binding["sha256"])

    def test_runner_has_backward_without_training_or_generation(self):
        source = (ROOT / "run_rightbrain_qwen3_length_boundary_refine_v1.py").read_text(
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
