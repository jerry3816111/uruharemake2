#!/usr/bin/env python3
"""Validate the frozen negative result for admission cascade V1."""

from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from pathlib import Path

import analyze_consolidation_admission_cascade_v1_development as analyzer


ROOT = Path(__file__).resolve().parent
RESULT_LOCK_PATH = (
    ROOT
    / "configs"
    / "consolidation_admission_cascade_v1_result_lock.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ConsolidationAdmissionCascadeV1ResultTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = _load(RESULT_LOCK_PATH)
        frozen = cls.lock["frozen_artifacts"]
        cls.raw = _load(ROOT / frozen["raw_result"])
        cls.analysis = _load(ROOT / frozen["analysis_json"])

    def test_result_lock_hashes_every_result_artifact(self):
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
            path = ROOT / self.lock["frozen_artifacts"][name]
            self.assertEqual(
                _sha256(path),
                self.lock["frozen_artifacts"][f"{name}_sha256"],
            )

    def test_collection_was_complete_exact_and_transport_clean(self):
        self.assertEqual(self.raw["runner_branch"], "main")
        self.assertEqual(
            self.raw["runner_commit"], self.lock["harness_merge_commit"]
        )
        self.assertEqual(self.raw["model_calls"], 30)
        self.assertEqual(self.raw["transport_attempts_made"], 30)
        self.assertEqual(len(self.raw["control_rows"]), 12)
        self.assertEqual(len(self.raw["stage1_rows"]), 12)
        self.assertEqual(len(self.raw["stage2_rows"]), 6)
        self.assertIsNone(self.raw["inflight"])
        rows = (
            self.raw["control_rows"]
            + self.raw["stage1_rows"]
            + self.raw["stage2_rows"]
        )
        self.assertFalse(
            any(row.get("transport_error") is not None for row in rows)
        )
        self.assertFalse(self.raw["gold_fields_passed_to_model"])
        self.assertFalse(self.raw["runtime_memory_write_performed"])

    def test_independent_analyzer_reproduces_the_frozen_decision(self):
        recomputed = analyzer.analyze(
            ROOT / self.lock["frozen_artifacts"]["raw_result"]
        )
        self.assertEqual(
            recomputed["cascade_result"],
            self.analysis["cascade_result"],
        )
        self.assertEqual(recomputed["decision"], self.analysis["decision"])

    def test_candidate_regressed_against_the_matched_control(self):
        result = self.analysis["cascade_result"]
        self.assertFalse(result["all_gates_pass"])
        self.assertEqual(result["control"]["correct_count"], 10)
        self.assertEqual(result["candidate"]["correct_count"], 9)
        self.assertEqual(result["stage1"]["positive_write_count"], 6)
        self.assertEqual(result["stage1"]["false_write_count"], 0)
        self.assertEqual(result["stage2"]["call_count"], 6)
        self.assertEqual(
            result["candidate"]["false_long_term_write_count"], 0
        )
        self.assertEqual(
            result["candidate"]["missed_long_term_write_count"], 3
        )
        self.assertEqual(
            result["paired_vs_control"]["newly_correct_count"], 0
        )
        self.assertEqual(
            result["paired_vs_control"]["regression_count"], 1
        )
        self.assertEqual(
            result["paired_vs_control"]["net_correct_gain_vs_control"], -1
        )
        self.assertTrue(all(result["run_checks"].values()))

    def test_failure_stops_this_cascade_and_runtime_integration(self):
        self.assertEqual(self.lock["result"], "FAIL")
        self.assertEqual(
            self.lock["decision"],
            "fail_stop_qwen35_4b_to_9b_cascade",
        )
        limits = self.lock["next_step_authorization"]
        self.assertTrue(limits["stop_current_cascade"])
        for key, value in limits.items():
            if key != "stop_current_cascade":
                self.assertFalse(value, key)
        for value in self.analysis.items():
            key, flag = value
            if key.endswith("_authorized"):
                self.assertFalse(flag, key)

    def test_result_files_did_not_exist_in_harness_merge_commit(self):
        harness_commit = self.lock["harness_merge_commit"]
        for name in (
            "raw_result",
            "analysis_json",
            "analysis_markdown",
            "diagnostic_zh",
            "result_test",
        ):
            path = self.lock["frozen_artifacts"][name]
            completed = subprocess.run(
                ["git", "cat-file", "-e", f"{harness_commit}:{path}"],
                cwd=ROOT,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(completed.returncode, 0)


if __name__ == "__main__":
    unittest.main()
