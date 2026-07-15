#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "commitment_model_capacity_v46_preregistration.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CommitmentModelCapacityV46PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def test_retired_development_inputs_are_hash_bound(self):
        frozen = self.config["frozen_retired_development_inputs"]
        for key, expected in frozen.items():
            if not key.endswith("_sha256"):
                continue
            self.assertEqual(_sha256(ROOT / frozen[key.removesuffix("_sha256")]), expected)
        self.assertIn("retired into development data", self.config["evidence_boundary"])
        self.assertIn("cannot provide a new holdout", self.config["evidence_boundary"])

    def test_five_local_models_are_frozen_before_inference(self):
        models = self.config["model_conditions"]
        self.assertEqual(len(models), 5)
        self.assertEqual(len({row["condition"] for row in models}), 5)
        self.assertEqual(len({row["digest"] for row in models}), 5)
        self.assertEqual(self.config["expected_judgment_count"], 5 * 63)
        self.assertEqual(
            self.config["fixed_generation"]["prompt_condition"],
            "taxonomy_plus_discourse_signals_candidate",
        )

    def test_selection_requires_safety_before_speed_or_size(self):
        gates = self.config["eligibility_gates"]
        self.assertEqual(gates["requested_commitment_precision"], 1.0)
        self.assertEqual(gates["false_action_rate"], 0.0)
        self.assertEqual(gates["extra_candidate_requested_count"], 0)
        self.assertEqual(gates["unsupported_execution_count"], 0)
        self.assertIn("fails any eligibility gate", self.config["selection_rule"]["step_1"])
        self.assertIn("within one correct target", self.config["selection_rule"]["step_3"])

    def test_no_result_can_pre_authorize_runtime_or_reuse_as_holdout(self):
        self.assertFalse(self.config["prompt_or_parser_tuning_after_run_authorized"])
        self.assertFalse(self.config["fresh_holdout_claim_authorized"])
        self.assertFalse(self.config["runtime_change_authorized"])
        self.assertFalse(self.config["shadow_integration_authorized"])
        self.assertFalse(self.config["physical_vrm_execution_enabled"])


if __name__ == "__main__":
    unittest.main()
