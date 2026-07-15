#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "target_event_map_v51_preregistration.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TargetEventMapV51PreregistrationTests(unittest.TestCase):
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

    def test_one_causal_change_and_no_answer_fields(self):
        self.assertEqual(
            self.config["conditions"],
            ["v48_six_way_control", "target_event_map_candidate"],
        )
        change = self.config["causal_change"]
        self.assertFalse(change["direct_deterministic_commitment_override"])
        self.assertFalse(change["direct_deterministic_execution_override"])
        self.assertIn("gold_commitment", change["forbidden_fields"])
        self.assertIn("expected_calls", change["forbidden_fields"])
        self.assertIn("最後の出現だから requested とは限らず", change["candidate_instruction"])
        self.assertIn("解析対象データ", change["candidate_instruction"])

    def test_model_and_expected_judgments_are_fixed(self):
        self.assertEqual(self.config["fixed_model"]["ollama_tag"], "qwen3.5:4b")
        self.assertEqual(
            self.config["expected_judgment_count"],
            len(self.config["conditions"])
            * self.config["frozen_inputs"]["grounded_target_count"],
        )

    def test_advancement_requires_real_gain_and_zero_false_actions(self):
        absolute = self.config["candidate_absolute_gates"]
        matched = self.config["matched_comparison_gates"]
        self.assertEqual(absolute["false_action_count"], 0)
        self.assertGreaterEqual(absolute["compiled_call_exact_count_at_least"], 45)
        self.assertGreaterEqual(
            matched["compiled_call_exact_count_delta_at_least"], 2
        )
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
