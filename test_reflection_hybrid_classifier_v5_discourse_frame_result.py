#!/usr/bin/env python3
"""Verify the frozen negative V5 discourse-frame development result."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from analyze_reflection_hybrid_classifier_v5_discourse_frame_development import (
    analyze,
)


ROOT = Path(__file__).resolve().parent
LOCK_PATH = ROOT / "configs" / "reflection_hybrid_classifier_v5_discourse_frame_result_lock.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReflectionDiscourseFrameResultTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = _load(LOCK_PATH)
        cls.analysis = _load(
            ROOT / cls.lock["frozen_artifacts"]["analysis_json"]
        )
        cls.raw = _load(ROOT / cls.lock["frozen_artifacts"]["raw_result"])

    def test_result_artifact_hashes_are_frozen(self):
        for name in (
            "preregistration",
            "protocol_amendment",
            "harness_lock",
            "raw_result",
            "analysis_json",
            "analysis_md",
        ):
            path = ROOT / self.lock["frozen_artifacts"][name]
            self.assertEqual(
                _sha256(path), self.lock["frozen_artifacts"][f"{name}_sha256"]
            )

    def test_independent_analyzer_exactly_reproduces_saved_result(self):
        regenerated = analyze(
            ROOT / self.lock["frozen_artifacts"]["raw_result"]
        )
        regenerated.pop("generated_at")
        saved = dict(self.analysis)
        saved.pop("generated_at")
        self.assertEqual(regenerated, saved)

    def test_live_control_is_matched_and_reproduces_frozen_v3(self):
        result = self.analysis["matched_result"]
        self.assertEqual(result["frozen_control_correct_count"], 29)
        self.assertEqual(result["live_control_correct_count"], 29)
        self.assertEqual(result["live_control_prediction_drift_count"], 0)
        self.assertEqual(result["live_control_parse_success_rate"], 1.0)
        self.assertEqual(result["live_control_critical_false_positive_count"], 0)

    def test_candidate_improves_positive_recall_but_fails_safety(self):
        result = self.analysis["matched_result"]
        self.assertEqual(result["candidate_correct_count"], 30)
        self.assertEqual(result["candidate_accuracy"], 0.9375)
        self.assertEqual(
            self.lock["matched_result"]["delta_display"],
            "+3.13 percentage points",
        )
        self.assertEqual(result["newly_correct_count"], 3)
        self.assertEqual(result["regression_count"], 2)
        self.assertEqual(result["critical_false_positive_count"], 2)
        for label in ("semantic", "procedural", "interpretive"):
            self.assertEqual(result["class_metrics"][label]["correct"], 8)
        self.assertEqual(result["class_metrics"]["none"]["correct"], 6)
        self.assertFalse(result["all_gates_pass"])

    def test_transport_and_provenance_are_complete(self):
        self.assertEqual(self.raw["model_calls"], 40)
        self.assertEqual(len(self.raw["live_control_fallback_rows"]), 20)
        self.assertEqual(len(self.raw["candidate_fallback_rows"]), 20)
        self.assertTrue(
            all(
                row["transport_attempts"] == 1
                for row in self.raw["live_control_fallback_rows"]
                + self.raw["candidate_fallback_rows"]
            )
        )
        self.assertFalse(self.raw["gold_label_passed_to_model"])
        self.assertFalse(self.raw["fresh_v4_holdout_loaded"])
        self.assertFalse(self.raw["runtime_memory_write_performed"])

    def test_failure_decision_and_evidence_limits_are_enforced(self):
        self.assertEqual(
            self.analysis["decision"],
            "freeze_negative_result_and_abandon_exact_discourse_frame_contract",
        )
        self.assertFalse(self.lock["same_dataset_retest_authorized"])
        self.assertFalse(self.lock["fresh_holdout_authorized"])
        for name in (
            "runtime_memory_write_authorized",
            "runtime_shadow_authorized",
            "official_benchmark_claim_authorized",
            "cross_corpus_generalization_claim_authorized",
            "broad_human_likeness_claim_authorized",
        ):
            self.assertFalse(self.lock[name])


if __name__ == "__main__":
    unittest.main()
