import collections
import json
import unittest
from pathlib import Path

import build_semantic_memory_recall_support_v1_holdout as builder
from project_paths import LONGMEMEVAL_S_CLEANED_DATASET_PATH
from run_longmemeval_retrieval_benchmark import (
    canonical_sha256,
    file_sha256,
    load_and_validate_dataset,
)


ROOT = Path(__file__).resolve().parent
CASES = ROOT / "configs/semantic_memory_recall_support_v1_holdout_cases.json"
PREREG = ROOT / "configs/semantic_memory_recall_support_v1_holdout_preregistration.json"
EXPECTED_CASES_SHA256 = "801e11c31aa0039a4fe8c1a1ffc2cbfe9cb936284b5cedb18cea019fb963ccf0"


class SemanticMemoryRecallSupportV1HoldoutCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(CASES.read_text(encoding="utf-8"))

    def test_frozen_file_and_official_source_match(self):
        self.assertEqual(file_sha256(CASES), EXPECTED_CASES_SHA256)
        data, evidence = load_and_validate_dataset(LONGMEMEVAL_S_CLEANED_DATASET_PATH)
        self.assertEqual(self.payload["source"]["sha256"], evidence["sha256"])
        selected = builder.eligible_rows(data)
        self.assertEqual(
            [case["official_question_id"] for case in self.payload["cases"]],
            [row["question_id"] for row in selected],
        )

    def test_builder_and_preregistration_were_frozen(self):
        construction = self.payload["construction"]
        self.assertEqual(construction["builder_sha256"], file_sha256(builder.__file__))
        self.assertEqual(construction["preregistration_sha256"], file_sha256(PREREG))
        self.assertEqual(
            construction["model"]["digest"],
            "845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e",
        )

    def test_case_count_languages_and_ids_match_contract(self):
        cases = self.payload["cases"]
        self.assertEqual(len(cases), 8)
        self.assertEqual(
            collections.Counter(case["language"] for case in cases),
            {"English": 4, "Japanese": 2, "Traditional Chinese": 2},
        )
        self.assertEqual(
            self.payload["case_ids_sha256"],
            canonical_sha256([case["case_id"] for case in cases]),
        )

    def test_records_are_nonempty_distinct_and_uniquely_traced(self):
        trace_ids = []
        for case in self.payload["cases"]:
            self.assertTrue(case["question"].strip())
            target = case["target"]
            negative = case["hard_negative"]
            replacement = case["replacement"]
            for record in (target, negative, replacement):
                self.assertTrue(record["text"].strip())
                trace_ids.append(record["trace_id"])
            self.assertNotEqual(target["text"].strip(), replacement["text"].strip())
            self.assertNotEqual(target["official_session_id"], negative["official_session_id"])
        self.assertEqual(len(trace_ids), len(set(trace_ids)))


if __name__ == "__main__":
    unittest.main()
