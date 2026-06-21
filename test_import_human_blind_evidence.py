import csv
import json
import os
import tempfile
import unittest

from human_feedback_validation import invalid_annotation_reason
from import_human_blind_evidence import (
    S0_SYSTEM_ID,
    build_evidence_report,
    load_blind_evidence,
    merge_annotation_stream,
)


class TestHumanBlindEvidenceImport(unittest.TestCase):
    def _write_csv(self, path, rows):
        with open(path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def _fixture_spec(self, root):
        ratings_path = os.path.join(root, "ratings.csv")
        key_path = os.path.join(root, "key.jsonl")
        sheet_path = os.path.join(root, "sheet.csv")
        self._write_csv(
            ratings_path,
            [
                {
                    "review_id": "task_1__A",
                    "task_id": "task_1",
                    "output_label": "A",
                    "semantic_understanding_1_5": "2",
                    "human_likeness_1_5": "2",
                    "direct_chat_ok": "no",
                    "notes": "太模板化了",
                },
                {
                    "review_id": "task_1__B",
                    "task_id": "task_1",
                    "output_label": "B",
                    "semantic_understanding_1_5": "4",
                    "human_likeness_1_5": "4",
                    "direct_chat_ok": "yes",
                    "notes": "",
                },
                {
                    "review_id": "task_2__A",
                    "task_id": "task_2",
                    "output_label": "A",
                    "semantic_understanding_1_5": "",
                    "human_likeness_1_5": "",
                    "direct_chat_ok": "",
                    "notes": "",
                },
            ],
        )
        with open(key_path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps({"review_id": "task_1__A", "output_label": "A", "system_id": S0_SYSTEM_ID}) + "\n")
            handle.write(json.dumps({"review_id": "task_1__B", "output_label": "B", "system_id": "C1_CONTROL"}) + "\n")
            handle.write(json.dumps({"review_id": "task_2__A", "output_label": "A", "system_id": S0_SYSTEM_ID}) + "\n")
        self._write_csv(
            sheet_path,
            [
                {"review_id": "task_1__A", "task_id": "task_1", "category": "repair", "input": "重說一次", "output_text": "同一句。", "leftbrain_required_meaning": "重新說", "required_marker_groups": '[["言い直"]]', "forbidden_markers": "同じ"},
                {"review_id": "task_1__B", "task_id": "task_1", "category": "repair", "input": "重說一次", "output_text": "分かった、言い直す。", "leftbrain_required_meaning": "重新說", "required_marker_groups": '[["言い直"]]', "forbidden_markers": "同じ"},
                {"review_id": "task_2__A", "task_id": "task_2", "category": "chat", "input": "未完成", "output_text": "未評分", "leftbrain_required_meaning": "", "required_marker_groups": "[]", "forbidden_markers": ""},
            ],
        )
        return {
            "source_id": "v16_test",
            "ratings_path": ratings_path,
            "key_path": key_path,
            "sheet_path": sheet_path,
            "score_fields": ["semantic_understanding_1_5", "human_likeness_1_5"],
            "decision_field": "direct_chat_ok",
            "semantic_field": "semantic_understanding_1_5",
            "naturalness_field": "human_likeness_1_5",
            "rated_at": "2026-05-24T18:00:00+09:00",
            "designed_task_count": 2,
        }

    def test_import_excludes_blank_rows_and_control_annotations(self):
        with tempfile.TemporaryDirectory() as root:
            rows, annotations, sources = load_blind_evidence([self._fixture_spec(root)])

        self.assertEqual(len(rows), 2)
        self.assertEqual(len(annotations), 1)
        self.assertEqual(sources[0]["incomplete_candidate_count"], 1)
        annotation = annotations[0]
        self.assertEqual(annotation["verdict"], "fail")
        self.assertEqual(annotation["severity"], "high")
        self.assertIn("RIGHTBRAIN_SURFACE_ERROR", annotation["failure_types"])
        self.assertIn("MISREAD_INTENT", annotation["failure_types"])
        self.assertIn("TOO_ROBOTIC_LOGIC", annotation["failure_types"])
        self.assertIn("GENERIC_REPLY", annotation["failure_types"])
        self.assertEqual(annotation["human_contract"]["required_marker_groups"], [["言い直"]])
        self.assertEqual(invalid_annotation_reason(annotation), "")

        report = build_evidence_report(rows, annotations, sources)
        self.assertEqual(report["summary"]["completed_candidate_rating_count"], 2)
        self.assertEqual(report["summary"]["s0_annotation_count"], 1)
        self.assertEqual(len(report["by_system"]), 2)

    def test_merge_is_idempotent_for_imported_sources(self):
        interactive = {"source_kind": "web_ui", "session_id": "real", "turn_index": 1}
        stale = {"source_kind": "human_blind_import", "session_id": "old", "turn_index": 1}
        replacement = {"source_kind": "human_blind_import", "session_id": "new", "turn_index": 1}

        merged = merge_annotation_stream([interactive, stale], [replacement])

        self.assertEqual(merged, [interactive, replacement])

    def test_committed_sources_reproduce_known_completed_counts(self):
        rows, annotations, sources = load_blind_evidence()

        self.assertEqual(len(rows), 76)
        self.assertEqual(len(annotations), 19)
        self.assertEqual(sum(row["completed_task_count"] for row in sources), 19)
        self.assertEqual(sum(row["missing_join_count"] for row in sources), 0)


if __name__ == "__main__":
    unittest.main()
