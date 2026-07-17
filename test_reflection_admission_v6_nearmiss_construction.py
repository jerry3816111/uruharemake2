#!/usr/bin/env python3
"""Validate V6 source fetching, dataset construction, and frozen audit."""

from __future__ import annotations

import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path

from audit_reflection_admission_v6_nearmiss_dataset import audit
from build_reflection_admission_v6_nearmiss_dataset import build_dataset


ROOT = Path(__file__).resolve().parent
PREREG_PATH = (
    ROOT
    / "configs"
    / "reflection_admission_v6_nearmiss_construction_preregistration.json"
)
SOURCE_PATH = (
    ROOT / "datasets" / "sources" / "tatoeba_reflection_admission_v6_selected.json"
)
DATASET_PATH = ROOT / "datasets" / "reflection_admission_v6_nearmiss_development.json"
AUDIT_PATH = ROOT / "reports" / "reflection_admission_v6_nearmiss_audit.json"
CLOSURE_PATH = (
    ROOT / "configs" / "reflection_admission_v6_nearmiss_construction_closure.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReflectionAdmissionNearMissConstructionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prereg = _load(PREREG_PATH)
        cls.source = _load(SOURCE_PATH)
        cls.dataset = _load(DATASET_PATH)
        cls.saved_audit = _load(AUDIT_PATH)
        cls.closure = _load(CLOSURE_PATH)

    def test_source_exactly_matches_preregistered_ids_and_languages(self):
        selected = {
            row["sentence_id"]: row["language"]
            for row in self.prereg["selected_cases"]
        }
        observed = {
            row["sentence_id"]: row["language"] for row in self.source["items"]
        }
        self.assertEqual(observed, selected)
        self.assertTrue(
            all(not row["is_unapproved"] and row["license"] for row in self.source["items"])
        )
        self.assertFalse(self.source["evaluated_qwen_model_inference_used"])

    def test_builder_exactly_reproduces_saved_dataset(self):
        rebuilt = build_dataset(self.prereg, self.source)
        rebuilt.pop("created_at")
        saved = dict(self.dataset)
        saved.pop("created_at")
        self.assertEqual(rebuilt, saved)
        self.assertEqual(self.dataset["case_count"], 32)
        self.assertEqual(
            Counter(row["expected_admission"] for row in self.dataset["cases"]),
            Counter({"admit": 16, "reject": 16}),
        )

    def test_dataset_keeps_source_and_label_provenance_separate(self):
        self.assertFalse(
            self.dataset["reflection_admission_labels_provided_by_source"]
        )
        self.assertTrue(self.dataset["constructor_ai_assistance_used"])
        self.assertFalse(self.dataset["independent_human_label_validation"])
        self.assertFalse(self.dataset["evaluated_qwen_model_inference_used"])

    def test_independent_audit_exactly_reproduces_saved_report(self):
        regenerated = audit()
        regenerated.pop("generated_at")
        saved = dict(self.saved_audit)
        saved.pop("generated_at")
        self.assertEqual(regenerated, saved)
        self.assertTrue(saved["all_gates_pass"])

    def test_no_existing_reflection_overlap_or_qwen_calls(self):
        self.assertEqual(
            self.saved_audit["existing_reflection_sentence_id_overlap"], []
        )
        self.assertEqual(
            self.saved_audit[
                "existing_reflection_normalized_text_overlap_case_ids"
            ],
            [],
        )
        self.assertEqual(self.saved_audit["evaluated_qwen_model_calls"], 0)

    def test_closure_hashes_all_construction_artifacts(self):
        for name, path in (
            ("construction_preregistration", PREREG_PATH),
            ("source_snapshot", SOURCE_PATH),
            ("dataset", DATASET_PATH),
            ("audit_json", AUDIT_PATH),
            (
                "audit_md",
                ROOT / "reports" / "reflection_admission_v6_nearmiss_audit.md",
            ),
            (
                "fetcher",
                ROOT / "fetch_tatoeba_reflection_admission_v6_source.py",
            ),
            ("builder", ROOT / "build_reflection_admission_v6_nearmiss_dataset.py"),
            ("auditor", ROOT / "audit_reflection_admission_v6_nearmiss_dataset.py"),
        ):
            self.assertEqual(
                _sha256(path),
                self.closure["frozen_artifacts"][f"{name}_sha256"],
            )


if __name__ == "__main__":
    unittest.main()
