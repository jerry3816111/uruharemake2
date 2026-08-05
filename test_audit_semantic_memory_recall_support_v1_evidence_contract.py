import json
import inspect
import unittest

import audit_semantic_memory_recall_support_v1_evidence_contract as audit


class SemanticMemoryRecallEvidenceContractAuditTests(unittest.TestCase):
    def test_witness_groups_require_one_match_per_group(self):
        result = audit.witness_groups_present(
            "I made a lemon blueberry cake.",
            [["lemon"], ["blueberry"], ["cake"]],
        )
        self.assertTrue(result["passed"])
        self.assertFalse(
            audit.witness_groups_present("I made a lemon tart.", [["lemon"], ["cake"]])[
                "passed"
            ]
        )

    def test_timestamp_signature_is_locale_independent(self):
        self.assertEqual(
            audit.timestamp_signature("時間：2023年5月22日（月）凌晨5点54分"),
            [2023, 5, 22, 5, 54],
        )
        self.assertEqual(
            audit.timestamp_signature("Time: 2023/05/22 (Mon) 05:54"),
            [2023, 5, 22, 5, 54],
        )

    def test_language_contract_detects_known_construction_failures(self):
        self.assertTrue(audit.language_contract("Japanese", "友人サラと話しました")["passed"])
        self.assertFalse(audit.language_contract("Japanese", "I spoke with Sarah")["passed"])
        self.assertFalse(
            audit.language_contract("Traditional Chinese", "这个周末举办晚宴")["passed"]
        )
        self.assertTrue(
            audit.language_contract("Traditional Chinese", "這個週末舉辦晚宴")["passed"]
        )

    def test_locked_report_records_invalid_artifact(self):
        report = json.loads(audit.REPORT_JSON.read_text(encoding="utf-8"))
        observed = report["observed"]
        self.assertEqual(report["decision"], "invalidate_v1_cases_for_architecture_or_capacity_claims")
        self.assertEqual(observed["case_count"], 8)
        self.assertEqual(observed["strict_contract_valid_count"], 0)
        self.assertEqual(observed["check_pass_counts"]["target_answer_bearing"], 7)
        self.assertEqual(observed["check_pass_counts"]["replacement_answer_bearing"], 4)
        self.assertEqual(
            observed["check_pass_counts"]["all_fields_match_requested_language"], 4
        )
        self.assertIn("official-07-8550ddae", observed["target_source_contradiction_case_ids"])
        self.assertFalse(report["authorization"]["runtime_change"])
        self.assertFalse(report["authorization"]["model_selection"])

    def test_result_lock_hashes_every_audited_artifact(self):
        lock = json.loads(audit.RESULT_LOCK.read_text(encoding="utf-8"))
        for relative_path, expected_hash in lock["artifacts"].items():
            self.assertEqual(audit.file_sha256(audit.ROOT / relative_path), expected_hash)
        self.assertFalse(lock["authorization"]["reuse_v1_cases_as_holdout"])

    def test_auditor_does_not_import_runtime_or_vector_database(self):
        source = inspect.getsource(audit)
        self.assertNotIn("import chromadb", source)
        self.assertNotIn("import uruha_brain", source)
        self.assertNotIn("import build_semantic_memory_recall_support", source)


if __name__ == "__main__":
    unittest.main()
