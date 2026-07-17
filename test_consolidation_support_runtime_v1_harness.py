#!/usr/bin/env python3
"""Validate the frozen support-attribution runtime harness."""

from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "consolidation_support_runtime_v1_preregistration.json"
)
LOCK_PATH = (
    ROOT
    / "configs"
    / "consolidation_support_runtime_v1_harness_lock.json"
)
IMPLEMENTATION_MERGE_COMMIT = (
    "c8703743c223bca78c6a23fe585fab9821a8cc64"
)
FORMAL_RUNNER_COMMIT = "7ff8d47cae24fc664765a17f5172d10c07789321"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _git_file_content(commit, path):
    return subprocess.check_output(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
    )


def _git_file_sha256(commit, path):
    return hashlib.sha256(
        _git_file_content(commit, path)
    ).hexdigest()


def _git_file_exists(commit, path):
    completed = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}:{path}"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return completed.returncode == 0


class ConsolidationSupportRuntimeV1HarnessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = _load(CONFIG_PATH)
        cls.lock = _load(LOCK_PATH)

    def test_identity_model_and_formal_call_count_are_frozen(self):
        self.assertEqual(
            self.lock["experiment_id"],
            self.config["experiment_id"],
        )
        self.assertEqual(
            self.lock["implementation_merge_commit"],
            IMPLEMENTATION_MERGE_COMMIT,
        )
        self.assertEqual(
            self.lock["model"]["digest"],
            self.config["model"]["digest"],
        )
        invariants = self.config["formal_run_invariants"]
        self.assertEqual(
            self.lock["formal_run"]["model_call_count_exact"],
            invariants["candidate_model_call_count_exact"],
        )
        self.assertEqual(
            self.lock["formal_run"]["transport_attempt_count_exact"],
            18,
        )
        self.assertEqual(
            self.lock["formal_run"]["formal_run_count_exact"],
            1,
        )

    def test_every_frozen_artifact_matches_its_hash(self):
        for name, artifact in self.lock["frozen_artifacts"].items():
            self.assertEqual(
                _git_file_sha256(
                    FORMAL_RUNNER_COMMIT,
                    artifact["path"],
                ),
                artifact["sha256"],
                name,
            )

    def test_runner_rejects_drift_dirty_tree_and_result_overwrite(self):
        source = _git_file_content(
            FORMAL_RUNNER_COMMIT,
            self.lock["frozen_artifacts"]["runner"]["path"],
        ).decode("utf-8")
        self.assertIn("_verify_frozen_artifacts(lock)", source)
        self.assertIn("formal run requires the main branch", source)
        self.assertIn("formal run requires a clean worktree", source)
        self.assertIn("refusing to overwrite formal result", source)
        self.assertIn("TemporaryDirectory", source)
        self.assertIn('"production_database_writes": 0', source)
        self.assertIn(
            '"gold_or_expected_outcome_passed_to_runtime": False',
            source,
        )
        self.assertNotIn("gold_support_event_indices", source)
        self.assertNotIn("expected_candidate_outcome", source)

    def test_model_transport_is_single_attempt_and_gold_blind(self):
        source = _git_file_content(
            FORMAL_RUNNER_COMMIT,
            self.lock["frozen_artifacts"]["model_adapter"]["path"],
        ).decode("utf-8")
        self.assertIn(
            'transport_attempts"] != 1',
            source,
        )
        self.assertIn('"transport_attempts": 1', source)
        self.assertNotIn("gold_support_event_indices", source)
        self.assertNotIn("expected_candidate_outcome", source)
        self.assertNotIn("episode_id", source)

    def test_preflight_is_fixed_and_covers_atomicity_and_regressions(self):
        arguments = self.lock["preflight"]["arguments"]
        self.assertEqual(arguments[:3], ["-m", "unittest", "-q"])
        required = {
            "test_consolidation_support_runtime_v1_runtime.py",
            "test_consolidation_support_runtime_v1_model.py",
            "test_consolidation_support_runtime_v1_analyzer.py",
            "test_consolidation_source_provenance_v1_runtime.py",
            "test_memory_runtime_activation.py",
            "test_typed_reflection_runtime_v3.py",
        }
        self.assertTrue(required <= set(arguments))
        self.assertEqual(
            self.lock["preflight"]["expected_test_count"],
            166,
        )

    def test_result_artifacts_did_not_exist_at_implementation_merge(self):
        for relative_path in self.config["result_artifacts"]:
            self.assertFalse(
                _git_file_exists(
                    IMPLEMENTATION_MERGE_COMMIT,
                    relative_path,
                ),
                relative_path,
            )

    def test_authorization_and_claim_boundary_are_explicit(self):
        self.assertTrue(
            self.lock[
                "formal_model_inference_authorized_after_lock_merge"
            ]
        )
        self.assertFalse(
            self.lock["production_activation_authorized"]
        )
        limits = self.config["evidence_limits"]
        for key in (
            "production_activation_authorized",
            "retrieval_improvement_claim_authorized",
            "downstream_dialogue_improvement_claim_authorized",
            "human_likeness_claim_authorized",
            "biological_equivalence_claim_authorized",
        ):
            self.assertFalse(limits[key], key)


if __name__ == "__main__":
    unittest.main()
