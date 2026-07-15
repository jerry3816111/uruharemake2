#!/usr/bin/env python3

import json
import unittest
from pathlib import Path

from audit_metalinguistic_nonrequest_v54_holdout import audit


ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "datasets" / "metalinguistic_nonrequest_v54_holdout.json"
V52_CONFIG_PATH = ROOT / "configs" / "precise_target_mentions_v52_preregistration.json"


class MetalinguisticNonrequestV54HoldoutDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
        v52 = json.loads(V52_CONFIG_PATH.read_text(encoding="utf-8"))
        cls.audit = audit(
            cls.dataset, v52["causal_change"]["target_mention_patterns"]
        )

    def test_holdout_has_balanced_external_and_controlled_sources(self):
        self.assertEqual(self.dataset["case_count"], 64)
        self.assertEqual(self.dataset["source_counts"]["external_exact"], 32)
        self.assertEqual(self.dataset["source_counts"]["controlled_authored"], 32)

    def test_controlled_cases_cover_eight_balanced_families(self):
        controlled = {
            family: count
            for family, count in self.dataset["family_counts"].items()
            if family.startswith("controlled_")
        }
        self.assertEqual(len(controlled), 8)
        self.assertEqual(set(controlled.values()), {4})

    def test_no_model_was_used_during_construction(self):
        construction = self.dataset["construction"]
        self.assertFalse(construction["model_generation_used"])
        self.assertFalse(construction["model_inference_used"])
        self.assertFalse(construction["base_model_pretraining_exclusion_guaranteed"])

    def test_freshness_and_source_checks_pass(self):
        self.assertEqual(self.audit["historical_exact_overlaps"], [])
        self.assertEqual(self.audit["old_source_id_overlaps"], [])
        self.assertEqual(self.audit["source_errors"], [])

    def test_candidate_and_precise_mention_representation_is_exact(self):
        self.assertEqual(self.audit["target_count"], 76)
        self.assertEqual(self.audit["candidate_mismatches"], [])
        representation = self.audit["representation_audit"]
        self.assertEqual(representation["grounded_occurrence_mention_coverage"], 1.0)
        self.assertEqual(representation["fallback_occurrence_count"], 0)
        self.assertEqual(representation["cross_target_mention_overlap_count"], 0)

    def test_full_construction_gate_passes(self):
        self.assertTrue(self.audit["passed"], self.audit["failed_checks"])


if __name__ == "__main__":
    unittest.main()
