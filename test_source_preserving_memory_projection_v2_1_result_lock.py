import json
import unittest
from pathlib import Path

import build_source_preserving_memory_projection_v2_1_result_lock as lock_builder


class SourcePreservingMemoryProjectionV21ResultLockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(lock_builder.RESULT_LOCK.read_text(encoding="utf-8"))
        cls.analysis = json.loads(lock_builder.FAILURE_JSON.read_text(encoding="utf-8"))

    def test_every_locked_artifact_hash_matches(self):
        for name, artifact in self.lock["artifacts"].items():
            self.assertEqual(
                lock_builder.sha256(lock_builder.ROOT / artifact["path"]),
                artifact["sha256"],
                name,
            )

    def test_failure_is_locked_without_runtime_authorization(self):
        self.assertEqual(self.lock["status"], "locked_failed_phase_1")
        self.assertEqual(self.lock["executed_model_calls"], 32)
        self.assertFalse(self.lock["phase_2_executed"])
        self.assertFalse(self.lock["authorization"]["rerun_same_contract"])
        self.assertFalse(self.lock["authorization"]["runtime_change"])
        self.assertFalse(self.lock["authorization"]["production_enablement"])

    def test_failure_localization_matches_frozen_observations(self):
        primary = self.analysis["primary_failure"]
        secondary = self.analysis["secondary_failure"]
        positive = self.analysis["positive_observation"]
        self.assertEqual(primary["projected_target_support_count"], 5)
        self.assertEqual(primary["miss_count"], 3)
        self.assertTrue(all(row["answer_preserved_in_projection"] for row in primary["misses"]))
        self.assertEqual(secondary["invalid_row_count"], 4)
        self.assertEqual(positive["paired_gain_count"], 5)
        self.assertEqual(positive["paired_loss_count"], 0)


if __name__ == "__main__":
    unittest.main()
