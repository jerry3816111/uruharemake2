#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "metalinguistic_nonrequest_v54_preregistration.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class MetalinguisticNonrequestV54PreregistrationTests(unittest.TestCase):
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

    def test_only_metalinguistic_distinction_can_change(self):
        change = self.config["single_causal_change"]
        self.assertFalse(change["other_transition_changes_authorized"])
        self.assertFalse(change["fallback_change_authorized"])
        self.assertFalse(change["ontology_change_authorized"])
        self.assertFalse(change["compiler_change_authorized"])
        self.assertFalse(change["new_model_call_authorized"])

    def test_specific_gate_requires_exactly_three_safe_corrections(self):
        gates = self.config["v54_specific_gates"]
        self.assertEqual(gates["correction_count"], 3)
        self.assertEqual(gates["corrected_rule_accuracy"], 1.0)
        self.assertEqual(gates["v53_previously_correct_target_regression_count"], 0)
        self.assertEqual(gates["v53_previously_correct_call_regression_count"], 0)

    def test_consumed_data_cannot_authorize_runtime(self):
        self.assertIn("consumed V52", self.config["evidence_boundary"])
        self.assertFalse(self.config["model_calls_authorized"])
        self.assertFalse(self.config["fresh_generalization_claim_authorized"])
        self.assertFalse(self.config["runtime_change_authorized"])
        self.assertFalse(self.config["shadow_integration_authorized"])
        self.assertFalse(self.config["physical_vrm_execution_enabled"])


if __name__ == "__main__":
    unittest.main()
