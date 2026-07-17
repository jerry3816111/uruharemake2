#!/usr/bin/env python3
"""Verify the frozen negative role-separated consolidation V3 result."""

from __future__ import annotations

import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path

import analyze_consolidation_admission_v3_role_separated_development as analyzer


ROOT = Path(__file__).resolve().parent
LOCK_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_v3_role_separated_result_lock.json"
)
RAW_PATH = (
    ROOT
    / "reports"
    / "consolidation_admission_v3_role_separated_development_raw.json"
)
ANALYSIS_PATH = (
    ROOT
    / "reports"
    / "consolidation_admission_v3_role_separated_development_analysis.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ConsolidationAdmissionV3ResultTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = _load(LOCK_PATH)
        cls.raw = _load(RAW_PATH)
        cls.analysis = _load(ANALYSIS_PATH)
        cls.result = cls.analysis["matched_result"]

    def test_result_artifact_hashes_are_frozen(self):
        frozen = self.lock["frozen_artifacts"]
        for name in (
            "raw_result",
            "analysis_json",
            "analysis_markdown",
            "diagnostic_zh",
            "preregistration",
            "harness_lock",
            "dataset",
            "result_test",
        ):
            self.assertEqual(
                _sha256(ROOT / frozen[name]),
                frozen[f"{name}_sha256"],
            )

    def test_independent_analyzer_reproduces_saved_result(self):
        recomputed = analyzer.analyze(RAW_PATH)
        self.assertEqual(
            recomputed["matched_result"], self.analysis["matched_result"]
        )
        self.assertEqual(recomputed["decision"], self.analysis["decision"])
        for key in (
            "same_dataset_retest_authorized",
            "post_admission_generation_pilot_authorized",
            "single_call_qwen25_7b_frame_simplification_continuation_authorized",
            "runtime_memory_write_authorized",
            "runtime_shadow_authorized",
            "fresh_holdout_authorized",
            "broad_human_likeness_claim_authorized",
        ):
            self.assertEqual(recomputed[key], self.analysis[key])

    def test_collection_provenance_is_complete_and_runtime_safe(self):
        self.assertEqual(self.raw["runner_branch"], "main")
        self.assertEqual(
            self.raw["runner_commit"], self.lock["harness_merge_commit"]
        )
        self.assertEqual(self.raw["model_calls"], 36)
        self.assertEqual(self.raw["transport_attempts_made"], 36)
        self.assertEqual(len(self.raw["control_rows"]), 18)
        self.assertEqual(len(self.raw["candidate_rows"]), 18)
        self.assertFalse(self.raw["gold_fields_passed_to_model"])
        self.assertFalse(self.raw["runtime_memory_write_performed"])

    def test_failure_is_small_net_gain_with_regressions(self):
        self.assertFalse(self.result["all_gates_pass"])
        self.assertEqual(self.result["control"]["correct_count"], 9)
        self.assertEqual(self.result["candidate"]["correct_count"], 10)
        self.assertEqual(self.result["net_correct_gain_vs_control"], 1)
        self.assertEqual(self.result["newly_correct_count"], 3)
        self.assertEqual(self.result["regression_count"], 2)
        self.assertEqual(
            self.result["class_metrics"]["wisdom"]["candidate_correct"], 3
        )
        self.assertEqual(
            self.result["class_metrics"]["procedural"]["candidate_correct"], 2
        )
        self.assertEqual(
            self.result["class_metrics"]["none"]["candidate_correct"], 5
        )
        self.assertEqual(
            self.result["candidate_false_long_term_write_count"], 1
        )
        self.assertEqual(
            self.result["candidate_missed_long_term_write_count"], 6
        )

    def test_kind_basis_confusion_and_transport_failures_are_preserved(self):
        rows = self.raw["candidate_rows"]
        errors = Counter(row["parse_error"] or "none" for row in rows)
        self.assertEqual(
            errors,
            Counter(
                {
                    "none": 12,
                    "invalid_memory_kind": 2,
                    "tool_call_count": 2,
                    "index_contract": 2,
                }
            ),
        )
        procedural_gold_ids = {
            row["id"]
            for row in self.result["matched_rows"]
            if row["expected_target"] == "procedural"
        }
        procedural_raw = [
            row for row in rows if row["id"] in procedural_gold_ids
        ]
        self.assertEqual(
            Counter(row["memory_kind"] for row in procedural_raw),
            Counter({"procedural": 6}),
        )
        self.assertEqual(
            Counter(row["persistence_basis"] for row in procedural_raw),
            Counter(
                {
                    "repeated_pattern": 4,
                    "explicit_future_policy": 2,
                }
            ),
        )
        self.assertEqual(
            self.result["candidate"]["semantic_frame_exact_count"], 7
        )
        self.assertEqual(
            self.result["candidate"]["positive_evidence_grounded_count"], 8
        )

    def test_negative_decision_stops_this_line_and_runtime_advancement(self):
        self.assertEqual(self.lock["result"], "FAIL")
        self.assertEqual(
            self.analysis["decision"],
            "freeze_negative_result_and_stop_single_call_qwen25_7b_frame_simplification",
        )
        for value in self.lock["evidence_limits"].values():
            self.assertFalse(value)
        for key, value in self.analysis.items():
            if key.endswith("_authorized"):
                self.assertFalse(value, key)


if __name__ == "__main__":
    unittest.main()
