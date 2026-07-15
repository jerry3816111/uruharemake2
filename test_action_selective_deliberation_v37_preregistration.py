#!/usr/bin/env python3

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "action_selective_deliberation_v37_preregistration.json"


class ActionSelectiveDeliberationV37PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def test_evidence_boundary_preserves_fresh_holdout(self):
        boundary = self.config["evidence_boundary"]
        self.assertEqual(boundary["development_status"], "retired_and_already_observed")
        self.assertTrue(boundary["development_results_cannot_authorize_runtime"])
        self.assertIn("Freeze and commit", boundary["fresh_confirmation_rule"])

    def test_candidate_is_matched_local_4b(self):
        model = self.config["model"]
        self.assertEqual(model["ollama_tag"], "qwen3.5:4b")
        self.assertEqual(len(model["digest"]), 64)
        self.assertFalse(model["thinking"])
        self.assertFalse(self.config["generation_shared"]["paid_api"])

    def test_three_fixed_independent_passes_are_preregistered(self):
        passes = self.config["generation_passes"]
        self.assertEqual([row["pass_id"] for row in passes], [
            "primary",
            "deliberation_a",
            "deliberation_b",
        ])
        self.assertEqual(len({row["seed"] for row in passes}), 3)
        self.assertEqual(passes[0]["temperature"], 0.0)
        self.assertGreater(passes[1]["temperature"], 0.0)

    def test_selective_policy_is_only_advancement_candidate(self):
        rule = self.config["decision_rule"]
        self.assertIn("Only selective_three_pass_v37_candidate", rule)
        self.assertIn("every development gate", rule)
        self.assertIn("every frozen fresh-holdout gate", rule)

    def test_false_actions_must_be_zero(self):
        self.assertEqual(self.config["development_gates"]["false_action_rate"], 0.0)
        self.assertEqual(self.config["fresh_holdout_gates"]["false_action_rate"], 0.0)
        self.assertEqual(self.config["development_gates"]["negation_violation_count"], 0)

    def test_runtime_and_execution_remain_disabled(self):
        self.assertFalse(self.config["runtime_change_authorized"])
        self.assertFalse(self.config["vrm_execution_enabled"])
        self.assertFalse(self.config["human_likeness_claim_authorized"])


if __name__ == "__main__":
    unittest.main()
