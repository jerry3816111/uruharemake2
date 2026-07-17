#!/usr/bin/env python3
"""Validate the frozen candidate and its current runtime withdrawal."""

from __future__ import annotations

import hashlib
import inspect
import json
import subprocess
import unittest
from pathlib import Path

import uruha_brain_mac as brain


ROOT = Path(__file__).resolve().parent
HARNESS_LOCK_PATH = (
    ROOT
    / "configs"
    / "consolidation_support_runtime_v1_harness_lock.json"
)
FORMAL_RUNNER_COMMIT = "7ff8d47cae24fc664765a17f5172d10c07789321"
RUNTIME_REVERT_COMMIT = "d32aa6686203643fcbb0f7c346c593a66802d167"
REVERTED_RUNTIME_SHA256 = (
    "53cbdee26d3be3e42399c8e512ceb17884ead0bb2143d0fbda115a25fa90593a"
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


class ConsolidationSupportRuntimeV1RuntimeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.harness_lock = _load(HARNESS_LOCK_PATH)

    def test_formal_candidate_runtime_and_test_remain_hash_bound(self):
        artifacts = self.harness_lock["frozen_artifacts"]
        for name in ("brain_runtime", "runtime_helper", "runtime_test"):
            artifact = artifacts[name]
            self.assertEqual(
                _git_file_sha256(
                    FORMAL_RUNNER_COMMIT,
                    artifact["path"],
                ),
                artifact["sha256"],
                name,
            )

    def test_current_runtime_is_exactly_the_pre_candidate_version(self):
        self.assertEqual(
            _sha256(ROOT / "uruha_brain_mac.py"),
            REVERTED_RUNTIME_SHA256,
        )
        self.assertEqual(
            _git_file_sha256(
                RUNTIME_REVERT_COMMIT,
                "uruha_brain_mac.py",
            ),
            REVERTED_RUNTIME_SHA256,
        )
        source = (ROOT / "uruha_brain_mac.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn(
            "consolidation_support_runtime as csr",
            source,
        )
        self.assertNotIn(
            "_consolidate_with_support_attribution",
            source,
        )

    def test_current_consolidation_signature_has_no_candidate_hook(self):
        parameters = inspect.signature(
            brain.MemoryManager.consolidate_recent_experiences
        ).parameters
        self.assertNotIn("support_attributor", parameters)


if __name__ == "__main__":
    unittest.main()
