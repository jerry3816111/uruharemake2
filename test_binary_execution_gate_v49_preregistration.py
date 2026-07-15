#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "binary_execution_gate_v49_preregistration.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class BinaryExecutionGateV49PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def test_every_historical_input_is_hash_bound(self):
        frozen = self.config["frozen_inputs"]
        for key, expected in frozen.items():
            if key.endswith("_sha256"):
                self.assertEqual(
                    _sha256(ROOT / frozen[key.removesuffix("_sha256")]), expected
                )

    def test_three_local_models_and_judgment_count_are_fixed(self):
        models = self.config["model_conditions"]
        self.assertEqual(
            [row["ollama_tag"] for row in models],
            ["qwen3.5:0.8b", "qwen3.5:2b", "qwen3.5:4b"],
        )
        self.assertEqual(
            self.config["expected_judgment_count"],
            len(models) * self.config["frozen_inputs"]["grounded_target_count"],
        )

    def test_contract_is_one_boolean_plus_version_ack(self):
        contract = self.config["binary_contract"]
        self.assertEqual(set(contract["properties"]), {"execute_now", "contract_ack"})
        self.assertEqual(contract["properties"]["execute_now"]["type"], "boolean")
        self.assertEqual(contract["properties"]["contract_ack"]["const"], "v49")
        self.assertFalse(contract["additionalProperties"])

    def test_selection_requires_safety_and_recall_before_model_size(self):
        gates = self.config["eligibility_gates"]
        self.assertEqual(gates["execute_precision"], 1.0)
        self.assertEqual(gates["execute_recall_at_least"], 0.9)
        self.assertEqual(gates["false_action_rate"], 0.0)
        self.assertEqual(gates["no_action_specificity"], 1.0)
        self.assertIn("fails", self.config["selection_rule"]["step_1"])

    def test_consumed_data_cannot_authorize_runtime(self):
        self.assertFalse(self.config["prompt_or_parser_tuning_after_run_authorized"])
        self.assertFalse(self.config["fresh_holdout_claim_authorized"])
        self.assertFalse(self.config["runtime_change_authorized"])
        self.assertFalse(self.config["shadow_integration_authorized"])
        self.assertFalse(self.config["physical_vrm_execution_enabled"])


if __name__ == "__main__":
    unittest.main()
