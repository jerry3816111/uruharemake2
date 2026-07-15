#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "selective_discourse_state_v53_preregistration.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SelectiveDiscourseStateV53PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def test_every_local_input_is_hash_bound(self):
        frozen = self.config["frozen_inputs"]
        for key, expected in frozen.items():
            if not key.endswith("_sha256"):
                continue
            path = ROOT / frozen[key.removesuffix("_sha256")]
            self.assertEqual(_sha256(path), expected, path)

    def test_consumed_evidence_boundary_is_explicit(self):
        self.assertIn("consumed V52", self.config["evidence_boundary"])
        self.assertFalse(self.config["fresh_generalization_claim_authorized"])
        self.assertEqual(self.config["frozen_inputs"]["case_count"], 64)
        self.assertEqual(self.config["frozen_inputs"]["grounded_target_count"], 85)

    def test_matched_control_and_two_state_conditions_are_fixed(self):
        self.assertEqual(
            self.config["conditions"],
            [
                "frozen_v51_model_control",
                "deterministic_state_machine_only",
                "selective_state_machine_with_v51_fallback",
            ],
        )
        change = self.config["single_causal_change"]
        self.assertFalse(change["direct_execution_override"])
        self.assertFalse(change["compiler_bypass"])

    def test_gate_requires_safety_gain_and_nearly_no_regression(self):
        gates = self.config["development_gates"]
        self.assertEqual(gates["hybrid_false_action_count"], 0)
        self.assertEqual(gates["hybrid_no_action_specificity"], 1.0)
        self.assertEqual(gates["compiled_call_exact_count_delta_at_least"], 4)
        self.assertEqual(gates["semantic_regression_count_at_most"], 1)
        self.assertEqual(gates["call_regression_count_at_most"], 0)

    def test_model_and_runtime_are_not_authorized(self):
        self.assertFalse(self.config["model_calls_authorized"])
        self.assertFalse(self.config["runtime_change_authorized"])
        self.assertFalse(self.config["shadow_integration_authorized"])
        self.assertFalse(self.config["physical_vrm_execution_enabled"])
        self.assertFalse(self.config["human_likeness_claim_authorized"])


if __name__ == "__main__":
    unittest.main()
