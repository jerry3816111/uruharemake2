import json
import unittest

import build_source_preserving_memory_projection_v2_3_result_lock as lock_builder


class SourcePreservingMemoryProjectionV23ResultLockTests(unittest.TestCase):
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

    def test_carrier_gain_and_remaining_failure_are_exact(self):
        effect = self.analysis["carrier_effect"]
        failure = self.analysis["remaining_failure"]
        self.assertEqual(effect["single_record_complete_target_support_count"], 6)
        self.assertEqual(effect["single_record_projected_target_support_count"], 7)
        self.assertEqual(effect["single_record_nonexistent_source_index_errors"], 0)
        self.assertEqual(effect["single_record_valid_rows"], 31)
        self.assertEqual(failure["invalid_row_count"], 1)
        self.assertEqual(failure["classification"], "noncanonical_quoted_empty_placeholder")

    def test_post_hoc_pass_and_runtime_remain_forbidden(self):
        authorization = self.lock["authorization"]
        self.assertFalse(authorization["rerun_same_contract"])
        self.assertFalse(authorization["treat_quoted_empty_as_empty_post_hoc"])
        self.assertFalse(authorization["runtime_change"])
        self.assertFalse(authorization["production_enablement"])
        self.assertFalse(authorization["fresh_holdout"])


if __name__ == "__main__":
    unittest.main()
