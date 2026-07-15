#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "precise_target_mentions_v52_preregistration.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PreciseTargetMentionsV52PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def test_every_historical_input_is_hash_bound(self):
        for key, expected in self.config["frozen_inputs"].items():
            if key.endswith("_sha256"):
                path = ROOT / self.config["frozen_inputs"][
                    key.removesuffix("_sha256")
                ]
                self.assertEqual(_sha256(path), expected)

    def test_one_representation_change_is_fixed(self):
        self.assertEqual(
            self.config["conditions"],
            ["v51_event_map_control", "precise_target_mentions_candidate"],
        )
        change = self.config["causal_change"]
        self.assertFalse(change["direct_deterministic_commitment_override"])
        self.assertFalse(change["direct_deterministic_execution_override"])
        self.assertIn("target_mentions", change["candidate"])
        self.assertIn("predicate_evidence", change["candidate"])

    def test_all_current_targets_have_locked_mention_patterns(self):
        patterns = self.config["causal_change"]["target_mention_patterns"]
        self.assertEqual(len(patterns), 14)
        self.assertEqual(patterns["gaze.left"], "左")
        self.assertEqual(patterns["gaze.right"], "右")

    def test_advancement_requires_47_calls_zero_false_and_zero_regression(self):
        absolute = self.config["candidate_absolute_gates"]
        matched = self.config["matched_comparison_gates"]
        self.assertEqual(absolute["compiled_call_exact_count_at_least"], 47)
        self.assertEqual(absolute["false_action_count"], 0)
        self.assertEqual(matched["semantic_regression_count"], 0)
        self.assertEqual(matched["call_regression_count"], 0)

    def test_consumed_data_cannot_authorize_runtime(self):
        self.assertFalse(self.config["prompt_or_map_tuning_after_run_authorized"])
        self.assertFalse(self.config["fresh_holdout_claim_authorized"])
        self.assertFalse(self.config["runtime_change_authorized"])
        self.assertFalse(self.config["shadow_integration_authorized"])
        self.assertFalse(self.config["physical_vrm_execution_enabled"])
        self.assertFalse(self.config["human_likeness_claim_authorized"])


if __name__ == "__main__":
    unittest.main()
