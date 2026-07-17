#!/usr/bin/env python3
"""Verify the frozen negative consolidation-admission V1 result."""

from __future__ import annotations

import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path

import analyze_consolidation_admission_v1_development as analyzer


ROOT = Path(__file__).resolve().parent
LOCK_PATH = ROOT / "configs" / "consolidation_admission_v1_result_lock.json"
RAW_PATH = ROOT / "reports" / "consolidation_admission_v1_development_raw.json"
ANALYSIS_PATH = (
    ROOT / "reports" / "consolidation_admission_v1_development_analysis.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ConsolidationAdmissionResultTest(unittest.TestCase):
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

    def test_failure_is_specificity_without_recall(self):
        self.assertFalse(self.result["all_gates_pass"])
        self.assertEqual(self.result["control"]["correct_count"], 0)
        self.assertEqual(self.result["candidate"]["correct_count"], 6)
        self.assertEqual(
            self.result["control"]["observed_target_counts"],
            {"multiple": 16, "procedural": 2},
        )
        self.assertEqual(
            self.result["candidate"]["observed_target_counts"],
            {"none": 18},
        )
        self.assertEqual(
            self.result["class_metrics"]["wisdom"]["candidate_correct"], 0
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
            self.result["candidate_missed_long_term_write_count"], 12
        )

    def test_observed_contract_failures_are_preserved(self):
        errors = Counter(
            row["parse_error"] or "none"
            for row in self.raw["candidate_rows"]
        )
        self.assertEqual(errors, Counter({"none": 11, "confidence_range": 7}))
        evidence_failures_after_parse = sum(
            row["parse_success"] and not row["evidence_contract_success"]
            for row in self.raw["candidate_rows"]
        )
        self.assertEqual(evidence_failures_after_parse, 5)
        self.assertEqual(
            self.result["candidate"]["parse_success_count"], 11
        )
        self.assertEqual(
            self.result["candidate"]["evidence_contract_success_count"], 6
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
