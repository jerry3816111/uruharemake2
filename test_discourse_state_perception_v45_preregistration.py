#!/usr/bin/env python3

import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "discourse_state_perception_v45_preregistration.json"


class DiscourseStatePerceptionV45PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def test_frozen_input_hashes_match(self):
        frozen = self.config["frozen_inputs"]
        for key, expected in frozen.items():
            if key.endswith("_sha256"):
                path = ROOT / frozen[key.removesuffix("_sha256")]
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)

    def test_signal_patterns_compile_and_are_general(self):
        patterns = self.config["deterministic_discourse_signals"]["patterns"]
        self.assertEqual(set(patterns), set(self.config["deterministic_discourse_signals"]["signal_types"]))
        for pattern in patterns.values():
            re.compile(pattern)
        encoded = json.dumps(patterns, ensure_ascii=False)
        for action_example in ("手を振", "うなず", "笑顔", "視線"):
            self.assertNotIn(action_example, encoded)

    def test_only_signal_candidate_can_advance(self):
        self.assertIn("Only taxonomy_plus_discourse_signals_candidate", self.config["development_decision_rule"])
        self.assertTrue(self.config["fresh_holdout"]["freeze_and_commit_before_model_inference"])

    def test_no_integration_or_execution_is_authorized(self):
        self.assertFalse(self.config["runtime_change_authorized"])
        self.assertFalse(self.config["shadow_integration_authorized"])
        self.assertFalse(self.config["physical_vrm_execution_enabled"])


if __name__ == "__main__":
    unittest.main()
