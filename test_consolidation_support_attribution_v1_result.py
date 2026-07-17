#!/usr/bin/env python3
"""Validate the frozen support-attribution V1 development result."""

from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from pathlib import Path

from analyze_consolidation_support_attribution_v1_development import (
    analyze,
)


ROOT = Path(__file__).resolve().parent
LOCK_PATH = (
    ROOT
    / "configs"
    / "consolidation_support_attribution_v1_result_lock.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ConsolidationSupportAttributionV1ResultTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = _load(LOCK_PATH)
        cls.analysis = analyze()

    def test_positive_decision_is_supported_by_every_frozen_gate(self):
        self.assertEqual(
            self.lock["decision"],
            (
                "keep_support_attribution_candidate_for_fresh_"
                "runtime_integration_pilot"
            ),
        )
        self.assertFalse(self.lock["runtime_integration_authorized"])
        self.assertTrue(
            self.lock["fresh_runtime_integration_pilot_authorized"]
        )
        self.assertTrue(self.analysis["artifact_integrity_valid"])
        self.assertTrue(
            self.analysis["result"]["all_success_gates_pass"]
        )
        self.assertEqual(
            [
                key
                for key, row in self.analysis["result"]["gates"].items()
                if not row["passed"]
            ],
            [],
        )

    def test_all_result_and_harness_artifacts_are_hash_bound(self):
        for artifact in self.lock["frozen_artifacts"].values():
            self.assertEqual(
                _sha256(ROOT / artifact["path"]),
                artifact["sha256"],
                artifact["path"],
            )

    def test_preregistration_merge_is_the_exact_runner_commit(self):
        preregistration = self.lock["preregistration"]
        run = self.lock["formal_run"]
        self.assertEqual(
            preregistration["merge_commit"],
            run["runner_commit"],
        )
        completed = subprocess.run(
            [
                "git",
                "merge-base",
                "--is-ancestor",
                preregistration["commit"],
                preregistration["merge_commit"],
            ],
            cwd=ROOT,
            check=False,
        )
        self.assertEqual(completed.returncode, 0)

    def test_observed_metrics_and_errors_match_frozen_result(self):
        result = self.lock["results"]
        control = self.analysis["result"]["control"]
        candidate = self.analysis["result"]["candidate"]
        self.assertEqual(control["exact_set_match_count"], 0)
        self.assertEqual(control["evidence_precision"], 0.1389)
        self.assertEqual(candidate["exact_set_match_count"], 16)
        self.assertEqual(candidate["evidence_precision"], 0.9333)
        self.assertEqual(candidate["evidence_recall"], 0.9333)
        self.assertEqual(candidate["unsupported_empty_count"], 6)
        self.assertEqual(candidate["false_source_count"], 1)
        self.assertEqual(candidate["missed_source_count"], 1)
        self.assertEqual(
            result["non_exact_case_ids"],
            [
                "csa1_jpn_sunday_meal_prep",
                "csa1_cmn_no_analysis_policy",
            ],
        )
        self.assertEqual(result["model_calls"], 18)
        self.assertEqual(result["transport_attempts"], 18)

    def test_runtime_is_unchanged_and_claims_remain_bounded(self):
        for path, expected_hash in self.lock["unchanged_runtime_files"].items():
            self.assertEqual(_sha256(ROOT / path), expected_hash, path)
        limits = self.lock["evidence_limits"]
        self.assertTrue(limits["development_mechanism_claim_authorized"])
        self.assertTrue(
            limits[
                "fresh_runtime_integration_pilot_authorized_only"
            ]
        )
        for key in (
            "runtime_integration_authorized",
            "official_benchmark_claim_authorized",
            "cross_corpus_generalization_claim_authorized",
            "long_term_recall_improvement_claim_authorized",
            "downstream_dialogue_improvement_claim_authorized",
            "human_likeness_claim_authorized",
            "biological_equivalence_claim_authorized",
            "production_data_migration_authorized",
        ):
            self.assertFalse(limits[key], key)


if __name__ == "__main__":
    unittest.main()
