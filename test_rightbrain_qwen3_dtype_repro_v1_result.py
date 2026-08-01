#!/usr/bin/env python3
"""Observed-result checks for the Qwen3 compute-dtype localization."""

from __future__ import annotations

import unittest
from pathlib import Path

import build_rightbrain_qwen3_dtype_repro_v1 as construction


ROOT = Path(__file__).resolve().parent


class RightBrainQwen3DtypeReproV1ResultTest(unittest.TestCase):
    def setUp(self):
        self.prereg = construction.load_json(construction.DEFAULT_PREREGISTRATION)
        self.result = construction.load_json(
            ROOT / self.prereg["result_paths"]["aggregate_json"]
        )

    def test_float16_does_not_eliminate_observed_drift(self):
        decision = self.result["decision"]
        self.assertTrue(decision["localization_complete"])
        self.assertEqual(
            decision["outcome"],
            "float16_does_not_eliminate_gradient_drift",
        )
        self.assertEqual(
            decision["authorized_next_step"],
            "localize_metal_graph_shape_or_allocator_path",
        )
        self.assertEqual(
            self.result["stability_by_dtype"],
            {"bfloat16": False, "float16": False},
        )
        self.assertFalse(decision["authorize_float16_training"])
        self.assertFalse(decision["authorize_persona_training"])
        self.assertFalse(decision["authorize_production"])
        self.assertFalse(decision["authorize_persona_similarity_claim"])

    def test_float16_reduces_but_does_not_pass_drift_limits(self):
        limits = self.prereg["falsifiable_outcomes"]["within_level_reproducibility"]
        bfloat16 = self.result["measurements"]["bfloat16"]
        float16 = self.result["measurements"]["float16"]
        self.assertAlmostEqual(
            bfloat16["gradient_norm_coefficient_of_variation"],
            0.06285123479328746,
        )
        self.assertAlmostEqual(
            float16["gradient_norm_coefficient_of_variation"],
            0.02901573267069816,
        )
        self.assertLess(
            float16["gradient_norm_coefficient_of_variation"],
            bfloat16["gradient_norm_coefficient_of_variation"],
        )
        self.assertLess(
            float16["gradient_norm_max_to_min_ratio"],
            bfloat16["gradient_norm_max_to_min_ratio"],
        )
        for metrics in (bfloat16, float16):
            self.assertGreater(
                metrics["gradient_norm_coefficient_of_variation"],
                limits["gradient_norm_coefficient_of_variation_maximum"],
            )
            self.assertGreater(
                metrics["gradient_norm_max_to_min_ratio"],
                limits["gradient_norm_max_to_min_ratio_maximum"],
            )
            self.assertFalse(metrics["gradient_hashes_identical"])
            self.assertEqual(len(set(metrics["losses"])), 1)

    def test_all_twenty_repeats_preserve_frozen_contracts(self):
        for dtype_name in construction.DTYPE_LEVELS:
            losses = set()
            for repeat in construction.REPEATS:
                path = (
                    ROOT
                    / f"{self.prereg['result_paths']['repeat_prefix']}"
                    f"{dtype_name}_repeat_{repeat}.json"
                )
                row = construction.load_json(path)
                self.assertTrue(row["execution_success"])
                self.assertTrue(row["original_base_contract"]["exact"])
                self.assertTrue(row["compute_dtype_contract"]["exact"])
                self.assertTrue(row["adapter_contract"]["exact"])
                self.assertTrue(row["gradient"]["all_elements_finite"])
                self.assertTrue(row["parameter_integrity"]["unchanged"])
                self.assertEqual(
                    row["batch_contract"]["sha256"],
                    self.prereg["batch_contract"]["sha256"],
                )
                losses.add(row["loss"])
            self.assertEqual(len(losses), 1)

    def test_result_lock_preserves_all_observations(self):
        lock = construction.load_json(
            ROOT / self.prereg["result_paths"]["result_lock"]
        )
        self.assertEqual(len(lock["result_bindings"]), 22)
        for binding in lock["result_bindings"]:
            path = Path(binding["path"])
            if binding["scope"] == "repository":
                path = ROOT / path
            self.assertEqual(construction.sha256_file(path), binding["sha256"])
        self.assertFalse(lock["authorization"]["float16_training"])
        self.assertFalse(lock["authorization"]["persona_training"])
        self.assertFalse(lock["authorization"]["production_runtime_change"])


if __name__ == "__main__":
    unittest.main()
