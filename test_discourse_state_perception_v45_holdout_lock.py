#!/usr/bin/env python3

import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCK_PATH = ROOT / "configs" / "discourse_state_perception_v45_holdout_lock.json"


class DiscourseStatePerceptionV45HoldoutLockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))

    def test_all_frozen_hashes_match(self):
        for section in (
            "authorization_provenance",
            "frozen_implementations",
            "frozen_holdout",
        ):
            values = self.lock[section]
            for key, expected in values.items():
                if key.endswith("_sha256"):
                    path = ROOT / values[key.removesuffix("_sha256")]
                    self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)

    def test_development_and_construction_gates_are_bound(self):
        development = json.loads(
            (ROOT / self.lock["authorization_provenance"]["development_analysis"]).read_text()
        )
        audit = json.loads(
            (ROOT / self.lock["frozen_holdout"]["construction_audit"]).read_text()
        )
        self.assertTrue(development["fresh_holdout_authorized"])
        self.assertTrue(audit["construction_gate_passed"])
        self.assertFalse(audit["model_inference_used"])

    def test_holdout_has_48_unique_new_cases_and_eight_balanced_families(self):
        holdout = json.loads(
            (ROOT / self.lock["frozen_holdout"]["dataset"]).read_text()
        )
        self.assertEqual(len(holdout["cases"]), 48)
        self.assertEqual(len({case["id"] for case in holdout["cases"]}), 48)
        families = Counter(case["family"] for case in holdout["cases"])
        self.assertEqual(len(families), 8)
        self.assertTrue(all(count == 6 for count in families.values()))

    def test_decision_requires_absolute_comparison_and_zero_regression(self):
        self.assertEqual(
            self.lock["matched_comparison_gates"]["semantic_regression_count_at_most"],
            0,
        )
        self.assertGreater(
            self.lock["matched_comparison_gates"]["commitment_accuracy_delta_vs_control_at_least"],
            0,
        )
        self.assertFalse(self.lock["shadow_integration_authorized"])
        self.assertFalse(self.lock["physical_vrm_execution_enabled"])
        self.assertFalse(self.lock["holdout_has_been_observed_by_model"])


if __name__ == "__main__":
    unittest.main()
