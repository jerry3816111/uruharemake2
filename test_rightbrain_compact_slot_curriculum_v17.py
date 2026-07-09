import json
import unittest

from build_rightbrain_compact_slot_curriculum_v17 import build_curriculum
from rightbrain_language_quality import ASCII_WORD_RE, FOREIGN_SCRIPT_RE, NONSTANDARD_CJK_RE


class RightBrainCompactSlotCurriculumV17Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.summary = build_curriculum()

    def test_builds_holdout_separated_compact_rows(self):
        self.assertEqual(self.summary["curriculum_row_count"], 32)
        self.assertEqual(self.summary["family_spec_count"], 8)
        self.assertEqual(self.summary["data_boundary"]["holdout_case_overlap_count"], 0)
        self.assertEqual(self.summary["data_boundary"]["holdout_target_overlap_count"], 0)
        self.assertFalse(self.summary["data_boundary"]["diagnostic_only"])

    def test_rows_match_default_runtime_payload_boundary(self):
        for row in self.rows:
            with self.subTest(row=row["id"]):
                payload = json.loads(row["messages"][1]["content"])
                assistant = row["messages"][-1]["content"]

                self.assertEqual(payload["contract_version"], "plan_surface_contract_v1")
                self.assertTrue(row["source_case_id"].startswith("v17_"))
                self.assertEqual(row["training_role"], "rightbrain_compact_slot_preservation_v17_sft")
                self.assertNotIn("surface_failure_watchlist", payload)
                self.assertIn("required_marker_groups", payload)
                self.assertEqual(assistant.strip(), assistant)
                self.assertNotRegex(assistant, ASCII_WORD_RE)
                self.assertNotRegex(assistant, FOREIGN_SCRIPT_RE)
                self.assertNotRegex(assistant, NONSTANDARD_CJK_RE)
                self.assertNotIn("です", assistant)
                self.assertNotIn("ます", assistant)
                for group in payload["required_marker_groups"]:
                    self.assertTrue(any(str(marker) and str(marker) in assistant for marker in group), row)

    def test_targets_v16_regressed_semantic_slots_without_watchlist(self):
        families = self.summary["failure_family_counts"]

        self.assertIn("semantic_slots_missing", families)
        self.assertGreaterEqual(families["semantic_slots_missing"], 32)
        self.assertFalse(self.summary["runtime_payload_boundary"]["surface_failure_watchlist_present"])
        self.assertTrue(self.summary["runtime_payload_boundary"]["matches_default_watchlist_flag_off"])


if __name__ == "__main__":
    unittest.main()
