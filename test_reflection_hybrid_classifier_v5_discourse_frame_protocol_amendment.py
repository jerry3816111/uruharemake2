#!/usr/bin/env python3
"""Validate the pre-inference V5 matched-control correction."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs" / "reflection_hybrid_classifier_v5_discourse_frame_development_preregistration.json"
AMENDMENT = ROOT / "configs" / "reflection_hybrid_classifier_v5_discourse_frame_protocol_amendment.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


class ReflectionDiscourseFrameProtocolAmendmentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prereg = _load(PREREG)
        cls.amendment = _load(AMENDMENT)

    def test_correction_precedes_all_inference(self):
        self.assertEqual(
            self.amendment["timing"],
            "before_harness_merge_and_before_any_model_inference",
        )
        self.assertEqual(self.amendment["model_calls_before_amendment"], 0)

    def test_both_conditions_receive_same_output_budget(self):
        correction = self.amendment["correction"]
        self.assertEqual(
            correction["shared_maximum_output_tokens"],
            self.prereg["generation"]["maximum_output_tokens"],
        )
        self.assertTrue(
            correction["shared_model_dataset_rules_temperature_top_p_seed_context_and_transport"]
        )
        self.assertTrue(correction["shared_fallback_case_ids_and_order"])
        self.assertEqual(correction["total_model_call_count_exact"], 40)

    def test_live_control_must_reproduce_frozen_v3(self):
        gates = self.amendment["live_control_reproduction_gates"]
        self.assertEqual(gates["correct_count_exact"], 29)
        self.assertEqual(gates["prediction_drift_vs_frozen_v3_count_max"], 0)
        self.assertEqual(gates["parse_success_rate_min"], 1.0)
        self.assertEqual(gates["critical_false_positive_count_max"], 0)
        self.assertEqual(gates["fallback_call_count_exact"], 20)

    def test_candidate_capability_thresholds_did_not_get_easier(self):
        original = self.prereg["success_gates"]
        corrected = self.amendment["unchanged_candidate_capability_gates"]
        same_names = {
            "candidate_correct_count_min",
            "candidate_accuracy_min",
            "candidate_semantic_correct_min",
            "candidate_procedural_correct_min",
            "candidate_interpretive_correct_min",
            "candidate_none_correct",
            "critical_false_positive_count_max",
            "parse_success_rate_min",
            "median_fallback_seconds_max",
            "warm_p95_fallback_seconds_max",
        }
        for name in same_names:
            self.assertEqual(corrected[name], original[name])
        self.assertEqual(
            corrected["newly_correct_vs_matched_control_min"],
            original["newly_correct_vs_frozen_control_min"],
        )
        self.assertEqual(
            corrected["regression_vs_matched_control_max"],
            original["regression_vs_frozen_control_max"],
        )

    def test_no_post_result_relaxation_or_runtime_claim(self):
        self.assertFalse(self.amendment["post_result_changes_authorized"])
        self.assertFalse(self.amendment["same_dataset_retest_authorized"])
        self.assertFalse(
            self.amendment["runtime_or_generalization_claim_authorized"]
        )


if __name__ == "__main__":
    unittest.main()
