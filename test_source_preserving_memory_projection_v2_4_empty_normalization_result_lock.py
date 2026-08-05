import json
import unittest
from pathlib import Path

from run_source_preserving_memory_projection_v2_1_development import file_sha256


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "configs/source_preserving_memory_projection_v2_4_empty_normalization_replay_result_lock.json"


class EmptyNormalizationReplayResultLockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK.read_text(encoding="utf-8"))
        report_path = ROOT / cls.lock["artifacts"]["report_json"]["path"]
        cls.report = json.loads(report_path.read_text(encoding="utf-8"))

    def test_every_locked_artifact_hash_matches(self):
        for name, artifact in self.lock["artifacts"].items():
            self.assertEqual(
                file_sha256(ROOT / artifact["path"]), artifact["sha256"], name
            )

    def test_all_replay_gates_pass_without_model_calls(self):
        self.assertTrue(all(self.report["gates"].values()))
        self.assertEqual(self.report["metrics"]["model_call_count"], 0)
        self.assertEqual(self.report["metrics"]["model_output_sha_unchanged_count"], 32)
        self.assertEqual(self.report["metrics"]["normalized_row_count"], 1)
        self.assertEqual(self.report["metrics"]["semantic_support_change_count"], 0)
        self.assertEqual(self.report["metrics"]["replay_valid_row_count"], 32)

    def test_only_external_holdout_preregistration_is_authorized(self):
        authorization = self.lock["authorization"]
        self.assertTrue(authorization["external_fresh_holdout_preregistration"])
        self.assertFalse(authorization["runtime_change"])
        self.assertFalse(authorization["production_enablement"])
        self.assertFalse(authorization["training_use"])
        self.assertFalse(authorization["fresh_generation_claim"])


if __name__ == "__main__":
    unittest.main()
