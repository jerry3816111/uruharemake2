#!/usr/bin/env python3
"""Observed-result checks for Qwen3 depth localization."""

from __future__ import annotations

import unittest
from pathlib import Path

import build_rightbrain_qwen3_depth_repro_v1 as construction


ROOT = Path(__file__).resolve().parent


class RightBrainQwen3DepthReproV1ResultTest(unittest.TestCase):
    def test_depth_alone_does_not_reproduce_gradient_drift(self):
        prereg = construction.load_json(construction.DEFAULT_PREREGISTRATION)
        result = construction.load_json(ROOT / prereg["result_paths"]["aggregate_json"])
        decision = result["decision"]
        self.assertTrue(decision["localization_complete"])
        self.assertEqual(
            decision["outcome"],
            "depth_alone_does_not_reproduce_full_model_drift",
        )
        self.assertFalse(decision["authorize_persona_training"])
        self.assertFalse(decision["authorize_production"])
        for level in ("1", "36"):
            metrics = result["measurements"][level]
            self.assertEqual(metrics["gradient_norm_coefficient_of_variation"], 0.0)
            self.assertEqual(metrics["gradient_norm_max_to_min_ratio"], 1.0)
            self.assertEqual(metrics["minimum_pairwise_group_profile_cosine"], 1.0)
            self.assertTrue(metrics["gradient_hashes_identical"])
            self.assertEqual(len(set(metrics["losses"])), 1)
        self.assertLess(
            max(result["measurements"]["36"]["peak_memory_bytes"]),
            prereg["exact_probe"]["memory_limit_bytes"],
        )


if __name__ == "__main__":
    unittest.main()
