#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "predicate_morphology_v60_independent_holdout_construction_preregistration.json"
)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PredicateMorphologyV60IndependentConstructionPreregistrationTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def test_candidate_and_development_evidence_are_hash_frozen(self):
        frozen = self.config["frozen_candidate"]
        self.assertEqual(
            _sha256(ROOT / frozen["implementation"]), frozen["implementation_sha256"]
        )
        self.assertEqual(
            _sha256(ROOT / frozen["development_closure"]),
            frozen["development_closure_sha256"],
        )

    def test_external_ids_are_unique_and_not_historically_selected(self):
        selected = self.config["external_source"]["selected_sentence_ids"]
        historical = {
            int(line.split("\t", 1)[0])
            for path in (ROOT / "datasets" / "sources").glob("tatoeba_jpn_v*.tsv")
            if path.name != "tatoeba_jpn_v60_selected.tsv"
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertEqual(len(selected), len(set(selected)))
        self.assertTrue(set(selected).isdisjoint(historical))
        self.assertEqual(len(selected), self.config["external_source"]["case_count"])

    def test_controlled_matrix_is_complete_and_counted(self):
        matrix = self.config["controlled_matrix"]
        self.assertEqual(len(matrix["target_ids_per_family"]), 14)
        self.assertEqual(len(matrix["families"]), 7)
        self.assertTrue(
            all(row["case_count"] == 14 for row in matrix["families"].values())
        )
        self.assertEqual(matrix["case_count"], 98)
        self.assertEqual(matrix["grounded_target_count"], 98)

    def test_frozen_totals_match_source_components(self):
        external = self.config["external_source"]
        controlled = self.config["controlled_matrix"]
        totals = self.config["frozen_totals"]
        self.assertEqual(
            totals["case_count"], external["case_count"] + controlled["case_count"]
        )
        self.assertEqual(
            totals["grounded_target_count"],
            external["grounded_target_count"] + controlled["grounded_target_count"],
        )
        self.assertEqual(
            totals["expected_action_case_count"]
            + totals["expected_no_action_case_count"],
            totals["case_count"],
        )

    def test_construction_does_not_claim_official_labels_or_unseen_pretraining(self):
        external = self.config["external_source"]
        self.assertFalse(external["official_labels_provided"])
        self.assertTrue(external["labels_are_researcher_authored"])
        self.assertFalse(external["base_model_pretraining_exclusion_guaranteed"])
        self.assertFalse(self.config["controlled_matrix"]["official_corpus_claimed"])

    def test_no_evaluation_or_deployment_is_authorized(self):
        for key in (
            "construction_before_preregistration_merge_authorized",
            "evaluation_before_dataset_closure_authorized",
            "runtime_change_authorized",
            "physical_vrm_execution_enabled",
            "complete_rightbrain_claim_authorized",
            "broad_human_likeness_claim_authorized",
        ):
            self.assertFalse(self.config[key], key)
        self.assertEqual(self.config["model_calls_authorized"], 0)


if __name__ == "__main__":
    unittest.main()
