import unittest

import replay_source_preserving_memory_projection_v2_4_empty_normalization as replay


class EmptyNormalizationReplayTests(unittest.TestCase):
    def test_frozen_replay_changes_one_boundary_value_and_no_semantics(self):
        _contract, prereg, conditions, cases_payload = replay.load_frozen_configuration()
        raw_rows = replay.load_jsonl(replay.ROOT / prereg["frozen_source"]["raw_path"])
        rows = replay.replay_all(raw_rows, cases_payload, conditions)
        self.assertEqual(len(rows), 32)
        self.assertEqual(sum(row["normalization"]["applied"] for row in rows), 1)
        self.assertEqual(sum(row["semantic_support_changed"] for row in rows), 0)
        self.assertEqual(sum(row["previously_valid_regressed"] for row in rows), 0)
        self.assertEqual(sum(row["model_call_count"] for row in rows), 0)
        self.assertTrue(
            all(
                row["model_output_sha256_before"] == row["model_output_sha256_after"]
                for row in rows
            )
        )


if __name__ == "__main__":
    unittest.main()
