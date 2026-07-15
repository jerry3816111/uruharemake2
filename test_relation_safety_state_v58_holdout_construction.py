#!/usr/bin/env python3

import json
import unittest
from pathlib import Path

from audit_relation_safety_state_v58_holdout import (
    DATASET_PATH,
    MENTION_CONFIG_PATH,
    SOURCE_PATH,
    audit,
)
from build_relation_safety_state_v58_holdout import build


ROOT = Path(__file__).resolve().parent
AUDIT_PATH = ROOT / "reports" / "relation_safety_state_v58_holdout_audit.json"


class RelationSafetyStateV58HoldoutConstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load = lambda path: json.loads(path.read_text(encoding="utf-8"))
        cls.dataset = load(DATASET_PATH)
        cls.audit = load(AUDIT_PATH)
        cls.mention_config = load(MENTION_CONFIG_PATH)

    def test_builder_reproduces_frozen_dataset(self):
        self.assertEqual(build(), self.dataset)

    def test_source_and_family_design_is_exact(self):
        self.assertEqual(self.dataset["case_count"], 64)
        self.assertEqual(
            self.dataset["source_counts"],
            {"controlled_compositional": 48, "external_exact": 16},
        )
        self.assertEqual(
            self.dataset["family_counts"],
            {
                "controlled_deferred_preference": 12,
                "controlled_exclusive_alternative": 12,
                "controlled_past_benefactive_description": 12,
                "controlled_relation_contrast": 12,
                "external_tatoeba_relation_safety": 16,
            },
        )
        self.assertEqual(len(SOURCE_PATH.read_text(encoding="utf-8").splitlines()), 16)

    def test_construction_audit_passes_without_overlap(self):
        recomputed = audit(
            self.dataset, self.mention_config["target_mention_patterns"]
        )
        self.assertTrue(recomputed["passed"])
        self.assertEqual(recomputed["failed_checks"], [])
        self.assertEqual(recomputed["historical_exact_input_overlap_count"], 0)
        self.assertEqual(recomputed["historical_near_duplicate_count"], 0)
        self.assertEqual(recomputed["prior_external_source_id_overlap_count"], 0)
        self.assertLess(recomputed["maximum_historical_similarity"], 0.94)

    def test_action_abstention_and_target_coverage_prevent_trivial_pass(self):
        self.assertEqual(self.audit["target_count"], 87)
        self.assertEqual(self.audit["distinct_target_count"], 14)
        self.assertEqual(self.audit["action_case_count"], 13)
        self.assertEqual(self.audit["no_action_case_count"], 51)
        self.assertEqual(self.audit["commitment_counts"]["requested"], 17)

    def test_provenance_does_not_overclaim_official_or_human_review(self):
        construction = self.dataset["construction"]
        self.assertFalse(construction["external_exact_model_generation_used"])
        self.assertTrue(construction["controlled_model_assistance_used"])
        self.assertFalse(construction["controlled_human_blind_review_used"])
        self.assertFalse(construction["evaluation_model_inference_used"])
        self.assertFalse(construction["v56_or_v58_state_evaluation_used"])
        self.assertFalse(construction["base_model_pretraining_exclusion_guaranteed"])
        for case in self.dataset["cases"]:
            if case["source_type"] == "external_exact":
                self.assertIn("tatoeba.org/en/sentences/show/", case["source_provenance"]["sentence_url"])
            else:
                self.assertFalse(case["source_provenance"]["official_corpus_claimed"])

    def test_construction_code_has_no_state_or_model_evaluation(self):
        source = (
            (ROOT / "build_relation_safety_state_v58_holdout.py").read_text(
                encoding="utf-8"
            )
            + (ROOT / "audit_relation_safety_state_v58_holdout.py").read_text(
                encoding="utf-8"
            )
        )
        for forbidden in (
            "resolve_v56",
            "resolve_v58",
            "_run_judgment",
            "urllib.request",
            "requests.post",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
