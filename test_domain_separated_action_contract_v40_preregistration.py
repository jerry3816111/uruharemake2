#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs" / "domain_separated_action_contract_v40_preregistration.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DomainSeparatedActionContractV40PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_probe_and_fixed_inputs_are_bound_by_hash(self):
        boundary = self.config["infrastructure_boundary"]
        scope = self.config["causal_scope"]
        self.assertEqual(
            _sha256(ROOT / boundary["probe_source"]), boundary["probe_sha256"]
        )
        self.assertEqual(
            _sha256(ROOT / scope["fixed_development_dataset"]),
            scope["fixed_development_dataset_sha256"],
        )
        self.assertEqual(
            _sha256(ROOT / scope["fixed_v39_compiler_source"]),
            scope["fixed_v39_compiler_sha256"],
        )
        self.assertEqual(
            _sha256(ROOT / scope["matched_control_source"]),
            scope["matched_control_sha256"],
        )

    def test_only_output_contract_changes(self):
        scope = self.config["causal_scope"]
        self.assertEqual(
            scope["single_changed_factor"],
            "model output contract and its matching instructions",
        )
        self.assertEqual(scope["fixed_model"], "qwen3.5:4b")
        self.assertEqual(scope["fixed_temperature"], 0.0)
        self.assertFalse(scope["fixed_thinking"])
        self.assertEqual(scope["fixed_persona_adapter"], "none")

    def test_conditional_schema_is_explicitly_excluded(self):
        boundary = self.config["infrastructure_boundary"]
        self.assertTrue(boundary["observed_json_parse_success"])
        self.assertFalse(boundary["observed_one_of_contract_success"])
        self.assertIn("Do not use oneOf", boundary["decision"])

    def test_fresh_data_is_not_authorized_before_development(self):
        self.assertTrue(
            self.config["fresh_holdout"]["authorized_only_after_development_pass"]
        )
        self.assertTrue(self.config["fresh_holdout"]["freeze_and_commit_before_inference"])
        self.assertFalse(self.config["runtime_change_authorized"])
        self.assertFalse(self.config["shadow_integration_authorized"])
        self.assertFalse(self.config["physical_vrm_execution_enabled"])


if __name__ == "__main__":
    unittest.main()
