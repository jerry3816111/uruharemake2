import copy
import unittest

import analyze_source_preserving_memory_projection_v2_5_locomo_construction as analyzer
import build_source_preserving_memory_projection_v2_5_locomo_cases as builder
from test_build_source_preserving_memory_projection_v2_5_locomo_cases import sample


class LocomoV25ConstructionAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.prereg = builder.load_preregistration()
        self.data = [sample(f"sample-{index}", f"d{index}") for index in range(10)]

    def test_synthetic_manifest_reaches_retention_gate(self):
        manifest = builder.build_manifest(self.data, self.prereg)
        report = analyzer.summarize(self.data, self.prereg, manifest)
        self.assertEqual(
            report["metrics"]["source_turn_projection_answer_retention_count"], 12
        )
        self.assertTrue(report["gate"]["passed"])
        self.assertEqual(
            report["decision"], "construction_pass_freeze_model_evaluation_contract"
        )

    def test_omitted_answer_fails_before_model_calls(self):
        modified = copy.deepcopy(self.data)
        manifest = builder.build_manifest(modified, self.prereg)
        for case in manifest["cases"][:3]:
            case["target"]["projection_source_turn_indices"] = [1, 2]
            case["target"]["contains_answer_projection"] = False
        report = analyzer.summarize(modified, self.prereg, manifest)
        self.assertEqual(
            report["metrics"]["source_turn_projection_answer_retention_count"], 9
        )
        self.assertFalse(report["gate"]["passed"])
        self.assertEqual(report["metrics"]["executed_model_calls"], 0)
        self.assertFalse(report["authorization"]["model_generation"])

    def test_metadata_only_answer_invalidates_construction_oracle(self):
        modified = copy.deepcopy(self.data)
        for row in modified:
            for qa in row["qa"]:
                qa["answer"] = "2024-01-01 10:00"
        manifest = builder.build_manifest(modified, self.prereg)
        report = analyzer.summarize(modified, self.prereg, manifest)
        self.assertEqual(report["metrics"]["source_turn_valid_case_count"], 0)
        self.assertFalse(report["integrity"]["corrected_source_turn_oracle_valid"])
        self.assertFalse(report["gate"]["evaluable"])
        self.assertEqual(report["decision"], "construction_invalid_oracle_do_not_run_model")


if __name__ == "__main__":
    unittest.main()
