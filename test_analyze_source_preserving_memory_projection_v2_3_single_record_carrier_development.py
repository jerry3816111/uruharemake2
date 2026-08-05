import unittest

import analyze_source_preserving_memory_projection_v2_3_single_record_carrier_development as analyzer


class SourcePreservingMemoryProjectionV23AnalyzerTests(unittest.TestCase):
    def test_expected_keys_cover_exact_32_row_matrix(self):
        cases = [{"case_id": f"c{i}"} for i in range(8)]
        prereg = {
            "controlled_variables": {
                "conditions": ["target", "removed"],
                "representations": ["complete", "projected"],
            }
        }
        keys = analyzer.expected_keys(cases, prereg)
        self.assertEqual(len(keys), 32)
        self.assertEqual(len(set(keys)), 32)


if __name__ == "__main__":
    unittest.main()
