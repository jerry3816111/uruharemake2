#!/usr/bin/env python3
"""Observed-result checks kept separate from the frozen execution harness."""

from __future__ import annotations

import unittest
from pathlib import Path

import build_rightbrain_qwen3_block_backend_repro_v1 as construction


ROOT = Path(__file__).resolve().parent


class RightBrainQwen3BlockBackendReproV1ResultTest(unittest.TestCase):
    def test_result_localizes_drift_outside_one_block(self):
        preregistration = construction.load_json(construction.DEFAULT_PREREGISTRATION)
        path = ROOT / preregistration["result_paths"]["aggregate_json"]
        result = construction.load_json(path)
        decision = result["decision"]
        self.assertTrue(decision["localization_complete"])
        self.assertEqual(
            decision["outcome"],
            "reduced_block_does_not_reproduce_full_graph_drift",
        )
        self.assertEqual(
            decision["authorized_next_step"],
            "preregister_layer_count_scaling_localization",
        )
        self.assertFalse(decision["authorize_persona_training"])
        self.assertFalse(decision["authorize_production"])
        for device in ("cpu", "gpu"):
            measurements = result["measurements"][device]
            self.assertEqual(
                measurements["gradient_norm_coefficient_of_variation"], 0.0
            )
            self.assertEqual(measurements["gradient_norm_max_to_min_ratio"], 1.0)
            self.assertTrue(measurements["gradient_hashes_identical"])
            self.assertGreaterEqual(
                measurements["minimum_pairwise_group_profile_cosine"], 0.9999
            )
        cross = result["measurements"]["cross_device"]
        self.assertAlmostEqual(
            cross["mean_gradient_norm_ratio_gpu_over_cpu"], 1.0, delta=0.001
        )
        self.assertGreaterEqual(cross["minimum_group_profile_cosine"], 0.9999)


if __name__ == "__main__":
    unittest.main()
