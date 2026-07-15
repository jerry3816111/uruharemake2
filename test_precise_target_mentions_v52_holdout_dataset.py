#!/usr/bin/env python3

import json
import unittest
from pathlib import Path

from audit_precise_target_mentions_v52_holdout import audit


ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "datasets" / "precise_target_mentions_v52_holdout.json"
V52_CONFIG_PATH = ROOT / "configs" / "precise_target_mentions_v52_preregistration.json"


class PreciseTargetMentionsV52HoldoutDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
        cls.v52_config = json.loads(V52_CONFIG_PATH.read_text(encoding="utf-8"))
        cls.audit = audit(
            cls.dataset,
            cls.v52_config["causal_change"]["target_mention_patterns"],
        )

    def test_holdout_has_locked_external_and_controlled_counts(self):
        self.assertEqual(self.dataset["case_count"], 64)
        self.assertEqual(self.dataset["source_counts"]["external_exact"], 24)
        self.assertEqual(self.dataset["source_counts"]["controlled_authored"], 40)

    def test_no_model_was_used_to_construct_the_holdout(self):
        construction = self.dataset["construction"]
        self.assertFalse(construction["model_generation_used"])
        self.assertFalse(construction["model_inference_used"])
        self.assertFalse(construction["base_model_pretraining_exclusion_guaranteed"])

    def test_candidate_targets_and_gold_are_exactly_aligned(self):
        self.assertTrue(self.audit["checks"]["candidate_target_sets_exact"])
        self.assertEqual(self.audit["target_count"], 85)

    def test_holdout_does_not_repeat_prior_project_inputs(self):
        self.assertEqual(self.audit["historical_exact_overlaps"], [])
        self.assertGreaterEqual(self.audit["historical_input_count"], 700)

    def test_precise_mentions_cover_every_grounded_occurrence(self):
        representation = self.audit["representation_audit"]
        self.assertEqual(representation["grounded_occurrence_mention_coverage"], 1.0)
        self.assertEqual(representation["fallback_occurrence_count"], 0)
        self.assertEqual(representation["cross_target_mention_overlap_count"], 0)

    def test_full_construction_audit_passes(self):
        self.assertTrue(self.audit["passed"], self.audit["failed_checks"])


if __name__ == "__main__":
    unittest.main()
