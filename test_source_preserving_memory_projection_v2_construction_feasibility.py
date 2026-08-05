import json
import unittest

import build_source_preserving_memory_projection_v2_development as builder


class SourcePreservingMemoryProjectionV2FeasibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(builder.FEASIBILITY_REPORT_JSON.read_text(encoding="utf-8"))
        cls.lock = json.loads(builder.FEASIBILITY_LOCK.read_text(encoding="utf-8"))

    def test_locked_result_is_infeasible_without_model_calls(self):
        self.assertEqual(self.report["status"], "construction_infeasible_locked")
        self.assertEqual(self.report["required_case_count"], 8)
        self.assertEqual(self.report["eligible_case_count"], 1)
        self.assertEqual(
            self.report["sequential_exclusion_counts"]["target_over_character_limit"],
            39,
        )
        self.assertEqual(self.report["model_calls"], 0)
        self.assertFalse(self.report["case_file_written"])

    def test_lock_hashes_all_construction_evidence(self):
        for relative_path, expected_hash in self.lock["artifacts"].items():
            self.assertEqual(
                builder.file_sha256(builder.ROOT / relative_path),
                expected_hash,
                relative_path,
            )

    def test_failure_does_not_authorize_runtime_or_model_evaluation(self):
        authorization = self.lock["authorization"]
        self.assertFalse(authorization["runtime_change"])
        self.assertFalse(authorization["production_enablement"])
        self.assertFalse(authorization["model_evaluation"])
        self.assertTrue(authorization["new_preregistration_changing_only_context_limits"])


if __name__ == "__main__":
    unittest.main()
