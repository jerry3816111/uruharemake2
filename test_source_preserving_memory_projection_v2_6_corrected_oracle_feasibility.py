import json
import unittest
from pathlib import Path

import analyze_source_preserving_memory_projection_v2_6_corrected_oracle_feasibility as analyzer
import build_source_preserving_memory_projection_v2_6_corrected_oracle_cases as v26
from test_build_source_preserving_memory_projection_v2_5_locomo_cases import sample


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "configs/source_preserving_memory_projection_v2_6_corrected_oracle_feasibility_lock.json"


class CorrectedOracleFeasibilityV26Tests(unittest.TestCase):
    def test_synthetic_feasible_population(self):
        prereg = v26.load_preregistration()
        data = [sample(f"sample-{index}", f"d{index}") for index in range(10)]
        prereg["controlled_variables"]["exposed_sample_ids"] = [
            f"sample-{index}" for index in range(4)
        ]
        report = analyzer.summarize(data, prereg)
        self.assertEqual(report["decision"], "construction_feasible_build_once")
        self.assertEqual(report["metrics"]["eligible_question_count"], 12)

    def test_formal_failure_is_locked_without_model_calls(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        report = json.loads(
            (ROOT / "reports/source_preserving_memory_projection_v2_6_corrected_oracle_feasibility.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            report["decision"], "construction_infeasible_do_not_build_cases"
        )
        self.assertEqual(report["metrics"]["eligible_question_count"], 10)
        self.assertEqual(report["metrics"]["required_question_count"], 12)
        self.assertFalse(report["metrics"]["case_manifest_written"])
        self.assertEqual(lock["model_calls"], 0)
        self.assertTrue(
            lock["authorization"][
                "new_preregistration_changing_only_development_count_and_allocation"
            ]
        )
        self.assertFalse(lock["authorization"]["change_projection_algorithm"])
        self.assertFalse(lock["authorization"]["use_reserve_conversations"])

    def test_locked_artifact_hashes_match(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        for relative, expected in lock["artifacts"].items():
            self.assertEqual(
                __import__(
                    "build_source_preserving_memory_projection_v2_5_locomo_cases"
                ).file_sha256(ROOT / relative),
                expected,
                relative,
            )


if __name__ == "__main__":
    unittest.main()
