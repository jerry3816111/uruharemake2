import json
import unittest
from pathlib import Path

from build_rightbrain_runtime_rejection_curriculum_v13 import (
    DEFAULT_SOURCE_REPORTS,
    build_curriculum,
)


class RightBrainRuntimeRejectionCurriculumV13Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        reports = [
            json.loads(Path(path).read_text(encoding="utf-8"))
            | {"_source_path": str(path)}
            for path in DEFAULT_SOURCE_REPORTS
        ]
        cls.rows, cls.summary = build_curriculum(reports)

    def test_builds_from_promoted_runtime_reports(self):
        self.assertEqual(
            self.summary["source_adapter_refs"],
            ["uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1"],
        )
        self.assertEqual(self.summary["source_seeds"], [20260708, 20260709])
        self.assertEqual(self.summary["source_candidate_count_per_case"], [3])
        self.assertEqual(self.summary["case_count"], 11)
        self.assertEqual(self.summary["case_count_with_training_rows"], 10)
        self.assertGreaterEqual(self.summary["curriculum_row_count"], 35)
        self.assertEqual(self.summary["skipped_counts"]["no_model_generation"], 1)

    def test_failure_reasons_cover_current_runtime_weaknesses(self):
        reasons = self.summary["failure_reason_counts"]
        self.assertIn("unexpected_ascii_leak", reasons)
        self.assertIn("nonstandard_cjk_surface", reasons)
        self.assertIn("semantic_slots_missing:0/1", reasons)
        self.assertGreater(reasons["unexpected_ascii_leak"], reasons["nonstandard_cjk_surface"])

    def test_targets_are_valid_contract_outputs_not_raw_rejections(self):
        raw_rejections = {
            example["raw_candidate"]
            for row in self.rows
            for example in row["rejected_candidate_examples"]
            if example.get("raw_candidate")
        }
        self.assertTrue(raw_rejections)
        for row in self.rows:
            assistant = row["messages"][-1]["content"]
            self.assertNotIn(assistant, raw_rejections)
            self.assertEqual(assistant.strip(), assistant)
            payload = json.loads(row["messages"][1]["content"])
            self.assertEqual(payload["contract_version"], "plan_surface_contract_v1")
            for group in payload["required_marker_groups"]:
                self.assertTrue(any(str(marker) and str(marker) in assistant for marker in group))
            self.assertNotIn("stomach", assistant)
            self.assertNotIn("coffee", assistant)

    def test_boundary_case_is_not_trained_when_generation_is_disabled(self):
        case_ids = {row["source_case_id"] for row in self.rows}
        self.assertNotIn("boundary_dirty_language", case_ids)
        self.assertIn("support_tired_no_closing_template", case_ids)
        self.assertIn("daily_state_answer", case_ids)


if __name__ == "__main__":
    unittest.main()
