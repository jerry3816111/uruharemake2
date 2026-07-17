#!/usr/bin/env python3
"""Validate the frozen negative source-pointer V1 result."""

from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from pathlib import Path

from analyze_consolidation_source_pointer_v1 import analyze


ROOT = Path(__file__).resolve().parent
LOCK_PATH = (
    ROOT
    / "configs"
    / "consolidation_source_pointer_v1_result_lock.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_file_sha256(commit, path):
    content = subprocess.check_output(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
    )
    return hashlib.sha256(content).hexdigest()


class ConsolidationSourcePointerV1ResultTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = _load(LOCK_PATH)
        cls.analysis = analyze()

    def test_negative_decision_is_supported_by_frozen_gates(self):
        self.assertEqual(
            self.lock["decision"],
            "drop_source_pointer_v1_candidate",
        )
        self.assertFalse(self.lock["runtime_change_authorized"])
        self.assertEqual(self.analysis["decision"], "DROP")
        self.assertTrue(self.analysis["artifact_integrity_valid"])
        self.assertFalse(self.analysis["candidate_gates_passed"])
        self.assertEqual(
            {
                key
                for key, item in self.analysis["gates"].items()
                if not item["passed"]
            },
            {
                "treatment_positive_target_source_hits_min",
                "paired_positive_net_gain_min",
                "treatment_positive_exact_user_text_hits_min",
                "treatment_positive_summary_exact_user_text_hits_min",
                "treatment_wrong_source_injections_exact",
            },
        )

    def test_result_artifacts_and_candidate_runtime_are_hash_bound(self):
        for artifact in self.lock["frozen_artifacts"].values():
            self.assertEqual(
                _sha256(ROOT / artifact["path"]),
                artifact["sha256"],
                artifact["path"],
            )
        candidate = self.lock["candidate_runtime"]
        for path, expected_hash in candidate[
            "file_sha256"
        ].items():
            self.assertEqual(
                _git_file_sha256(candidate["commit"], path),
                expected_hash,
                path,
            )

    def test_preregistration_precedes_candidate_and_revert(self):
        preregistration = self.lock["preregistration"]
        candidate = self.lock["candidate_runtime"]
        revert = self.lock["runtime_revert"]
        for ancestor, descendant in (
            (preregistration["merge_commit"], candidate["commit"]),
            (candidate["commit"], revert["commit"]),
        ):
            completed = subprocess.run(
                [
                    "git",
                    "merge-base",
                    "--is-ancestor",
                    ancestor,
                    descendant,
                ],
                cwd=ROOT,
                check=False,
            )
            self.assertEqual(completed.returncode, 0)

    def test_observed_result_matches_reports(self):
        result = self.lock["results"]
        baseline = self.analysis["baseline"]["summary"]
        treatment = self.analysis["treatment"]["summary"]
        self.assertEqual(baseline["positive_target_source_hits"], 0)
        self.assertEqual(treatment["positive_target_source_hits"], 4)
        self.assertEqual(treatment["wrong_source_injections"], 2)
        self.assertEqual(
            result["correct_source_recall"],
            {
                "baseline": "0/6",
                "candidate": "4/6",
                "required": "at_least_5/6",
            },
        )
        self.assertEqual(
            result["failed_positive_case_ids"],
            ["positive_en_time", "positive_zh_change"],
        )

    def test_runtime_is_reverted_and_claims_remain_bounded(self):
        self.assertTrue(
            self.analysis["artifact_checks"][
                "current_runtime_reverted"
            ]
        )
        for path, expected_hash in self.lock["runtime_revert"][
            "current_file_sha256"
        ].items():
            self.assertEqual(_sha256(ROOT / path), expected_hash)
        limits = self.lock["evidence_limits"]
        self.assertTrue(limits["pointer_integrity_fail_closed_validated"])
        self.assertTrue(
            limits["partial_exact_source_recall_observed"]
        )
        for key in (
            "source_pointer_runtime_authorized",
            "reliable_source_selection_validated",
            "semantic_answer_accuracy_validated",
            "dialogue_improvement_validated",
            "human_likeness_validated",
            "biological_equivalence_validated",
            "production_data_migration_validated",
        ):
            self.assertFalse(limits[key], key)


if __name__ == "__main__":
    unittest.main()
