#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "relation_bound_event_graph_v56_preregistration.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RelationBoundEventGraphV56PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def test_every_frozen_hash_matches(self):
        for key, expected in self.config["frozen_inputs"].items():
            if not key.endswith("_sha256"):
                continue
            path = ROOT / self.config["frozen_inputs"][key.removesuffix("_sha256")]
            self.assertEqual(_sha256(path), expected, path)

    def test_conditions_include_strong_and_rejected_controls(self):
        self.assertEqual(
            self.config["conditions"],
            [
                "frozen_v54_hybrid_control",
                "frozen_rejected_v55_hybrid",
                "v56_deterministic_relation_graph_only",
                "v56_selective_relation_graph_with_frozen_v51_fallback",
            ],
        )

    def test_locked_targets_and_strict_gates(self):
        self.assertEqual(len(self.config["targeted_v54_failures"]), 6)
        self.assertEqual(len(self.config["v55_regression_cases"]), 7)
        gates = self.config["development_gates"]
        self.assertEqual(gates["hybrid_commitment_accuracy_at_least"], 1.0)
        self.assertEqual(gates["semantic_regression_count"], 0)
        self.assertEqual(gates["call_regression_count"], 0)
        self.assertEqual(gates["false_action_count"], 0)

    def test_no_model_or_integration_is_authorized(self):
        self.assertFalse(self.config["model_calls_authorized"])
        self.assertFalse(self.config["runtime_change_authorized"])
        self.assertFalse(self.config["shadow_integration_authorized"])
        self.assertFalse(self.config["physical_vrm_execution_enabled"])


if __name__ == "__main__":
    unittest.main()
