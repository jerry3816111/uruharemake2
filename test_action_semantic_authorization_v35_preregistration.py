#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs" / "action_semantic_authorization_v35_preregistration.json"


class ActionSemanticAuthorizationV35PreregistrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_development_sources_are_hash_bound_and_retired(self):
        evidence = self.config["development_evidence"]
        for path_key, hash_key in (
            ("dataset", "dataset_sha256"),
            ("raw_proposals", "raw_proposals_sha256"),
        ):
            path = ROOT / evidence[path_key]
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(digest, evidence[hash_key])
        self.assertIn("development_only", evidence["status"])

    def test_small_model_capacity_ladder_is_frozen(self):
        candidates = self.config["candidate_authorizers"]
        self.assertEqual(
            [candidate["blob_bytes"] for candidate in candidates.values()],
            sorted(candidate["blob_bytes"] for candidate in candidates.values()),
        )
        self.assertEqual(len(candidates), 3)

    def test_runtime_and_executor_remain_locked(self):
        self.assertFalse(self.config["runtime_change_authorized"])
        self.assertFalse(self.config["vrm_execution_enabled"])
        self.assertFalse(
            self.config["fresh_confirmation_authorized_before_development_pass"]
        )


if __name__ == "__main__":
    unittest.main()
