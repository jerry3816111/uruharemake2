#!/usr/bin/env python3
"""Verify the frozen negative indexed consolidation V2 result."""

from __future__ import annotations

import hashlib
import json
import unittest
from collections import Counter
from datetime import datetime
from pathlib import Path

import analyze_consolidation_admission_v2_indexed_development as analyzer


ROOT = Path(__file__).resolve().parent
LOCK_PATH = (
    ROOT / "configs" / "consolidation_admission_v2_indexed_result_lock.json"
)
RAW_PATH = (
    ROOT
    / "reports"
    / "consolidation_admission_v2_indexed_development_raw.json"
)
ANALYSIS_PATH = (
    ROOT
    / "reports"
    / "consolidation_admission_v2_indexed_development_analysis.json"
)
METADATA_CORRECTION_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_v2_indexed_metadata_correction.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ConsolidationAdmissionV2ResultTest(unittest.TestCase):
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
            "metadata_correction",
            "preregistration",
            "protocol_correction",
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

    def test_failure_is_small_gain_without_positive_recall(self):
        self.assertFalse(self.result["all_gates_pass"])
        self.assertEqual(self.result["control"]["correct_count"], 6)
        self.assertEqual(self.result["candidate"]["correct_count"], 8)
        self.assertEqual(self.result["net_correct_gain_vs_control"], 2)
        self.assertEqual(self.result["newly_correct_count"], 2)
        self.assertEqual(self.result["regression_count"], 0)
        self.assertEqual(
            self.result["class_metrics"]["wisdom"]["candidate_correct"], 2
        )
        self.assertEqual(
            self.result["class_metrics"]["procedural"]["candidate_correct"], 0
        )
        self.assertEqual(
            self.result["class_metrics"]["none"]["candidate_correct"], 6
        )
        self.assertEqual(
            self.result["candidate_false_long_term_write_count"], 0
        )
        self.assertEqual(
            self.result["candidate_missed_long_term_write_count"], 10
        )

    def test_owner_ambiguity_and_transport_failures_are_preserved(self):
        rows = self.raw["candidate_rows"]
        errors = Counter(row["parse_error"] or "none" for row in rows)
        self.assertEqual(
            errors,
            Counter(
                {
                    "none": 13,
                    "index_contract": 2,
                    "tool_call_count": 2,
                    "argument_keys": 1,
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
            Counter(row["owner"] for row in procedural_raw),
            Counter({"user": 6}),
        )
        self.assertEqual(self.result["candidate"]["frame_exact_count"], 1)
        self.assertEqual(
            self.result["candidate"]["positive_evidence_grounded_count"], 8
        )

    def test_metadata_timestamp_error_is_transparently_corrected(self):
        correction = _load(METADATA_CORRECTION_PATH)
        chronology = correction["authoritative_chronology"]
        commit_at = datetime.fromisoformat(
            chronology["protocol_and_harness_commit"]["committed_at"]
        )
        merge_at = datetime.fromisoformat(
            chronology["harness_merge"]["merged_at"]
        )
        run_start = datetime.fromisoformat(
            chronology["model_collection"]["started_at"]
        )
        run_end = datetime.fromisoformat(
            chronology["model_collection"]["completed_at"]
        )
        self.assertLess(commit_at, merge_at)
        self.assertLess(merge_at, run_start)
        self.assertLess(run_start, run_end)
        self.assertEqual(
            chronology["harness_merge"]["commit"],
            self.lock["harness_merge_commit"],
        )
        self.assertEqual(
            chronology["model_collection"]["started_at"],
            self.raw["started_at"],
        )
        self.assertFalse(
            correction["protocol_or_gate_changed_after_result"]
        )

    def test_negative_decision_forbids_retest_or_runtime_advancement(self):
        self.assertEqual(self.lock["result"], "FAIL")
        self.assertEqual(
            self.analysis["decision"],
            "freeze_negative_result_and_leave_enabled_consolidation_unchanged",
        )
        for value in self.lock["evidence_limits"].values():
            self.assertFalse(value)
        for key, value in self.analysis.items():
            if key.endswith("_authorized"):
                self.assertFalse(value, key)


if __name__ == "__main__":
    unittest.main()
