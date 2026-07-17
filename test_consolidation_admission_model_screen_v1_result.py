#!/usr/bin/env python3
"""Verify the frozen consolidation-admission model screen V1 result."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

import analyze_consolidation_admission_model_screen_v1_development as analyzer


ROOT = Path(__file__).resolve().parent
LOCK_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_model_screen_v1_result_lock.json"
)
RAW_PATH = (
    ROOT
    / "reports"
    / "consolidation_admission_model_screen_v1_development_raw.json"
)
ANALYSIS_PATH = (
    ROOT
    / "reports"
    / "consolidation_admission_model_screen_v1_development_analysis.json"
)
DATASET_PATH = (
    ROOT
    / "datasets"
    / "consolidation_admission_model_screen_v1_development.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ConsolidationAdmissionModelScreenV1ResultTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = _load(LOCK_PATH)
        cls.raw = _load(RAW_PATH)
        cls.analysis = _load(ANALYSIS_PATH)
        cls.result = cls.analysis["model_screen_result"]
        cls.dataset = _load(DATASET_PATH)

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
            recomputed["model_screen_result"],
            self.analysis["model_screen_result"],
        )
        self.assertEqual(recomputed["decision"], self.analysis["decision"])
        for key in (
            "selected_model_condition",
            "same_dataset_retest_authorized",
            "fresh_integration_pilot_authorized",
            "two_stage_architecture_development_authorized",
            "single_call_model_replacement_continuation_authorized",
            "runtime_memory_write_authorized",
            "runtime_shadow_authorized",
            "fresh_holdout_authorized",
            "broad_human_likeness_claim_authorized",
            "general_model_superiority_claim_authorized",
        ):
            self.assertEqual(recomputed[key], self.analysis[key])

    def test_collection_provenance_is_complete_and_runtime_safe(self):
        self.assertEqual(self.raw["runner_branch"], "main")
        self.assertEqual(
            self.raw["runner_commit"], self.lock["harness_merge_commit"]
        )
        self.assertEqual(self.raw["model_calls"], 36)
        self.assertEqual(self.raw["transport_attempts_made"], 36)
        self.assertIsNone(self.raw["inflight"])
        self.assertEqual(
            {
                condition: len(rows)
                for condition, rows in self.raw[
                    "rows_by_condition"
                ].items()
            },
            {
                "qwen25_7b_control": 12,
                "qwen35_4b_candidate": 12,
                "qwen35_9b_candidate": 12,
            },
        )
        self.assertFalse(self.raw["gold_fields_passed_to_model"])
        self.assertFalse(self.raw["runtime_memory_write_performed"])
        self.assertEqual(
            [
                row["transport_error"]
                for rows in self.raw["rows_by_condition"].values()
                for row in rows
                if row.get("transport_error")
            ],
            [],
        )

    def test_qwen35_4b_improves_transport_but_not_semantic_balance(self):
        control = self.result["control"]
        candidate = self.result["candidates"]["qwen35_4b_candidate"]
        summary = candidate["summary"]
        self.assertEqual(control["correct_count"], 6)
        self.assertEqual(summary["correct_count"], 8)
        self.assertEqual(summary["parse_success_count"], 12)
        self.assertEqual(summary["index_contract_success_count"], 12)
        self.assertEqual(
            summary["class_metrics"]["procedural"]["correct_count"], 4
        )
        self.assertEqual(
            summary["class_metrics"]["wisdom"]["correct_count"], 1
        )
        self.assertEqual(summary["missed_long_term_write_count"], 0)
        self.assertEqual(candidate["paired_vs_control"]["regression_count"], 2)
        self.assertFalse(candidate["eligible"])
        self.assertFalse(
            candidate["gate_checks"]["candidate_correct_count_min"]
        )
        self.assertFalse(
            candidate["gate_checks"]["candidate_wisdom_correct_min"]
        )

    def test_qwen35_9b_passes_semantics_but_fails_frozen_median_latency(self):
        candidate = self.result["candidates"]["qwen35_9b_candidate"]
        summary = candidate["summary"]
        self.assertEqual(summary["correct_count"], 10)
        self.assertEqual(summary["semantic_frame_exact_count"], 10)
        self.assertEqual(summary["evidence_grounded_count"], 11)
        self.assertEqual(
            summary["positive_evidence_grounded_count"], 8
        )
        self.assertEqual(summary["parse_success_count"], 12)
        self.assertEqual(summary["index_contract_success_count"], 12)
        self.assertEqual(
            candidate["paired_vs_control"]["net_correct_gain_vs_control"], 4
        )
        self.assertEqual(candidate["paired_vs_control"]["regression_count"], 1)
        failed = [
            name
            for name, passed in candidate["gate_checks"].items()
            if not passed
        ]
        self.assertEqual(failed, ["candidate_median_wall_seconds_max"])
        self.assertGreater(summary["median_wall_seconds"], 5.0)
        self.assertLessEqual(summary["warm_p95_wall_seconds"], 7.0)
        self.assertFalse(candidate["eligible"])

    def test_exploratory_cascade_replay_is_11_of_12_not_a_pass(self):
        rows4 = {
            row["id"]: row
            for row in self.raw["rows_by_condition"][
                "qwen35_4b_candidate"
            ]
        }
        rows9 = {
            row["id"]: row
            for row in self.raw["rows_by_condition"][
                "qwen35_9b_candidate"
            ]
        }
        replay = []
        for case in self.dataset["cases"]:
            stage_one_write = (
                rows4[case["id"]]["observed_target"] != "none"
            )
            final = (
                rows9[case["id"]]["observed_target"]
                if stage_one_write
                else "none"
            )
            replay.append(
                {
                    "expected": case["expected_memory_kind"],
                    "final": final,
                    "stage_one_write": stage_one_write,
                }
            )
        self.assertEqual(
            12 + sum(row["stage_one_write"] for row in replay), 21
        )
        self.assertEqual(
            sum(row["expected"] == row["final"] for row in replay), 11
        )
        self.assertEqual(
            sum(
                row["expected"] == "none" and row["final"] != "none"
                for row in replay
            ),
            0,
        )
        self.assertEqual(
            sum(
                row["expected"] != "none" and row["final"] == "none"
                for row in replay
            ),
            1,
        )
        self.assertFalse(
            self.analysis["fresh_integration_pilot_authorized"]
        )

    def test_negative_decision_stops_direct_replacement_only(self):
        self.assertEqual(self.lock["result"], "FAIL")
        self.assertEqual(
            self.analysis["decision"],
            "reject_model_replacement_and_proceed_to_two_stage_architecture",
        )
        self.assertIsNone(self.analysis["selected_model_condition"])
        self.assertTrue(
            self.analysis["two_stage_architecture_development_authorized"]
        )
        self.assertFalse(
            self.analysis[
                "single_call_model_replacement_continuation_authorized"
            ]
        )
        for value in self.lock["evidence_limits"].values():
            self.assertFalse(value)


if __name__ == "__main__":
    unittest.main()
