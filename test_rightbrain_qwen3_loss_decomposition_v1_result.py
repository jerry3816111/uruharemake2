#!/usr/bin/env python3
"""Result tests for the frozen Qwen3 loss-component localization."""

from __future__ import annotations

import unittest
from pathlib import Path

import build_rightbrain_qwen3_loss_decomposition_v1 as construction


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "reports/rightbrain_qwen3_loss_decomposition_v1_result.json"
RESULT_LOCK = (
    ROOT / "configs/rightbrain_qwen3_loss_decomposition_v1_result_lock.json"
)


class RightBrainQwen3LossDecompositionV1ResultTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = construction.load_json(RESULT)
        cls.prereg = construction.load_json(construction.DEFAULT_PREREGISTRATION)

    def test_all_fifty_four_isolated_repetitions_completed(self):
        self.assertTrue(self.result["decision"]["experiment_complete"])
        self.assertTrue(self.result["checks"]["all_repetitions_complete"])
        self.assertEqual(len(self.result["inputs"]["repeats"]), 54)
        for mode in construction.LOSS_MODES:
            metrics = self.result["measurements"][mode]
            self.assertEqual(len(metrics["gradient_norms"]), 18)
            self.assertEqual(len(metrics["gradient_hashes"]), 18)
            self.assertEqual(len(metrics["losses"]), 18)
            self.assertEqual(len(set(metrics["losses"])), 1)
            self.assertTrue(self.result["checks"][f"{mode}_contracts_exact"])

    def test_batch_exactly_matches_parent_512_token_control(self):
        parent = construction.load_json(construction.PARENT_PREREGISTRATION)
        self.assertEqual(
            self.prereg["batch_contract"], parent["batch_contracts"]["512"]
        )
        self.assertEqual(
            self.prereg["batch_source"]["dataset_sha256"],
            parent["batch_source"]["dataset_sha256"],
        )

    def test_all_loss_components_are_unstable(self):
        self.assertEqual(
            self.result["stability_by_loss_mode"],
            {mode: False for mode in construction.LOSS_MODES},
        )
        self.assertEqual(
            self.result["decision"]["outcome"],
            "drift_precedes_loss_decomposition_or_is_in_shared_model_backward",
        )
        self.assertEqual(
            self.result["decision"]["authorized_next_step"],
            "localize_tied_lm_head_or_shared_transformer_backward",
        )

    def test_observed_instability_exceeds_frozen_limits(self):
        limits = self.prereg["falsifiable_outcomes"][
            "within_level_reproducibility"
        ]
        for mode in construction.LOSS_MODES:
            metrics = self.result["measurements"][mode]
            self.assertGreater(
                metrics["gradient_norm_coefficient_of_variation"],
                limits["gradient_norm_coefficient_of_variation_maximum"],
            )
            self.assertGreater(
                metrics["gradient_norm_max_to_min_ratio"],
                limits["gradient_norm_max_to_min_ratio_maximum"],
            )
            self.assertLess(
                metrics["minimum_pairwise_group_profile_cosine"],
                limits["minimum_pairwise_group_profile_cosine"],
            )
            self.assertFalse(metrics["gradient_hashes_identical"])
        self.assertGreater(
            max(
                self.result["measurements"]["masked_cross_entropy"][
                    "gradient_norms"
                ]
            ),
            1_000_000,
        )
        self.assertGreater(
            max(
                self.result["measurements"]["logsumexp_only"]["gradient_norms"]
            ),
            1_000_000,
        )

    def test_every_repeat_kept_parameters_unchanged(self):
        for binding in self.result["inputs"]["repeats"]:
            path = ROOT / binding["path"]
            self.assertEqual(construction.sha256_file(path), binding["sha256"])
            row = construction.load_json(path)
            self.assertTrue(row["execution_success"])
            self.assertTrue(row["gradient"]["all_elements_finite"])
            self.assertTrue(row["parameter_integrity"]["unchanged"])
            self.assertEqual(row["runtime_contract"]["optimizer_steps"], 0)

    def test_result_authorizes_only_further_localization(self):
        decision = self.result["decision"]
        self.assertFalse(decision["authorize_training"])
        self.assertFalse(decision["authorize_persona_training"])
        self.assertFalse(decision["authorize_production"])
        self.assertFalse(decision["authorize_persona_similarity_claim"])

    def test_result_lock_binds_all_outputs(self):
        lock = construction.load_json(RESULT_LOCK)
        self.assertEqual(lock["decision"], self.result["decision"])
        self.assertEqual(len(lock["result_bindings"]), 56)
        for binding in lock["result_bindings"]:
            path = Path(binding["path"])
            if binding["scope"] == "repository":
                path = ROOT / path
            self.assertEqual(construction.sha256_file(path), binding["sha256"])
        self.assertTrue(all(value is False for value in lock["authorization"].values()))


if __name__ == "__main__":
    unittest.main()
