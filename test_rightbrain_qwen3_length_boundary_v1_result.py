#!/usr/bin/env python3
"""Observed-result checks for the Qwen3 allocated-length boundary sweep."""

from __future__ import annotations

import unittest
from pathlib import Path

import build_rightbrain_qwen3_length_boundary_v1 as construction


ROOT = Path(__file__).resolve().parent


class RightBrainQwen3LengthBoundaryV1ResultTest(unittest.TestCase):
    def test_boundary_is_localized_between_640_and_704_tokens(self):
        prereg = construction.load_json(construction.DEFAULT_PREREGISTRATION)
        result = construction.load_json(ROOT / prereg["result_paths"]["aggregate_json"])
        decision = result["decision"]
        self.assertTrue(decision["localization_complete"])
        self.assertEqual(
            decision["outcome"],
            "allocated_length_instability_bracket_localized",
        )
        self.assertTrue(decision["monotonic_across_tested_lengths"])
        self.assertEqual(
            decision["bracket"],
            {
                "highest_tested_stable_length": 640,
                "lowest_tested_unstable_length": 704,
            },
        )
        self.assertEqual(
            decision["authorized_next_step"],
            "refine_allocated_length_bracket",
        )
        self.assertFalse(decision["authorize_persona_training"])
        self.assertFalse(decision["authorize_production"])

    def test_shorter_graphs_are_exact_and_longer_graphs_drift(self):
        prereg = construction.load_json(construction.DEFAULT_PREREGISTRATION)
        result = construction.load_json(ROOT / prereg["result_paths"]["aggregate_json"])
        expected_stability = {
            "64": True,
            "256": True,
            "512": True,
            "640": True,
            "704": False,
            "768": False,
            "800": False,
        }
        self.assertEqual(result["stability_by_length"], expected_stability)
        for length in (64, 256, 512, 640):
            metrics = result["measurements"][str(length)]
            self.assertEqual(metrics["gradient_norm_coefficient_of_variation"], 0.0)
            self.assertEqual(metrics["gradient_norm_max_to_min_ratio"], 1.0)
            self.assertTrue(metrics["gradient_hashes_identical"])
        for length in (704, 768, 800):
            metrics = result["measurements"][str(length)]
            self.assertGreater(metrics["gradient_norm_coefficient_of_variation"], 0.24)
            self.assertGreater(metrics["gradient_norm_max_to_min_ratio"], 2.2)
            self.assertFalse(metrics["gradient_hashes_identical"])
            self.assertEqual(len(set(metrics["losses"])), 1)

    def test_every_repeat_keeps_parameters_and_frozen_contracts(self):
        prereg = construction.load_json(construction.DEFAULT_PREREGISTRATION)
        for length in construction.LENGTH_LEVELS:
            for repeat in construction.REPEATS:
                path = (
                    ROOT
                    / f"{prereg['result_paths']['repeat_prefix']}"
                    f"{length}_tokens_repeat_{repeat}.json"
                )
                row = construction.load_json(path)
                self.assertTrue(row["execution_success"])
                self.assertTrue(row["base_contract"]["exact"])
                self.assertTrue(row["adapter_contract"]["exact"])
                self.assertTrue(row["parameter_integrity"]["unchanged"])
                self.assertEqual(
                    row["batch_contract"]["sha256"],
                    prereg["batch_contracts"][str(length)]["sha256"],
                )


if __name__ == "__main__":
    unittest.main()
