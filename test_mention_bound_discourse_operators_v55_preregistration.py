#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "mention_bound_discourse_operators_v55_preregistration.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class MentionBoundDiscourseOperatorsV55PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def test_every_local_frozen_input_is_hash_bound(self):
        for key, expected in self.config["frozen_inputs"].items():
            if not key.endswith("_sha256"):
                continue
            path = ROOT / self.config["frozen_inputs"][key.removesuffix("_sha256")]
            self.assertEqual(_sha256(path), expected, path)

    def test_replay_uses_frozen_v54_and_no_model(self):
        self.assertEqual(
            self.config["conditions"][0], "frozen_v54_hybrid_control"
        )
        self.assertFalse(self.config["model_calls_authorized"])
        self.assertEqual(self.config["frozen_inputs"]["grounded_target_count"], 76)

    def test_six_attributed_failures_are_locked_before_replay(self):
        failures = self.config["targeted_development_failures"]
        self.assertEqual(len(failures), 6)
        self.assertEqual(
            {row["failure_class"] for row in failures},
            {
                "pending_scope_leakage",
                "request_force_leakage",
                "execution_prohibition_paraphrase",
                "cross_domain_correction",
                "unresolved_finite_assertion",
            },
        )

    def test_advancement_requires_six_fixes_and_zero_regression(self):
        gates = self.config["development_gates"]
        self.assertEqual(gates["targeted_fixed_count_at_least"], 6)
        self.assertEqual(gates["commitment_correct_count_delta_at_least"], 6)
        self.assertEqual(gates["semantic_regression_count"], 0)
        self.assertEqual(gates["false_action_count"], 0)

    def test_runtime_and_physical_execution_remain_disabled(self):
        self.assertFalse(self.config["runtime_change_authorized"])
        self.assertFalse(self.config["shadow_integration_authorized"])
        self.assertFalse(self.config["physical_vrm_execution_enabled"])


if __name__ == "__main__":
    unittest.main()
