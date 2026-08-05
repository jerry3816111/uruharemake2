import json
import unittest

import build_source_preserving_memory_projection_v2_2_result_lock as lock_builder


class SourcePreservingMemoryProjectionV22ResultLockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(lock_builder.RESULT_LOCK.read_text(encoding="utf-8"))
        cls.analysis = json.loads(lock_builder.FAILURE_JSON.read_text(encoding="utf-8"))

    def test_all_locked_hashes_match(self):
        for name, artifact in self.lock["artifacts"].items():
            self.assertEqual(
                lock_builder.sha256(lock_builder.ROOT / artifact["path"]),
                artifact["sha256"],
                name,
            )

    def test_capacity_helped_but_contract_still_failed(self):
        result = self.analysis["hypothesis_result"]
        blocking = self.analysis["blocking_failure"]
        self.assertEqual(result["frozen_4b_projected_target_support_count"], 5)
        self.assertEqual(result["intervention_9b_projected_target_support_count"], 7)
        self.assertEqual(result["support_gain_count"], 2)
        self.assertEqual(result["projected_false_support_count"], 0)
        self.assertEqual(blocking["invalid_row_count"], 6)
        self.assertTrue(blocking["invalid_rows_all_complete_session"])

    def test_runtime_and_same_contract_rerun_remain_forbidden(self):
        authorization = self.lock["authorization"]
        self.assertFalse(authorization["rerun_same_contract"])
        self.assertFalse(authorization["change_threshold_post_hoc"])
        self.assertFalse(authorization["runtime_change"])
        self.assertFalse(authorization["production_enablement"])
        self.assertFalse(authorization["fresh_holdout"])


if __name__ == "__main__":
    unittest.main()
