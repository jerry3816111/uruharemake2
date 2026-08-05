import json
import unittest
from pathlib import Path

from build_source_preserving_memory_projection_v2_5_locomo_cases import file_sha256


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "configs/source_preserving_memory_projection_v2_6_1_population_result_lock.json"
REPORT = ROOT / "reports/source_preserving_memory_projection_v2_6_1_population_baseline.json"


class ExposedPopulationResultLockV261Tests(unittest.TestCase):
    def setUp(self):
        self.lock = json.loads(LOCK.read_text(encoding="utf-8"))
        self.report = json.loads(REPORT.read_text(encoding="utf-8"))

    def test_locked_artifacts_match(self):
        for relative, expected in self.lock["artifacts"].items():
            self.assertEqual(file_sha256(ROOT / relative), expected, relative)

    def test_baseline_metrics_are_frozen(self):
        metrics = self.report["metrics"]
        self.assertEqual(metrics["top3_isolated_target_answer_retention_count"], 4)
        self.assertEqual(metrics["target_answer_omission_count"], 6)
        self.assertEqual(metrics["construction_model_calls"], 0)
        self.assertEqual(self.report["integrity"]["case_count"], 10)
        self.assertEqual(self.report["integrity"]["reserve_sample_access_count"], 0)

    def test_authorization_is_adjacency_preregistration_only(self):
        authorization = self.lock["authorization"]
        self.assertTrue(authorization["preregister_adjacency_projection_on_same_cases"])
        self.assertFalse(authorization["change_any_other_variable"])
        self.assertFalse(authorization["model_generation"])
        self.assertFalse(authorization["use_reserve_conversations"])
        self.assertFalse(authorization["runtime_change"])
        self.assertFalse(authorization["runtime_shadow"])
        self.assertFalse(authorization["production_enablement"])


if __name__ == "__main__":
    unittest.main()
