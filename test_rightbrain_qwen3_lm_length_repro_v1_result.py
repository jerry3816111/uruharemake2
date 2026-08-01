#!/usr/bin/env python3
"""Observed-result checks for full-Qwen3 LM length localization."""

from __future__ import annotations

import unittest
from pathlib import Path

import build_rightbrain_qwen3_lm_length_repro_v1 as construction


ROOT = Path(__file__).resolve().parent


class RightBrainQwen3LmLengthReproV1ResultTest(unittest.TestCase):
    def test_long_ignored_suffix_reproduces_global_gradient_scale_drift(self):
        prereg = construction.load_json(construction.DEFAULT_PREREGISTRATION)
        result = construction.load_json(ROOT / prereg["result_paths"]["aggregate_json"])
        decision = result["decision"]
        self.assertTrue(decision["localization_complete"])
        self.assertEqual(
            decision["outcome"],
            "ignored_padding_length_reproduces_gradient_drift",
        )
        self.assertEqual(
            decision["authorized_next_step"],
            "binary_search_allocated_sequence_length",
        )
        self.assertFalse(decision["authorize_persona_training"])
        short = result["measurements"]["64"]
        long = result["measurements"]["800"]
        self.assertEqual(short["gradient_norm_coefficient_of_variation"], 0.0)
        self.assertEqual(short["gradient_norm_max_to_min_ratio"], 1.0)
        self.assertTrue(short["gradient_hashes_identical"])
        self.assertGreater(long["gradient_norm_coefficient_of_variation"], 0.12)
        self.assertGreater(long["gradient_norm_max_to_min_ratio"], 1.33)
        self.assertFalse(long["gradient_hashes_identical"])
        self.assertEqual(len(set(long["losses"])), 1)

        repeats = [
            construction.load_json(
                ROOT
                / f"{prereg['result_paths']['repeat_prefix']}800_tokens_repeat_{repeat}.json"
            )
            for repeat in (1, 2, 3)
        ]
        profiles = [row["gradient"]["profile"] for row in repeats]
        b_groups = [name for name in profiles[0] if name.endswith(".lora_b")]
        a_groups = [name for name in profiles[0] if name.endswith(".lora_a")]
        self.assertTrue(all(profile[name] == 0 for profile in profiles for name in a_groups))
        self.assertTrue(
            all(
                max(profile[name] for profile in profiles)
                / min(profile[name] for profile in profiles)
                > 1.3
                for name in b_groups
            )
        )


if __name__ == "__main__":
    unittest.main()
