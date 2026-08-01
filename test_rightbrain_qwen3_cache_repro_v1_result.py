#!/usr/bin/env python3
"""Observed-result checks for the Qwen3 Metal free-cache localization."""

from __future__ import annotations

import unittest
from pathlib import Path

import build_rightbrain_qwen3_cache_repro_v1 as construction


ROOT = Path(__file__).resolve().parent


class RightBrainQwen3CacheReproV1ResultTest(unittest.TestCase):
    def setUp(self):
        self.prereg = construction.load_json(construction.DEFAULT_PREREGISTRATION)
        self.result = construction.load_json(
            ROOT / self.prereg["result_paths"]["aggregate_json"]
        )

    def test_disabling_free_cache_does_not_eliminate_drift(self):
        decision = self.result["decision"]
        self.assertTrue(decision["experiment_complete"])
        self.assertEqual(
            decision["outcome"],
            "disabling_metal_free_cache_does_not_eliminate_drift",
        )
        self.assertEqual(
            decision["authorized_next_step"],
            "localize_command_buffer_or_kernel_dispatch_path",
        )
        self.assertEqual(
            self.result["stability_by_cache_mode"],
            {"default_cache": False, "disabled_cache": False},
        )
        self.assertFalse(decision["authorize_cache_disabled_training"])
        self.assertFalse(decision["authorize_persona_training"])
        self.assertFalse(decision["authorize_production"])
        self.assertFalse(decision["authorize_persona_similarity_claim"])

    def test_both_modes_fail_preregistered_stability_limits(self):
        limits = self.prereg["falsifiable_outcomes"]["within_level_reproducibility"]
        default = self.result["measurements"]["default_cache"]
        disabled = self.result["measurements"]["disabled_cache"]
        self.assertAlmostEqual(
            default["gradient_norm_coefficient_of_variation"],
            0.11294782346433253,
        )
        self.assertAlmostEqual(
            disabled["gradient_norm_coefficient_of_variation"],
            0.2201410699770045,
        )
        self.assertGreater(
            disabled["gradient_norm_coefficient_of_variation"],
            default["gradient_norm_coefficient_of_variation"],
        )
        self.assertGreater(
            disabled["gradient_norm_max_to_min_ratio"],
            default["gradient_norm_max_to_min_ratio"],
        )
        for metrics in (default, disabled):
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

    def test_all_twenty_repeats_apply_cache_and_preserve_parameters(self):
        for cache_mode in construction.CACHE_MODES:
            losses = set()
            for repeat in construction.REPEATS:
                path = (
                    ROOT
                    / f"{self.prereg['result_paths']['repeat_prefix']}"
                    f"{cache_mode}_repeat_{repeat}.json"
                )
                row = construction.load_json(path)
                self.assertTrue(row["execution_success"])
                self.assertTrue(row["base_contract"]["exact"])
                self.assertTrue(row["compute_dtype_contract"]["exact"])
                self.assertTrue(row["adapter_contract"]["exact"])
                self.assertTrue(row["gradient"]["all_elements_finite"])
                self.assertTrue(row["parameter_integrity"]["unchanged"])
                self.assertEqual(
                    row["batch_contract"]["sha256"],
                    self.prereg["batch_contract"]["sha256"],
                )
                if cache_mode == "disabled_cache":
                    self.assertTrue(row["cache_contract"]["disabled"])
                    self.assertEqual(row["cache_contract"]["target_limit_bytes"], 0)
                    self.assertEqual(row["resource"]["mlx_cache_memory_bytes"], 0)
                else:
                    self.assertFalse(row["cache_contract"]["disabled"])
                    self.assertGreater(row["cache_contract"]["target_limit_bytes"], 0)
                    self.assertGreater(row["resource"]["mlx_cache_memory_bytes"], 0)
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
        self.assertFalse(lock["authorization"]["cache_disabled_training"])
        self.assertFalse(lock["authorization"]["persona_training"])
        self.assertFalse(lock["authorization"]["production_runtime_change"])


if __name__ == "__main__":
    unittest.main()
