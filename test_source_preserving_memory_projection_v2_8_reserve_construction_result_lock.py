import json
import unittest
from pathlib import Path

from build_source_preserving_memory_projection_v2_5_locomo_cases import file_sha256


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "configs/source_preserving_memory_projection_v2_8_reserve_construction_result_lock.json"
CASES = ROOT / "configs/source_preserving_memory_projection_v2_8_reserve_cases.json"
REPORT = ROOT / "reports/source_preserving_memory_projection_v2_8_reserve_construction.json"


class ReserveConstructionResultLockV28Tests(unittest.TestCase):
    def setUp(self):
        self.lock = json.loads(LOCK.read_text(encoding="utf-8"))
        self.cases = json.loads(CASES.read_text(encoding="utf-8"))
        self.report = json.loads(REPORT.read_text(encoding="utf-8"))

    def test_locked_artifacts_match(self):
        for relative, expected in self.lock["artifacts"].items():
            self.assertEqual(file_sha256(ROOT / relative), expected, relative)

    def test_failed_construction_metrics_match_generated_manifest(self):
        metrics = self.cases["construction_metrics"]
        self.assertEqual(self.cases["case_count"], 5)
        self.assertEqual(metrics["isolated_target_answer_retention_count"], 2)
        self.assertEqual(metrics["adjacency_target_answer_retention_count"], 3)
        self.assertEqual(metrics["retention_delta_vs_isolated"], 1)
        failed = [
            name
            for name, passed in self.cases["construction_gates"].items()
            if not passed
        ]
        self.assertEqual(failed, self.lock["failed_gates"])
        self.assertEqual(self.report["failed_gates"], failed)

    def test_model_and_runtime_remain_unauthorized(self):
        self.assertEqual(
            self.lock["decision"],
            "construction_failed_do_not_freeze_model_evaluation_contract",
        )
        authorization = self.lock["authorization"]
        self.assertFalse(authorization["freeze_model_evaluation_contract"])
        self.assertFalse(authorization["run_model_generation"])
        self.assertFalse(authorization["access_final_reserve_case_selection_payload"])
        self.assertFalse(authorization["runtime_change"])
        self.assertFalse(authorization["runtime_shadow"])
        self.assertFalse(authorization["production_enablement"])
        self.assertTrue(authorization["analyze_failure_using_exposed_conversations_only"])

    def test_committed_artifacts_exclude_official_text_and_answers(self):
        self.assertFalse(self.cases["contains_official_text"])
        self.assertFalse(self.cases["contains_official_answers"])
        self.assertFalse(self.report["integrity"]["contains_official_text"])
        self.assertFalse(self.report["integrity"]["contains_official_answers"])
        for case in self.cases["cases"]:
            self.assertNotIn("question", case)
            self.assertNotIn("answer", case)
            self.assertNotIn("text", case)


if __name__ == "__main__":
    unittest.main()
