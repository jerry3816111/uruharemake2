#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "precise_target_mentions_v52_holdout_preregistration.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PreciseTargetMentionsV52HoldoutPreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def test_every_local_frozen_input_is_hash_bound(self):
        frozen = self.config["frozen_inputs"]
        for key, expected in frozen.items():
            if not key.endswith("_sha256"):
                continue
            path = ROOT / frozen[key.removesuffix("_sha256")]
            self.assertEqual(_sha256(path), expected, path)

    def test_dataset_and_judgment_counts_are_locked(self):
        frozen = self.config["frozen_inputs"]
        self.assertEqual(frozen["case_count"], 64)
        self.assertEqual(frozen["external_exact_case_count"], 24)
        self.assertEqual(frozen["controlled_authored_case_count"], 40)
        self.assertEqual(frozen["grounded_target_count"], 85)
        self.assertEqual(self.config["expected_judgment_count"], 170)

    def test_only_one_matched_representation_change_is_allowed(self):
        self.assertEqual(
            self.config["conditions"],
            ["v51_event_map_control", "precise_target_mentions_candidate"],
        )
        change = self.config["causal_change"]
        self.assertIn("replace only", change["candidate"])
        self.assertFalse(change["direct_deterministic_commitment_override"])
        self.assertFalse(change["direct_deterministic_execution_override"])

    def test_gold_and_provenance_fields_are_forbidden_from_model_payload(self):
        forbidden = set(self.config["causal_change"]["forbidden_fields"])
        self.assertTrue(
            {
                "expected_frames",
                "expected_calls",
                "family",
                "source_type",
                "source_provenance",
                "evaluation_tags",
            }.issubset(forbidden)
        )

    def test_advancement_requires_targeted_gain_and_zero_regression(self):
        gates = self.config["matched_comparison_gates"]
        self.assertEqual(gates["targeted_commitment_correct_count_delta_at_least"], 1)
        self.assertEqual(gates["targeted_compiled_call_exact_count_delta_at_least"], 1)
        self.assertEqual(gates["semantic_regression_count"], 0)
        self.assertEqual(gates["call_regression_count"], 0)
        self.assertEqual(self.config["candidate_absolute_gates"]["false_action_count"], 0)

    def test_no_runtime_or_physical_execution_is_pre_authorized(self):
        self.assertFalse(self.config["prompt_or_map_tuning_after_run_authorized"])
        self.assertFalse(self.config["fresh_holdout_claim_authorized"])
        self.assertFalse(self.config["runtime_change_authorized"])
        self.assertFalse(self.config["shadow_integration_authorized"])
        self.assertFalse(self.config["physical_vrm_execution_enabled"])
        self.assertFalse(self.config["human_likeness_claim_authorized"])


if __name__ == "__main__":
    unittest.main()
