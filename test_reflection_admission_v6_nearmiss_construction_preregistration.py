#!/usr/bin/env python3
"""Validate the V6 near-miss construction contract before source fetching."""

from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG = (
    ROOT
    / "configs"
    / "reflection_admission_v6_nearmiss_construction_preregistration.json"
)
EXISTING_REFLECTION_DATASETS = (
    ROOT / "datasets" / "reflection_classifier_v1_external_holdout.json",
    ROOT / "datasets" / "reflection_hybrid_classifier_v4_independent_holdout.json",
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


class ReflectionAdmissionNearMissConstructionPreregistrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = _load(CONFIG)
        cls.cases = cls.config["selected_cases"]

    def test_exact_balanced_distribution_is_frozen(self):
        distribution = self.config["frozen_distribution"]
        self.assertEqual(len(self.cases), distribution["case_count"])
        self.assertEqual(
            Counter(row["expected_admission"] for row in self.cases),
            Counter({"admit": distribution["admit"], "reject": distribution["reject"]}),
        )
        self.assertEqual(
            Counter(row["language"] for row in self.cases),
            Counter(distribution["language_counts"]),
        )

    def test_case_and_sentence_ids_are_unique(self):
        case_ids = [row["id"] for row in self.cases]
        sentence_ids = [row["sentence_id"] for row in self.cases]
        self.assertEqual(len(case_ids), len(set(case_ids)))
        self.assertEqual(len(sentence_ids), len(set(sentence_ids)))

    def test_sentence_ids_do_not_overlap_existing_reflection_data(self):
        selected = {row["sentence_id"] for row in self.cases}
        existing = set()
        for path in EXISTING_REFLECTION_DATASETS:
            for row in _load(path)["cases"]:
                provenance = row.get("source_provenance") or {}
                sentence_id = provenance.get("sentence_id")
                if sentence_id is None and row["id"].startswith("ext_"):
                    sentence_id = int(row["id"].rsplit("_", 1)[1])
                if sentence_id is not None:
                    existing.add(sentence_id)
        self.assertTrue(selected.isdisjoint(existing))

    def test_tatoeba_does_not_supply_admission_labels(self):
        provenance = self.config["construction_provenance"]
        self.assertFalse(provenance["reflection_admission_labels_provided_by_tatoeba"])
        self.assertTrue(provenance["constructor_ai_assistance_used"])
        self.assertFalse(provenance["evaluated_qwen_model_inference_used"])
        self.assertFalse(provenance["independent_human_label_validation"])

    def test_proposal_is_narrow_and_constant(self):
        proposal = self.config["proposal_under_review"]
        self.assertEqual(proposal["reflection_type"], "procedural")
        self.assertIn("interlocutor", proposal["claim"])
        self.assertIn("future interaction", proposal["claim"])

    def test_no_model_prompt_or_result_is_preregistered_here(self):
        serialized = json.dumps(self.config, ensure_ascii=False)
        self.assertNotIn("system_prompt", serialized)
        self.assertNotIn("tool_contract", serialized)
        self.assertFalse(
            self.config[
                "evaluated_model_inference_before_construction_closure_authorized"
            ]
        )

    def test_construction_gates_forbid_silent_overlap_or_qwen_calls(self):
        gates = self.config["construction_gates"]
        self.assertEqual(gates["existing_reflection_sentence_id_overlap_max"], 0)
        self.assertEqual(gates["existing_reflection_normalized_text_overlap_max"], 0)
        self.assertEqual(gates["source_text_mismatch_max"], 0)
        self.assertEqual(gates["evaluated_qwen_model_calls_exact"], 0)


if __name__ == "__main__":
    unittest.main()
