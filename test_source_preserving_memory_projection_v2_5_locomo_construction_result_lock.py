import json
import unittest
from pathlib import Path

from build_source_preserving_memory_projection_v2_5_locomo_cases import file_sha256


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "configs/source_preserving_memory_projection_v2_5_locomo_construction_result_lock.json"


class LocomoV25ConstructionResultLockTests(unittest.TestCase):
    def setUp(self):
        self.lock = json.loads(LOCK.read_text(encoding="utf-8"))
        report_path = ROOT / "reports/source_preserving_memory_projection_v2_5_locomo_construction.json"
        self.report = json.loads(report_path.read_text(encoding="utf-8"))

    def test_every_locked_artifact_hash_matches(self):
        for relative, expected in self.lock["artifacts"].items():
            self.assertEqual(file_sha256(ROOT / relative), expected, relative)

    def test_invalid_oracle_stops_model_generation(self):
        self.assertEqual(
            self.lock["decision"], "construction_invalid_oracle_do_not_run_model"
        )
        self.assertEqual(self.lock["model_calls"], 0)
        self.assertFalse(self.lock["authorization"]["model_generation"])
        self.assertFalse(self.report["integrity"]["corrected_source_turn_oracle_valid"])
        self.assertFalse(self.report["gate"]["evaluable"])

    def test_observed_failure_counts_are_frozen(self):
        metrics = self.report["metrics"]
        self.assertEqual(metrics["source_turn_valid_case_count"], 9)
        self.assertEqual(metrics["source_turn_invalid_case_count"], 3)
        self.assertEqual(
            metrics["source_turn_projection_answer_retention_count"], 4
        )
        self.assertEqual(metrics["manifest_serialized_projection_answer_retention_count"], 7)
        self.assertEqual(metrics["planned_model_calls"], 48)
        self.assertEqual(metrics["executed_model_calls"], 0)

    def test_authorization_remains_narrow(self):
        authorization = self.lock["authorization"]
        self.assertTrue(
            authorization["new_preregistration_using_only_six_reserve_conversations"]
        )
        self.assertTrue(authorization["correct_source_membership_oracle"])
        self.assertTrue(authorization["change_projection_algorithm"])
        self.assertFalse(authorization["runtime_change"])
        self.assertFalse(authorization["runtime_shadow"])
        self.assertFalse(authorization["production_enablement"])


if __name__ == "__main__":
    unittest.main()
