import json
import unittest
from pathlib import Path

from build_source_preserving_memory_projection_v2_5_locomo_cases import file_sha256


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "configs/source_preserving_memory_projection_v2_7_adjacency_result_lock.json"
REPORT = ROOT / "reports/source_preserving_memory_projection_v2_7_adjacency.json"


class AdjacencyProjectionResultLockV27Tests(unittest.TestCase):
    def setUp(self):
        self.lock = json.loads(LOCK.read_text(encoding="utf-8"))
        self.report = json.loads(REPORT.read_text(encoding="utf-8"))

    def test_every_locked_artifact_hash_matches(self):
        for relative, expected in self.lock["artifacts"].items():
            self.assertEqual(file_sha256(ROOT / relative), expected, relative)

    def test_all_preregistered_gates_pass(self):
        self.assertTrue(all(self.report["gates"].values()))
        self.assertEqual(
            self.report["decision"],
            "development_pass_authorize_reserve_holdout_preregistration_only",
        )

    def test_retention_and_cost_metrics_are_frozen(self):
        metrics = self.report["metrics"]
        self.assertEqual(metrics["control_target_answer_retention_count"], 4)
        self.assertEqual(metrics["adjacency_target_answer_retention_count"], 9)
        self.assertEqual(metrics["retention_delta_vs_control"], 5)
        self.assertEqual(metrics["adjacency_target_answer_omission_count"], 1)
        self.assertLessEqual(metrics["mean_target_projection_character_ratio"], 0.5)
        self.assertLessEqual(metrics["mean_all_record_projection_character_ratio"], 0.5)
        self.assertEqual(metrics["model_calls"], 0)
        self.assertEqual(metrics["reserve_sample_access_count"], 0)

    def test_authorization_stops_at_new_preregistration(self):
        authorization = self.lock["authorization"]
        self.assertTrue(authorization["preregister_reserve_fresh_holdout"])
        self.assertFalse(authorization["model_generation"])
        self.assertFalse(authorization["use_reserve_conversations_now"])
        self.assertFalse(authorization["runtime_change"])
        self.assertFalse(authorization["runtime_shadow"])
        self.assertFalse(authorization["production_enablement"])


if __name__ == "__main__":
    unittest.main()
