import unittest

import analyze_source_preserving_memory_projection_v2_1_development as analyzer


class SourcePreservingMemoryProjectionV21AnalyzerTests(unittest.TestCase):
    def test_rate_and_percentile(self):
        self.assertEqual(analyzer.rate(3, 4), 0.75)
        self.assertEqual(analyzer.percentile([1, 2, 3, 4], 0.5), 2.5)

    def test_case_audit_requires_answer_only_in_target_projection(self):
        case = {
            "official_answer": "home",
            "target": {"source_projection": {"text": "I went home."}},
            "hard_negative": {"source_projection": {"text": "I went outside."}},
        }
        self.assertTrue(analyzer.case_audit(case)["postconstruction_valid"])
        case["hard_negative"]["source_projection"]["text"] = "Maybe home."
        self.assertFalse(analyzer.case_audit(case)["postconstruction_valid"])

    def test_paired_support_changes_are_matched_by_case_id_not_order(self):
        complete = [
            {"case_id": "a", "target_supported": False},
            {"case_id": "b", "target_supported": True},
        ]
        projected = [
            {"case_id": "b", "target_supported": False},
            {"case_id": "a", "target_supported": True},
        ]
        self.assertEqual(analyzer.paired_support_changes(complete, projected), (1, 1))

    def test_expected_row_keys_include_phase_two_only_after_phase_one_passes(self):
        cases = [{"case_id": "a"}, {"case_id": "b"}]
        prereg = {
            "staged_execution": {
                "phase_1_conditions": ["target", "removed"],
                "phase_1_representations": ["complete", "projected"],
                "phase_2_conditions": ["intact"],
                "phase_2_representations": ["complete", "projected"],
            }
        }
        self.assertEqual(len(analyzer.expected_row_keys(cases, prereg, False)), 8)
        self.assertEqual(len(analyzer.expected_row_keys(cases, prereg, True)), 12)

    def test_frozen_cases_reconstruct_exactly_from_official_source(self):
        contract, _prereg = analyzer.load_effective_contract()
        payload = analyzer.load_json(analyzer.ROOT / contract["artifacts"]["cases"]["path"])
        audit = analyzer.audit_cases_against_source(payload)
        self.assertTrue(audit["official_source_hash_match"])
        self.assertTrue(all(case["complete_session_exact"] for case in audit["cases"]))
        self.assertTrue(all(case["source_projection_exact"] for case in audit["cases"]))
        self.assertTrue(all(case["answer_boundary_valid"] for case in audit["cases"]))


if __name__ == "__main__":
    unittest.main()
