#!/usr/bin/env python3
"""Observed-result checks for the Qwen3 length-boundary refinement."""

from __future__ import annotations

import unittest
from pathlib import Path

import build_rightbrain_qwen3_length_boundary_refine_v1 as construction


ROOT = Path(__file__).resolve().parent


class RightBrainQwen3LengthBoundaryRefineV1ResultTest(unittest.TestCase):
    def setUp(self):
        self.prereg = construction.load_json(construction.DEFAULT_PREREGISTRATION)
        self.result = construction.load_json(
            ROOT / self.prereg["result_paths"]["aggregate_json"]
        )

    def test_parent_stable_anchor_is_not_reproduced(self):
        decision = self.result["decision"]
        self.assertFalse(decision["localization_complete"])
        self.assertEqual(
            decision["outcome"],
            "refined_length_boundary_anchor_not_reproduced",
        )
        self.assertFalse(decision["monotonic_across_tested_lengths"])
        self.assertIsNone(decision["bracket"])
        self.assertEqual(
            decision["authorized_next_step"],
            "increase_anchor_repetitions_before_boundary_claim",
        )
        self.assertFalse(decision["authorize_persona_training"])
        self.assertFalse(decision["authorize_production"])

    def test_observed_pattern_refutes_a_simple_length_threshold(self):
        self.assertEqual(
            self.result["stability_by_length"],
            {
                "640": False,
                "656": False,
                "672": False,
                "688": True,
                "704": False,
            },
        )
        for length in (640, 656, 672, 704):
            metrics = self.result["measurements"][str(length)]
            self.assertGreater(metrics["gradient_norm_coefficient_of_variation"], 0.20)
            self.assertGreater(metrics["gradient_norm_max_to_min_ratio"], 2.2)
            self.assertFalse(metrics["gradient_hashes_identical"])
            self.assertEqual(len(set(metrics["losses"])), 1)
        stable = self.result["measurements"]["688"]
        self.assertEqual(stable["gradient_norm_coefficient_of_variation"], 0.0)
        self.assertEqual(stable["gradient_norm_max_to_min_ratio"], 1.0)
        self.assertTrue(stable["gradient_hashes_identical"])

    def test_all_fifty_repeats_preserve_parameters_and_contracts(self):
        for length in construction.LENGTH_LEVELS:
            for repeat in construction.REPEATS:
                path = (
                    ROOT
                    / f"{self.prereg['result_paths']['repeat_prefix']}"
                    f"{length}_tokens_repeat_{repeat}.json"
                )
                row = construction.load_json(path)
                self.assertTrue(row["execution_success"])
                self.assertTrue(row["base_contract"]["exact"])
                self.assertTrue(row["adapter_contract"]["exact"])
                self.assertTrue(row["parameter_integrity"]["unchanged"])
                self.assertEqual(
                    row["batch_contract"]["sha256"],
                    self.prereg["batch_contracts"][str(length)]["sha256"],
                )


if __name__ == "__main__":
    unittest.main()
