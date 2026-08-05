import json
import unittest

import build_source_preserving_memory_projection_v2_1_development as builder
import build_source_preserving_memory_projection_v2_development as v2
from audit_semantic_memory_recall_support_v1_evidence_contract import file_sha256, load_dataset
from project_paths import LONGMEMEVAL_S_CLEANED_DATASET_PATH


EXPECTED_CASES_SHA256 = "7c05f63eeaf8047c5e76114babef7ff4ae3a84f20819bf57142318ed4a280358"
EXPECTED_QUESTION_IDS = [
    "6ade9755",
    "577d4d32",
    "58bf7951",
    "af8d2e46",
    "f4f1d8a4",
    "1e043500",
    "76d63226",
    "60d45044",
]


class SourcePreservingMemoryProjectionV21CaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(builder.OUTPUT.read_text(encoding="utf-8"))
        data, cls.source_evidence = load_dataset(LONGMEMEVAL_S_CLEANED_DATASET_PATH)
        cls.rows = {row["question_id"]: row for row in data}

    def test_frozen_hash_count_ids_and_boundaries(self):
        self.assertEqual(file_sha256(builder.OUTPUT), EXPECTED_CASES_SHA256)
        self.assertEqual(self.payload["case_count"], 8)
        self.assertEqual(
            [case["official_question_id"] for case in self.payload["cases"]],
            EXPECTED_QUESTION_IDS,
        )
        self.assertEqual(self.payload["selection"]["eligible_count"], 14)
        self.assertEqual(self.payload["construction"]["model_calls"], 0)
        self.assertFalse(self.payload["authorization"]["run_model_evaluation"])
        self.assertFalse(self.payload["authorization"]["runtime_change"])

    def test_builder_preregistration_and_source_hashes_match(self):
        construction = self.payload["construction"]
        self.assertEqual(construction["builder_sha256"], file_sha256(builder.__file__))
        self.assertEqual(construction["inherited_builder_sha256"], file_sha256(v2.__file__))
        self.assertEqual(
            construction["revision_preregistration_sha256"],
            file_sha256(builder.REVISION_PREREG),
        )
        self.assertEqual(self.payload["source"]["sha256"], self.source_evidence["sha256"])

    def test_every_record_reconstructs_from_official_source(self):
        for case in self.payload["cases"]:
            row = self.rows[case["official_question_id"]]
            self.assertEqual(case["question"], row["question"])
            self.assertEqual(case["official_answer"], row["answer"])
            for kind in ("target", "hard_negative"):
                record = case[kind]
                source = v2.source_session(row, record["official_session_id"])
                complete = v2.complete_representation(source["session"], source["timestamp"])
                projection = v2.projection_representation(
                    source["session"], source["timestamp"], row["question"]
                )
                self.assertEqual(record["complete_session"], complete)
                self.assertEqual(record["source_projection"], projection)
            self.assertIn(case["target"]["official_session_id"], row["answer_session_ids"])
            self.assertNotIn(
                case["hard_negative"]["official_session_id"], row["answer_session_ids"]
            )

    def test_answer_is_preserved_only_in_target_projection(self):
        for case in self.payload["cases"]:
            answer = str(case["official_answer"]).casefold()
            self.assertIn(answer, case["target"]["source_projection"]["text"].casefold())
            self.assertNotIn(
                answer,
                case["hard_negative"]["source_projection"]["text"].casefold(),
            )
        audit = self.payload["postconstruction_audit"]
        self.assertEqual(audit["projected_target_exact_answer_count"], 8)
        self.assertEqual(audit["projected_hard_negative_exact_answer_count"], 0)

    def test_all_visible_complete_inputs_obey_revised_limits(self):
        limits = self.payload["selection"]["source_size_rules"]
        for case in self.payload["cases"]:
            target_length = len(case["target"]["complete_session"]["text"])
            negative_length = len(case["hard_negative"]["complete_session"]["text"])
            self.assertLessEqual(target_length, limits["maximum_target_characters"])
            self.assertLessEqual(negative_length, limits["maximum_hard_negative_characters"])
            self.assertLessEqual(
                target_length + negative_length,
                limits["maximum_combined_visible_characters"],
            )


if __name__ == "__main__":
    unittest.main()
