#!/usr/bin/env python3
"""Validate the frozen source-provenance V1 result."""

from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from pathlib import Path

from analyze_consolidation_source_provenance_v1 import analyze


ROOT = Path(__file__).resolve().parent
LOCK_PATH = (
    ROOT
    / "configs"
    / "consolidation_source_provenance_v1_result_lock.json"
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


class ConsolidationSourceProvenanceV1ResultTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = _load(LOCK_PATH)
        cls.analysis = analyze()

    def test_decision_is_supported_by_all_frozen_data_gates(self):
        self.assertEqual(
            self.lock["decision"],
            "keep_source_preserving_consolidation_runtime",
        )
        self.assertTrue(self.lock["runtime_change_authorized"])
        historical_artifact_checks = {
            key: passed
            for key, passed in self.analysis["artifact_checks"].items()
            if key != "current_runtime_matches_treatment"
        }
        self.assertTrue(all(historical_artifact_checks.values()))
        self.assertEqual(
            [
                key
                for key, item in self.analysis["gates"].items()
                if not item["passed"]
            ],
            [],
        )
        self.assertEqual(
            [
                key
                for key, passed in historical_artifact_checks.items()
                if not passed
            ],
            [],
        )

    def test_all_result_artifacts_are_hash_bound(self):
        for artifact in self.lock["frozen_artifacts"].values():
            self.assertEqual(
                _sha256(ROOT / artifact["path"]),
                artifact["sha256"],
                artifact["path"],
            )
        preregistration = self.lock["preregistration"]
        runtime = self.lock["treatment_runtime"]
        self.assertEqual(
            _sha256(ROOT / preregistration["path"]),
            preregistration["sha256"],
        )
        self.assertEqual(
            _git_file_sha256(runtime["commit"], runtime["path"]),
            runtime["sha256"],
        )

    def test_preregistration_precedes_treatment_runtime(self):
        preregistration = self.lock["preregistration"]
        runtime = self.lock["treatment_runtime"]
        completed = subprocess.run(
            [
                "git",
                "merge-base",
                "--is-ancestor",
                preregistration["merge_commit"],
                runtime["commit"],
            ],
            cwd=ROOT,
            check=False,
        )
        self.assertEqual(completed.returncode, 0)
        self.assertIn("created_at", self.lock["protocol_note"])
        self.assertIn("not used", self.lock["protocol_note"])

    def test_result_matches_the_frozen_reports(self):
        result = self.lock["results"]
        baseline = self.analysis["baseline"]
        treatment = self.analysis["treatment"]
        self.assertEqual(result["source_episode_retention"]["baseline"], "0/20")
        self.assertEqual(
            result["source_episode_retention"]["treatment"],
            "20/20",
        )
        self.assertEqual(baseline["deleted_episode_count"], 20)
        self.assertEqual(treatment["deleted_episode_count"], 0)
        self.assertEqual(
            treatment["derived_records_with_exact_source_ids"],
            3,
        )
        self.assertTrue(
            treatment[
                "second_pass_created_no_duplicate_derived_records"
            ]
        )

    def test_claims_remain_bounded(self):
        limits = self.lock["evidence_limits"]
        self.assertTrue(limits["source_retention_and_traceability_validated"])
        self.assertTrue(limits["idempotence_validated"])
        self.assertTrue(limits["summary_write_failure_retry_validated"])
        for key in (
            "semantic_consolidation_quality_validated",
            "retrieval_improvement_validated",
            "dialogue_improvement_validated",
            "human_likeness_validated",
            "biological_equivalence_validated",
            "permanent_retention_policy_validated",
            "production_data_migration_validated",
        ):
            self.assertFalse(limits[key], key)


if __name__ == "__main__":
    unittest.main()
