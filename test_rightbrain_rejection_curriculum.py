import json
import unittest
from pathlib import Path

from build_rightbrain_rejection_curriculum_v1 import build_curriculum
from project_paths import RIGHTBRAIN_MODEL_SURFACE_HOLDOUT_REPORT_JSON_PATH


class RightBrainRejectionCurriculumTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        report = json.loads(Path(RIGHTBRAIN_MODEL_SURFACE_HOLDOUT_REPORT_JSON_PATH).read_text(encoding="utf-8"))
        cls.rows, cls.summary = build_curriculum(report)

    def test_builds_rows_from_rejected_candidates_only(self):
        self.assertEqual(self.summary["curriculum_row_count"], 36)
        self.assertEqual(len(self.rows), 36)
        self.assertEqual(self.summary["skipped_counts"]["no_rejection"], 5)
        self.assertEqual(self.summary["variant_cases"], 6)
        self.assertIn("unexpected_ascii_leak", self.summary["failure_reason_counts"])
        self.assertIn("semantic_slots_missing:0/1", self.summary["failure_reason_counts"])
        per_case = {}
        for row in self.rows:
            per_case[row["source_case_id"]] = per_case.get(row["source_case_id"], 0) + 1
        self.assertEqual(set(per_case.values()), {6})

    def test_training_messages_use_clean_target_not_rejected_raw_candidate(self):
        for row in self.rows:
            self.assertTrue(row["failure_reasons"])
            self.assertTrue(row["rejected_candidate_examples"])
            messages_text = json.dumps(row["messages"], ensure_ascii=False)
            for example in row["rejected_candidate_examples"]:
                raw = example.get("raw_candidate") or ""
                self.assertNotIn(raw, messages_text)
            payload = json.loads(row["messages"][1]["content"])
            self.assertTrue(payload["required_marker_groups"])
            self.assertTrue(
                all(
                    any(str(marker) and str(marker) in row["messages"][-1]["content"] for marker in group)
                    for group in payload["required_marker_groups"]
                )
            )
            self.assertEqual(row["messages"][-1]["content"].strip(), row["messages"][-1]["content"])

    def test_explicit_memory_payload_preserves_allowed_memory_contract(self):
        row = next(item for item in self.rows if item["source_case_id"] == "explicit_stomach_coffee")
        payload = json.loads(row["messages"][1]["content"])
        brief = payload["context"]["audited_memory_brief"]
        assistant = row["messages"][-1]["content"]

        self.assertEqual(brief["policy"], "explicit_allowed")
        self.assertTrue(brief["allowed_memory_cues"])
        self.assertIn(["最近は胃が弱い", "胃が弱い"], payload["required_marker_groups"])
        self.assertIn(["コーヒー", "珈琲"], payload["required_marker_groups"])
        self.assertIn("胃", assistant)
        self.assertIn("コーヒー", assistant)

    def test_background_memory_payload_does_not_train_memory_leak(self):
        row = next(item for item in self.rows if item["source_case_id"] == "background_family_pressure")
        payload = json.loads(row["messages"][1]["content"])
        brief = payload["context"]["audited_memory_brief"]
        assistant = row["messages"][-1]["content"]

        self.assertEqual(brief["policy"], "background_only")
        self.assertEqual(brief["allowed_memory_cues"], [])
        self.assertNotIn("家庭の話", payload["required_marker_groups"][0])
        self.assertNotIn("家庭の話", assistant)


if __name__ == "__main__":
    unittest.main()
