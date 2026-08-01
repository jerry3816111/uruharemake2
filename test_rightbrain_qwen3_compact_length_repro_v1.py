#!/usr/bin/env python3
"""Contract tests for the Qwen3 512 versus 640 token probe."""

from __future__ import annotations

import unittest
from pathlib import Path

import build_rightbrain_qwen3_compact_length_repro_v1 as construction


ROOT = Path(__file__).resolve().parent


class RightBrainQwen3CompactLengthReproV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not construction.DEFAULT_PREREGISTRATION.exists():
            raise unittest.SkipTest("construction has not been generated")
        cls.prereg = construction.load_json(construction.DEFAULT_PREREGISTRATION)

    def test_allocated_length_is_the_only_causal_variable(self):
        causal = self.prereg["causal_variable"]
        self.assertEqual(causal["name"], "allocated_sequence_length")
        self.assertEqual(causal["levels"], [512, 640])
        self.assertEqual(causal["control"], 640)
        self.assertEqual(causal["treatment"], 512)
        self.assertTrue(causal["only_intended_change"])
        probe = self.prereg["exact_probe"]
        self.assertEqual(probe["base_compute_dtype"], "bfloat16")
        self.assertEqual(probe["full_transformer_layers"], 36)
        self.assertEqual(probe["lora_enabled_layers"], 36)
        self.assertEqual(probe["adapter_dtype"], "mlx.core.float32")

    def test_batches_share_content_labels_and_only_add_ignored_padding(self):
        batches = self.prereg["batch_contracts"]
        for length in ("512", "640"):
            row = batches[length]
            self.assertEqual(row["allocated_tokens"], int(length))
            self.assertEqual(row["shared_prefix_tokens"], 64)
            self.assertEqual(row["labelled_tokens"], 16)
            self.assertEqual(row["ignored_suffix_tokens"], int(length) - 64)
        source = self.prereg["batch_source"]
        self.assertTrue(source["same_labelled_prefix_across_both_levels"])
        self.assertEqual(source["suffix_labels"], -100)
        self.assertFalse(source["contains_target_utterance"])
        self.assertFalse(source["contains_benchmark_item_or_answer"])

    def test_prior_evidence_and_failed_serializer_boundary_are_explicit(self):
        evidence = self.prereg["evidence_parent"]
        cache = evidence["cache_result"]
        self.assertEqual(
            cache["outcome"],
            "disabling_metal_free_cache_does_not_eliminate_drift",
        )
        self.assertFalse(cache["default_cache"]["checks"]["cv"])
        historical = evidence["historical_length_result"]
        self.assertEqual(historical["length_512"]["repetitions"], 5)
        self.assertIn("directional evidence only", historical["limitation"])
        compact = evidence["compact_payload_result"]
        self.assertEqual(compact["observed_active_prompt_token_range"], [369, 408])
        self.assertEqual(compact["decision"], "revert_compact_serializer_experiment")
        self.assertIn("not authorized for reuse", compact["limitation"])
        for record in (cache, historical, compact):
            self.assertEqual(
                construction.sha256_file(ROOT / record["path"]), record["sha256"]
            )

    def test_twenty_isolated_repetitions_and_strict_hash_gate_are_frozen(self):
        probe = self.prereg["exact_probe"]
        self.assertEqual(
            probe["isolated_repetitions_per_level"], list(range(1, 21))
        )
        schedule = probe["balanced_interleaved_execution_schedule"]
        self.assertEqual(len(schedule), 20)
        self.assertEqual(schedule[0]["condition_order"], [640, 512])
        self.assertEqual(schedule[1]["condition_order"], [512, 640])
        self.assertEqual(
            sum(row["condition_order"][0] == 512 for row in schedule), 10
        )
        self.assertEqual(
            sum(row["condition_order"][0] == 640 for row in schedule), 10
        )
        limits = self.prereg["falsifiable_outcomes"][
            "within_level_reproducibility"
        ]
        self.assertTrue(limits["gradient_hashes_must_be_identical"])
        self.assertEqual(
            limits["gradient_norm_coefficient_of_variation_maximum"], 0.005
        )
        self.assertEqual(limits["gradient_norm_max_to_min_ratio_maximum"], 1.02)

    def test_positive_result_cannot_authorize_training_or_runtime(self):
        authorization = self.prereg["success_authorization"]
        self.assertEqual(
            authorization["maximum_positive_next_step"],
            "preregister_semantic_equivalent_512_token_contract_construction",
        )
        self.assertFalse(authorization["persona_training"])
        self.assertFalse(authorization["runtime_activation"])
        self.assertFalse(authorization["persona_similarity_claim"])
        boundaries = self.prereg["boundaries"]
        self.assertFalse(boundaries["safe_training_length_claim"])
        self.assertFalse(boundaries["compact_serializer_adoption"])

    def test_execution_lock_when_available(self):
        if not construction.DEFAULT_EXECUTION_LOCK.exists():
            self.skipTest("execution lock not generated")
        lock = construction.load_json(construction.DEFAULT_EXECUTION_LOCK)
        authorization = lock["authorization"]
        self.assertEqual(authorization["allocated_sequence_lengths"], [512, 640])
        self.assertEqual(authorization["repetitions_each"], list(range(1, 21)))
        self.assertEqual(
            authorization["balanced_interleaved_execution_schedule"],
            construction.EXECUTION_SCHEDULE,
        )
        self.assertEqual(authorization["optimizer_steps"], 0)
        for binding in lock["bindings"]:
            path = Path(binding["path"])
            if binding["scope"] == "repository":
                path = ROOT / path
            self.assertEqual(construction.sha256_file(path), binding["sha256"])

    def test_runner_never_updates_saves_or_generates(self):
        source = (
            ROOT / "run_rightbrain_qwen3_compact_length_repro_v1.py"
        ).read_text(encoding="utf-8")
        self.assertIn("nn.value_and_grad", source)
        self.assertNotIn("optimizer.update", source)
        self.assertNotIn("mlx_lm.generate", source)
        self.assertNotIn("save_safetensors", source)
        self.assertIn('"optimizer_steps": 0', source)


if __name__ == "__main__":
    unittest.main()
