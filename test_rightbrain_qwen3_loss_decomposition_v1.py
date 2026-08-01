#!/usr/bin/env python3
"""Contract tests for the Qwen3 loss-component localization."""

from __future__ import annotations

import unittest
from pathlib import Path

import mlx.core as mx

import build_rightbrain_qwen3_loss_decomposition_v1 as construction
import run_rightbrain_qwen3_loss_decomposition_v1 as runner


ROOT = Path(__file__).resolve().parent


class RightBrainQwen3LossDecompositionV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not construction.DEFAULT_PREREGISTRATION.exists():
            raise unittest.SkipTest("construction has not been generated")
        cls.prereg = construction.load_json(construction.DEFAULT_PREREGISTRATION)

    def test_loss_component_is_the_only_causal_variable(self):
        causal = self.prereg["causal_variable"]
        self.assertEqual(causal["name"], "loss_component")
        self.assertEqual(causal["levels"], list(construction.LOSS_MODES))
        self.assertTrue(causal["only_intended_change"])
        self.assertEqual(
            causal["masked_cross_entropy"], "logsumexp(logits) - target_score"
        )
        probe = self.prereg["exact_probe"]
        self.assertEqual(probe["allocated_sequence_length"], 512)
        self.assertEqual(probe["full_transformer_layers"], 36)
        self.assertEqual(probe["lora_enabled_layers"], 36)
        self.assertEqual(probe["base_compute_dtype"], "bfloat16")

    def test_installed_mlx_loss_decomposition_is_bound(self):
        upstream = self.prereg["upstream_implementation"]
        self.assertEqual(upstream["mlx_version"], "0.32.0")
        source = upstream["losses_source"]
        path = Path(source["path"])
        self.assertEqual(construction.sha256_file(path), source["sha256"])
        text = path.read_text(encoding="utf-8")
        self.assertIn("logsumexp_logits = mx.logsumexp", text)
        self.assertIn("loss = logsumexp_logits - score", text)

    def test_parent_and_reduced_path_evidence_are_frozen(self):
        evidence = self.prereg["evidence_parent"]
        full = evidence["full_lm_512_result"]
        self.assertEqual(
            full["outcome"], "compact_length_512_does_not_eliminate_drift"
        )
        self.assertFalse(full["metrics"]["checks"]["cv"])
        reduced = evidence["transformer_without_lm_head_or_loss_result"]
        self.assertTrue(reduced["thirty_six_layer_stable"])
        for record in (full, reduced):
            self.assertEqual(
                construction.sha256_file(ROOT / record["path"]), record["sha256"]
            )

    def test_batch_is_synthetic_and_contains_no_persona_or_benchmark_data(self):
        batch = self.prereg["batch_contract"]
        self.assertEqual(batch["allocated_tokens"], 512)
        self.assertEqual(batch["shared_prefix_tokens"], 64)
        self.assertEqual(batch["labelled_tokens"], 16)
        source = self.prereg["batch_source"]
        self.assertTrue(source["synthetic_source_independent"])
        self.assertFalse(source["contains_target_utterance"])
        self.assertFalse(source["contains_benchmark_item_or_answer"])

    def test_eighteen_repeats_have_balanced_condition_positions(self):
        probe = self.prereg["exact_probe"]
        self.assertEqual(
            probe["isolated_repetitions_per_level"], list(construction.REPEATS)
        )
        schedule = probe["fully_counterbalanced_execution_schedule"]
        self.assertEqual(len(schedule), 18)
        self.assertEqual(len({tuple(row["condition_order"]) for row in schedule}), 6)
        self.assertEqual(
            probe["position_counts_by_condition"],
            {mode: [6, 6, 6] for mode in construction.LOSS_MODES},
        )

    def test_loss_components_exactly_reconstruct_masked_cross_entropy(self):
        logits = mx.array(
            [
                [
                    [0.1, 0.2, 0.3, 0.4],
                    [0.4, 0.3, 0.2, 0.1],
                    [0.2, 0.4, 0.1, 0.3],
                ]
            ]
        )

        class FixedModel:
            def __call__(self, inputs):
                self.inputs = inputs
                return logits

        batch = mx.array([[3, 1, 2, 0]])
        labels = mx.array([[-100, 1, 2, -100]])
        values = {}
        for mode in construction.LOSS_MODES:
            loss, token_count = runner._decomposed_loss(
                FixedModel(), batch, labels, loss_mode=mode
            )
            mx.eval(loss, token_count)
            values[mode] = float(loss.item())
            self.assertEqual(int(token_count.item()), 2)
        self.assertAlmostEqual(
            values["masked_cross_entropy"],
            values["target_score_only"] + values["logsumexp_only"],
            places=6,
        )

    def test_strict_stability_and_safety_gates_are_frozen(self):
        limits = self.prereg["falsifiable_outcomes"][
            "within_level_reproducibility"
        ]
        self.assertEqual(
            limits["gradient_norm_coefficient_of_variation_maximum"], 0.005
        )
        self.assertEqual(limits["gradient_norm_max_to_min_ratio_maximum"], 1.02)
        self.assertTrue(limits["gradient_hashes_must_be_identical"])
        authorization = self.prereg["success_authorization"]
        self.assertFalse(authorization["persona_training"])
        self.assertFalse(authorization["runtime_activation"])
        self.assertFalse(authorization["persona_similarity_claim"])

    def test_execution_lock_when_available(self):
        if not construction.DEFAULT_EXECUTION_LOCK.exists():
            self.skipTest("execution lock not generated")
        lock = construction.load_json(construction.DEFAULT_EXECUTION_LOCK)
        authorization = lock["authorization"]
        self.assertEqual(authorization["loss_modes"], list(construction.LOSS_MODES))
        self.assertEqual(authorization["repetitions_each"], list(construction.REPEATS))
        self.assertEqual(
            authorization["fully_counterbalanced_execution_schedule"],
            construction.EXECUTION_SCHEDULE,
        )
        self.assertEqual(authorization["optimizer_steps"], 0)
        for binding in lock["bindings"]:
            path = Path(binding["path"])
            if binding["scope"] == "repository":
                path = ROOT / path
            self.assertEqual(construction.sha256_file(path), binding["sha256"])

    def test_runner_has_exact_loss_branches_and_never_trains(self):
        source = (ROOT / "run_rightbrain_qwen3_loss_decomposition_v1.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("nn.losses.cross_entropy", source)
        self.assertIn("mx.take_along_axis", source)
        self.assertIn("mx.logsumexp", source)
        self.assertIn("nn.value_and_grad", source)
        self.assertNotIn("optimizer.update", source)
        self.assertNotIn("mlx_lm.generate", source)
        self.assertNotIn("save_safetensors", source)


if __name__ == "__main__":
    unittest.main()
