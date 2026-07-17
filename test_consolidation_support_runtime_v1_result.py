#!/usr/bin/env python3
"""Validate the frozen negative support-attribution runtime result."""

from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCK_PATH = (
    ROOT
    / "configs"
    / "consolidation_support_runtime_v1_result_lock.json"
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


class ConsolidationSupportRuntimeV1ResultTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = _load(LOCK_PATH)
        cls.analysis = _load(
            ROOT / cls.lock["frozen_artifacts"]["analysis_json"]["path"]
        )
        cls.raw = _load(
            ROOT / cls.lock["frozen_artifacts"]["raw_result"]["path"]
        )

    def test_negative_decision_and_only_failed_gate_are_frozen(self):
        self.assertEqual(
            self.lock["decision"],
            "drop_support_attributed_runtime_candidate",
        )
        self.assertFalse(self.lock["runtime_change_authorized"])
        self.assertTrue(self.analysis["artifact_integrity_valid"])
        self.assertFalse(self.analysis["all_success_gates_pass"])
        self.assertEqual(
            self.analysis["failed_success_gates"],
            [
                "candidate_stored_records_with_exact_"
                "support_metadata_exact"
            ],
        )
        failed = self.analysis["gates"][
            "candidate_stored_records_with_exact_support_metadata_exact"
        ]
        self.assertEqual(failed["required"], 13)
        self.assertEqual(failed["observed"], 12)

    def test_support_and_runtime_metrics_match_frozen_artifacts(self):
        support = self.analysis["support_scoring"]
        runtime = self.analysis["runtime_scoring"]
        self.assertEqual(
            support["control"]["exact_set_match_count"],
            0,
        )
        self.assertEqual(
            support["candidate"]["exact_set_match_count"],
            17,
        )
        self.assertEqual(
            support["candidate"]["evidence_precision"],
            0.9524,
        )
        self.assertEqual(
            support["candidate"]["evidence_recall"],
            1.0,
        )
        self.assertEqual(
            support["candidate"]["unsupported_empty_count"],
            3,
        )
        self.assertEqual(
            support["candidate"]["false_source_count"],
            1,
        )
        self.assertEqual(
            runtime["control"]["unsupported_derived_records_written"],
            3,
        )
        self.assertEqual(
            runtime["candidate"]["unsupported_derived_records_written"],
            0,
        )
        self.assertEqual(
            runtime["candidate"]["stored_record_count"],
            13,
        )
        self.assertEqual(
            runtime["candidate"][
                "stored_records_with_exact_support_metadata"
            ],
            12,
        )
        self.assertEqual(
            runtime["candidate"]["partial_batch_count"],
            0,
        )

    def test_single_mismatch_is_preserved_without_relabeling(self):
        mismatches = [
            row
            for row in self.analysis["support_scoring"]["candidate"][
                "scored_cases"
            ]
            if not row["exact_set_match"]
        ]
        self.assertEqual(len(mismatches), 1)
        mismatch = mismatches[0]
        self.assertEqual(
            mismatch["id"],
            "csr1_cmn_language_exchange::wisdom",
        )
        self.assertEqual(mismatch["expected_indices"], [2])
        self.assertEqual(mismatch["predicted_indices"], [2, 5])
        localization = self.lock["failure_localization"]
        self.assertTrue(localization["possible_gold_ambiguity"])
        self.assertFalse(
            localization["posthoc_relabeling_authorized"]
        )
        self.assertFalse(localization["formal_rerun_authorized"])

    def test_formal_run_was_single_local_and_gold_blind(self):
        formal = self.lock["formal_run"]
        self.assertEqual(self.raw["runner_commit"], formal["runner_commit"])
        self.assertEqual(self.raw["candidate_model_call_count"], 18)
        self.assertEqual(
            self.raw["candidate_transport_attempt_count"],
            18,
        )
        self.assertTrue(self.raw["preflight"]["passed"])
        self.assertEqual(self.raw["production_database_writes"], 0)
        self.assertFalse(
            self.raw[
                "gold_or_expected_outcome_passed_to_runtime"
            ]
        )
        self.assertIsNone(self.raw["inflight_request_at_completion"])
        self.assertEqual(
            self.raw["model_snapshot"]["digest"],
            formal["model_digest"],
        )

    def test_result_artifacts_and_historical_harness_are_hash_bound(self):
        for name, artifact in self.lock["frozen_artifacts"].items():
            self.assertEqual(
                _sha256(ROOT / artifact["path"]),
                artifact["sha256"],
                name,
            )
        historical = self.lock["historical_harness_artifacts"]
        for name, artifact in historical.items():
            self.assertEqual(
                _git_file_sha256(
                    self.lock["formal_run"]["runner_commit"],
                    artifact["path"],
                ),
                artifact["sha256"],
                name,
            )

    def test_candidate_was_removed_from_current_runtime(self):
        revert = self.lock["runtime_revert"]
        self.assertEqual(
            _sha256(ROOT / revert["path"]),
            revert["sha256"],
        )
        self.assertEqual(
            _git_file_sha256(revert["commit"], revert["path"]),
            revert["sha256"],
        )
        self.assertEqual(
            _git_file_sha256(
                self.lock["candidate_runtime"]["commit"],
                self.lock["candidate_runtime"]["path"],
            ),
            self.lock["candidate_runtime"]["sha256"],
        )
        source = (ROOT / revert["path"]).read_text(encoding="utf-8")
        self.assertNotIn("support_attributor", source)
        self.assertNotIn(
            "_consolidate_with_support_attribution",
            source,
        )

    def test_claims_and_next_step_remain_bounded(self):
        limits = self.lock["evidence_limits"]
        self.assertTrue(limits["formal_runtime_pilot_observed"])
        self.assertTrue(limits["atomicity_preflight_validated"])
        for key in (
            "runtime_integration_authorized",
            "production_activation_authorized",
            "production_data_migration_authorized",
            "retrieval_improvement_validated",
            "dialogue_improvement_validated",
            "human_likeness_validated",
            "biological_equivalence_validated",
        ):
            self.assertFalse(limits[key], key)
        self.assertIn(
            "fresh",
            self.lock["next_primary_task"].lower(),
        )
        self.assertIn(
            "do not reuse",
            self.lock["next_primary_task"].lower(),
        )


if __name__ == "__main__":
    unittest.main()
