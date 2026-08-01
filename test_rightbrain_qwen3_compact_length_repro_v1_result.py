#!/usr/bin/env python3
"""Observed-result checks for the Qwen3 512 versus 640 token probe."""

from __future__ import annotations

import collections
import statistics
import unittest
from pathlib import Path

import build_rightbrain_qwen3_compact_length_repro_v1 as construction


ROOT = Path(__file__).resolve().parent


class RightBrainQwen3CompactLengthReproV1ResultTest(unittest.TestCase):
    def setUp(self):
        self.prereg = construction.load_json(construction.DEFAULT_PREREGISTRATION)
        self.result = construction.load_json(
            ROOT / self.prereg["result_paths"]["aggregate_json"]
        )

    def test_512_token_length_does_not_eliminate_drift(self):
        decision = self.result["decision"]
        self.assertTrue(decision["experiment_complete"])
        self.assertEqual(
            decision["outcome"],
            "compact_length_512_does_not_eliminate_drift",
        )
        self.assertEqual(
            decision["authorized_next_step"],
            "reject_512_length_workaround_and_localize_shared_backward_path",
        )
        self.assertEqual(
            self.result["stability_by_length"], {"512": False, "640": False}
        )
        self.assertFalse(decision["authorize_512_token_contract_construction"])
        self.assertFalse(decision["authorize_512_token_training"])
        self.assertFalse(decision["authorize_persona_training"])
        self.assertFalse(decision["authorize_production"])
        self.assertFalse(decision["authorize_persona_similarity_claim"])

    def test_both_lengths_fail_every_preregistered_stability_gate(self):
        limits = self.prereg["falsifiable_outcomes"][
            "within_level_reproducibility"
        ]
        expected = {
            "512": {
                "cv": 1.9753936999558075,
                "ratio": 431635.0379109821,
                "cosine": 0.9968789450519387,
            },
            "640": {
                "cv": 0.10125515822490135,
                "ratio": 1.8316471468849285,
                "cosine": 0.9993122399023376,
            },
        }
        for length, values in expected.items():
            metrics = self.result["measurements"][length]
            self.assertAlmostEqual(
                metrics["gradient_norm_coefficient_of_variation"], values["cv"]
            )
            self.assertAlmostEqual(
                metrics["gradient_norm_max_to_min_ratio"], values["ratio"]
            )
            self.assertAlmostEqual(
                metrics["minimum_pairwise_group_profile_cosine"], values["cosine"]
            )
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
            self.assertEqual(
                metrics["checks"],
                {
                    "cv": False,
                    "ratio": False,
                    "profile_cosine": False,
                    "gradient_hashes_identical": False,
                },
            )

    def test_anomaly_counts_are_not_hidden_by_means(self):
        expected = {
            "512": {"canonical_count": 15, "anomaly_count": 5},
            "640": {"canonical_count": 19, "anomaly_count": 1},
        }
        for length, counts in expected.items():
            metrics = self.result["measurements"][length]
            norm_counts = collections.Counter(metrics["gradient_norms"])
            canonical_norm, canonical_count = norm_counts.most_common(1)[0]
            anomaly_count = sum(
                abs(norm / canonical_norm - 1.0) > 0.02
                for norm in metrics["gradient_norms"]
            )
            self.assertEqual(canonical_count, counts["canonical_count"])
            self.assertEqual(anomaly_count, counts["anomaly_count"])
        self.assertGreater(
            max(self.result["measurements"]["512"]["gradient_norms"]), 3_000_000
        )
        self.assertLess(
            min(self.result["measurements"]["640"]["gradient_norms"]), 5.0
        )

    def test_all_forty_repeats_are_valid_zero_update_observations(self):
        for length in construction.LENGTH_LEVELS:
            losses = set()
            parameter_hashes = set()
            for repeat in construction.REPEATS:
                path = (
                    ROOT
                    / f"{self.prereg['result_paths']['repeat_prefix']}"
                    f"{length}_tokens_repeat_{repeat}.json"
                )
                row = construction.load_json(path)
                self.assertTrue(row["execution_success"])
                self.assertEqual(row["allocated_sequence_length"], length)
                self.assertTrue(row["base_contract"]["exact"])
                self.assertTrue(row["adapter_contract"]["exact"])
                self.assertTrue(row["gradient"]["all_elements_finite"])
                self.assertTrue(row["parameter_integrity"]["unchanged"])
                self.assertEqual(row["batch_contract"]["token_count_from_loss"], 16)
                self.assertEqual(
                    row["batch_contract"]["sha256"],
                    self.prereg["batch_contracts"][str(length)]["sha256"],
                )
                self.assertFalse(row["runtime_contract"]["optimizer_instantiated"])
                self.assertEqual(row["runtime_contract"]["optimizer_steps"], 0)
                losses.add(row["loss"])
                parameter_hashes.add(row["parameter_integrity"]["before_sha256"])
            self.assertEqual(len(losses), 1)
            self.assertEqual(len(parameter_hashes), 1)

    def test_shorter_length_reduces_resources_but_not_training_risk(self):
        short = self.result["measurements"]["512"]
        control = self.result["measurements"]["640"]
        self.assertLess(
            statistics.median(short["durations_seconds"]),
            statistics.median(control["durations_seconds"]),
        )
        self.assertLess(
            statistics.median(short["peak_memory_bytes"]),
            statistics.median(control["peak_memory_bytes"]),
        )
        self.assertFalse(self.result["stability_by_length"]["512"])

    def test_result_lock_preserves_all_observations(self):
        lock = construction.load_json(
            ROOT / self.prereg["result_paths"]["result_lock"]
        )
        self.assertEqual(len(lock["result_bindings"]), 42)
        for binding in lock["result_bindings"]:
            path = Path(binding["path"])
            if binding["scope"] == "repository":
                path = ROOT / path
            self.assertEqual(construction.sha256_file(path), binding["sha256"])
        authorization = lock["authorization"]
        self.assertFalse(
            authorization["semantic_equivalent_512_token_contract_construction"]
        )
        self.assertFalse(authorization["training"])
        self.assertFalse(authorization["persona_training"])
        self.assertFalse(authorization["production_runtime_change"])
        self.assertFalse(authorization["persona_similarity_claim"])


if __name__ == "__main__":
    unittest.main()
