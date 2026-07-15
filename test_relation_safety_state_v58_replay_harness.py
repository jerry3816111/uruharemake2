#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path

from run_relation_safety_state_v58_development import CONDITIONS


ROOT = Path(__file__).resolve().parent
LOCK_PATH = ROOT / "configs" / "relation_safety_state_v58_replay_harness_lock.json"
CONFIG_PATH = ROOT / "configs" / "relation_safety_state_v58_preregistration.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RelationSafetyStateV58ReplayHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def test_every_replay_artifact_is_hash_bound(self):
        frozen = self.lock["frozen_artifacts"]
        for key, expected in frozen.items():
            if not key.endswith("_sha256"):
                continue
            path_key = key.removesuffix("_sha256")
            self.assertIn(path_key, frozen)
            self.assertEqual(_sha256(ROOT / frozen[path_key]), expected, path_key)

    def test_condition_order_matches_preregistration(self):
        self.assertEqual(tuple(self.lock["conditions"]), CONDITIONS)
        self.assertEqual(tuple(self.config["conditions"]), CONDITIONS)

    def test_runner_has_no_model_transport(self):
        source = (ROOT / self.lock["frozen_artifacts"]["runner"]).read_text(
            encoding="utf-8"
        )
        for forbidden in ("_call_ollama", "_run_judgment", "urllib.request", "requests.post"):
            self.assertNotIn(forbidden, source)
        self.assertEqual(self.lock["model_calls_authorized"], 0)
        self.assertEqual(self.config["model_calls_authorized"], 0)

    def test_harness_reuses_frozen_model_outputs_and_compiler(self):
        source = (ROOT / self.lock["frozen_artifacts"]["runner"]).read_text(
            encoding="utf-8"
        )
        self.assertIn("fresh_v51_result", source)
        self.assertIn("v56_hybrid_commitment", source)
        self.assertIn("compile_relation_authorized_v57", source)
        self.assertIn("resolve_v58", source)

    def test_no_advancement_or_post_result_metric_change_is_authorized(self):
        for key in (
            "post_replay_metric_changes_authorized",
            "runtime_change_authorized",
            "shadow_integration_authorized",
            "physical_vrm_execution_enabled",
            "broad_human_likeness_claim_authorized",
        ):
            self.assertFalse(self.lock[key], key)


if __name__ == "__main__":
    unittest.main()
