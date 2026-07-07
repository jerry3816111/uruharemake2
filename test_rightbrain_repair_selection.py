import json
import unittest
from pathlib import Path

from build_rightbrain_repair_curriculum_v1 import _target_errors
from build_rightbrain_repair_selection_v1 import DEFAULT_MAX_ROWS, DEFAULT_SEED, build_selection_dataset
from eval_rightbrain_repair_selection_v1 import build_report, select_candidate
from project_paths import RIGHTBRAIN_REPAIR_CURRICULUM_V1_DATASET_PATH


class RightBrainRepairSelectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source_rows = json.loads(Path(RIGHTBRAIN_REPAIR_CURRICULUM_V1_DATASET_PATH).read_text(encoding="utf-8"))
        cls.rows, cls.summary = build_selection_dataset(source_rows)
        cls.report = build_report(cls.rows)

    def test_builds_candidate_selection_rows(self):
        self.assertEqual(len(self.rows), DEFAULT_MAX_ROWS)
        self.assertEqual(self.summary["selection_row_count"], DEFAULT_MAX_ROWS)
        self.assertEqual(self.summary["gold_candidate_count"], DEFAULT_MAX_ROWS)
        self.assertGreaterEqual(self.summary["invalid_candidate_count"], DEFAULT_MAX_ROWS * 5)
        for source in (
            "gold_valid_reply",
            "missing_required_marker",
            "ascii_leak",
            "chinese_leak",
            "polite_tone_drift",
            "instruction_or_plan_leak",
        ):
            self.assertIn(source, self.summary["candidate_source_counts"])

    def test_each_row_has_one_valid_gold_and_invalid_negatives(self):
        for row in self.rows:
            payload = row["contract_payload"]
            gold_candidates = [candidate for candidate in row["candidates"] if candidate["candidate_id"] == row["gold_candidate_id"]]
            self.assertEqual(len(gold_candidates), 1)
            self.assertEqual(_target_errors(gold_candidates[0]["text"], payload), [])
            negative_candidates = [
                candidate
                for candidate in row["candidates"]
                if candidate["candidate_id"] != row["gold_candidate_id"]
            ]
            self.assertGreaterEqual(len(negative_candidates), 5)
            for candidate in negative_candidates:
                self.assertTrue(
                    _target_errors(candidate["text"], payload),
                    msg=f"{row['id']} {candidate['candidate_id']} should be invalid",
                )

    def test_selector_uses_contract_errors_not_gold_position(self):
        for row in self.rows:
            selected = select_candidate(row)
            self.assertEqual(selected["candidate_id"], row["gold_candidate_id"])
            self.assertEqual(_target_errors(selected["text"], row["contract_payload"]), [])

    def test_eval_report_has_perfect_synthetic_oracle_gate(self):
        summary = self.report["summary"]
        self.assertEqual(summary["invalid_candidate_error_detection_rate"], 1.0)
        self.assertEqual(summary["gold_selection_rate"], 1.0)
        self.assertEqual(summary["valid_selection_rate"], 1.0)
        self.assertEqual(summary["invalid_selection_rate"], 0.0)

    def test_generation_is_deterministic(self):
        source_rows = json.loads(Path(RIGHTBRAIN_REPAIR_CURRICULUM_V1_DATASET_PATH).read_text(encoding="utf-8"))
        second_rows, second_summary = build_selection_dataset(source_rows, seed=DEFAULT_SEED)
        self.assertEqual(self.rows, second_rows)
        for key in (
            "candidate_source_counts",
            "detected_error_counts",
            "category_counts",
            "skipped_counts",
        ):
            self.assertEqual(self.summary[key], second_summary[key])


if __name__ == "__main__":
    unittest.main()
