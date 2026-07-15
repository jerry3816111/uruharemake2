#!/usr/bin/env python3

import json
import unittest
from pathlib import Path

from audit_relation_bound_event_graph_v56_holdout import audit


ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "datasets" / "relation_bound_event_graph_v56_holdout.json"
V52_CONFIG_PATH = ROOT / "configs" / "precise_target_mentions_v52_preregistration.json"


class RelationBoundEventGraphV56HoldoutDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
        v52 = json.loads(V52_CONFIG_PATH.read_text(encoding="utf-8"))
        cls.audit = audit(
            cls.dataset, v52["causal_change"]["target_mention_patterns"]
        )

    def test_sources_are_balanced_and_distinguished(self):
        self.assertEqual(self.dataset["case_count"], 64)
        self.assertEqual(self.dataset["source_counts"]["external_exact"], 32)
        self.assertEqual(
            self.dataset["source_counts"]["controlled_compositional"], 32
        )

    def test_eight_controlled_relation_families_are_balanced(self):
        controlled = {
            family: count
            for family, count in self.dataset["family_counts"].items()
            if family.startswith("controlled_")
        }
        self.assertEqual(len(controlled), 8)
        self.assertEqual(set(controlled.values()), {4})

    def test_generation_provenance_is_not_overclaimed(self):
        construction = self.dataset["construction"]
        self.assertFalse(construction["external_exact_model_generation_used"])
        self.assertTrue(construction["controlled_model_assistance_used"])
        self.assertFalse(construction["evaluation_model_inference_used"])
        self.assertFalse(construction["base_model_pretraining_exclusion_guaranteed"])

    def test_freshness_and_source_checks_pass(self):
        self.assertEqual(self.audit["historical_exact_overlaps"], [])
        self.assertEqual(self.audit["old_source_id_overlaps"], [])
        self.assertEqual(self.audit["source_errors"], [])

    def test_candidate_and_mention_representation_is_exact(self):
        self.assertEqual(self.audit["target_count"], 81)
        self.assertEqual(self.audit["candidate_mismatches"], [])
        representation = self.audit["representation_audit"]
        self.assertEqual(representation["grounded_occurrence_mention_coverage"], 1.0)
        self.assertEqual(representation["fallback_occurrence_count"], 0)
        self.assertEqual(representation["cross_target_mention_overlap_count"], 0)

    def test_full_construction_gate_passes(self):
        self.assertTrue(self.audit["passed"], self.audit["failed_checks"])


if __name__ == "__main__":
    unittest.main()
