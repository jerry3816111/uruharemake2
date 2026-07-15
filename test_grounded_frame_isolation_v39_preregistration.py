#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "grounded_frame_isolation_v39_preregistration.json"
V38_CONFIG_PATH = ROOT / "configs" / "action_ontology_grounding_v38_preregistration.json"
RAW_PATH = ROOT / "reports" / "action_selective_deliberation_v37_development_raw.json"
DATASET_PATH = ROOT / "datasets" / "action_selective_deliberation_v37_development.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class GroundedFrameIsolationV39PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def test_development_sources_are_frozen(self):
        scope = self.config["causal_scope"]
        self.assertEqual(scope["base_ontology_sha256"], _sha256(V38_CONFIG_PATH))
        self.assertEqual(scope["development_raw_sha256"], _sha256(RAW_PATH))
        self.assertEqual(scope["development_dataset_sha256"], _sha256(DATASET_PATH))
        self.assertTrue(scope["development_replay_only"])

    def test_colloquial_anchor_is_general_and_has_near_miss_requirement(self):
        additions = self.config["ontology_additions"]
        self.assertIn("motion.nod", additions)
        self.assertIn("うん", additions["motion.nod"][0])
        self.assertIn("must not become a nod", self.config["near_miss_requirement"])

    def test_execution_and_trace_are_separate_metrics(self):
        parser = self.config["frame_local_parser"]
        self.assertIn("Invalid individual frames are dropped", parser["execution_parse_success"])
        self.assertIn("no isolated frame warnings", parser["trace_wellformed"])
        self.assertEqual(self.config["development_gates"]["execution_parse_success_rate"], 1.0)
        self.assertGreaterEqual(self.config["fresh_holdout"]["gates"]["trace_wellformed_rate_at_least"], 0.95)

    def test_fresh_holdout_is_frozen_before_inference(self):
        holdout = self.config["fresh_holdout"]
        self.assertEqual(holdout["case_count"], 48)
        self.assertEqual(len(holdout["families"]), 8)
        self.assertTrue(holdout["freeze_and_commit_before_inference"])
        self.assertEqual(holdout["gates"]["false_action_rate"], 0.0)

    def test_runtime_stays_shadow_only_even_after_pass(self):
        self.assertFalse(self.config["runtime_change_authorized"])
        self.assertFalse(self.config["physical_vrm_execution_enabled"])
        self.assertIn("shadow integration", self.config["decision_rule"])


if __name__ == "__main__":
    unittest.main()
