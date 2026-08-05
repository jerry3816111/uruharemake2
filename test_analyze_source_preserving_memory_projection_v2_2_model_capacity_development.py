import unittest

import analyze_source_preserving_memory_projection_v2_2_model_capacity_development as analyzer


class SourcePreservingMemoryProjectionV22CapacityAnalyzerTests(unittest.TestCase):
    def test_expected_keys_cover_exact_phase_one_matrix(self):
        cases = [{"case_id": "a"}, {"case_id": "b"}]
        prereg = {
            "controlled_variables": {
                "conditions": ["target", "removed"],
                "representations": ["complete", "projected"],
            }
        }
        keys = analyzer.expected_keys(cases, prereg)
        self.assertEqual(len(keys), 8)
        self.assertEqual(len(set(keys)), 8)

    def test_row_key_is_order_independent_identity(self):
        row = {"case_id": "a", "condition": "target", "representation": "projected"}
        self.assertEqual(analyzer.row_key(row), ("a", "target", "projected"))


if __name__ == "__main__":
    unittest.main()
