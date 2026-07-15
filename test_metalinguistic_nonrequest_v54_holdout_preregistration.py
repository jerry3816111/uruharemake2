#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "metalinguistic_nonrequest_v54_holdout_preregistration.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class MetalinguisticNonrequestV54HoldoutPreregistrationTests(unittest.TestCase):
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

    def test_dataset_and_model_call_budget_are_locked(self):
        frozen = self.config["frozen_inputs"]
        self.assertEqual(frozen["case_count"], 64)
        self.assertEqual(frozen["external_exact_case_count"], 32)
        self.assertEqual(frozen["controlled_authored_case_count"], 32)
        self.assertEqual(frozen["grounded_target_count"], 76)
        self.assertEqual(self.config["model_call_budget"], 76)

    def test_conditions_share_one_fresh_v51_fallback(self):
        self.assertEqual(
            self.config["conditions"],
            [
                "fresh_v51_model_control",
                "v54_deterministic_state_machine_only",
                "v54_selective_state_machine_with_fresh_v51_fallback",
            ],
        )
        self.assertIn("exactly once per grounded target", self.config["model_usage_policy"])

    def test_state_and_end_to_end_claims_are_separate(self):
        self.assertEqual(
            self.config["state_component_gates"]["positive_idle_state_accuracy"],
            1.0,
        )
        self.assertEqual(self.config["end_to_end_gates"]["false_action_count"], 0)
        self.assertIn("compiler", self.config["failure_routing"])

    def test_model_size_experiment_requires_a_frozen_abstention_trigger(self):
        trigger = self.config["model_escalation_rule"]
        self.assertGreaterEqual(trigger["minimum_fallback_targets"], 4)
        self.assertLess(trigger["fallback_accuracy_below"], 1.0)
        self.assertIn("smallest model", trigger["next_experiment"])

    def test_no_runtime_or_physical_execution_is_pre_authorized(self):
        self.assertFalse(self.config["post_run_tuning_authorized"])
        self.assertFalse(self.config["runtime_change_authorized"])
        self.assertFalse(self.config["shadow_integration_authorized"])
        self.assertFalse(self.config["physical_vrm_execution_enabled"])
        self.assertFalse(self.config["human_likeness_claim_authorized"])


if __name__ == "__main__":
    unittest.main()
