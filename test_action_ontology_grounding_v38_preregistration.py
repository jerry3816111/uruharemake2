#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "action_ontology_grounding_v38_preregistration.json"
RAW_PATH = ROOT / "reports" / "action_selective_deliberation_v37_development_raw.json"
DATASET_PATH = ROOT / "datasets" / "action_selective_deliberation_v37_development.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ActionOntologyGroundingV38PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def test_replay_sources_are_frozen_before_new_code(self):
        scope = self.config["causal_scope"]
        self.assertEqual(scope["frozen_primary_output_sha256"], _sha256(RAW_PATH))
        self.assertEqual(scope["fixed_development_input_sha256"], _sha256(DATASET_PATH))
        self.assertIn("No new model inference", scope["replay_rule"])

    def test_ontology_covers_every_supported_vrm_value(self):
        ontology = self.config["action_anchor_ontology"]
        expected = {
            "expression.neutral", "expression.happy", "expression.sad",
            "expression.angry", "expression.surprised", "motion.idle",
            "motion.wave", "motion.nod", "motion.shake_head", "motion.point",
            "gaze.left", "gaze.right", "gaze.user", "gaze.down",
        }
        self.assertEqual(set(ontology), expected)
        self.assertTrue(all(patterns for patterns in ontology.values()))

    def test_ablation_conditions_change_named_components(self):
        conditions = self.config["matched_replay_conditions"]
        self.assertEqual(
            set(conditions),
            {
                "v37_single_control",
                "anchor_grounding_only",
                "local_isolation_only",
                "full_v38_candidate",
            },
        )

    def test_development_cannot_authorize_runtime(self):
        self.assertFalse(self.config["runtime_change_authorized"])
        self.assertFalse(self.config["vrm_execution_enabled"])
        self.assertIn("Development replay cannot authorize runtime", self.config["decision_rule"])

    def test_fresh_holdout_requires_zero_false_actions(self):
        policy = self.config["fresh_holdout_policy"]
        self.assertTrue(policy["freeze_and_commit_before_inference"])
        self.assertEqual(policy["gates"]["false_action_rate"], 0.0)
        self.assertEqual(policy["gates"]["accepted_call_anchor_coverage"], 1.0)


if __name__ == "__main__":
    unittest.main()
