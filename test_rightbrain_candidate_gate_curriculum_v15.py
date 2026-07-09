import json
import unittest

from build_rightbrain_candidate_gate_curriculum_v15 import build_curriculum
from rightbrain_language_quality import ASCII_WORD_RE, FOREIGN_SCRIPT_RE, NONSTANDARD_CJK_RE


class RightBrainCandidateGateCurriculumV15Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.summary = build_curriculum()

    def test_builds_generalized_rows_without_holdout_overlap(self):
        self.assertEqual(self.summary["curriculum_row_count"], 32)
        self.assertEqual(self.summary["family_spec_count"], 8)
        self.assertEqual(self.summary["data_boundary"]["holdout_case_overlap_count"], 0)
        self.assertEqual(self.summary["data_boundary"]["holdout_target_overlap_count"], 0)
        self.assertFalse(self.summary["data_boundary"]["diagnostic_only"])

    def test_rows_use_canonical_contract_and_clean_surface(self):
        for row in self.rows:
            with self.subTest(row=row["id"]):
                payload = json.loads(row["messages"][1]["content"])
                assistant = row["messages"][-1]["content"]
                self.assertEqual(payload["contract_version"], "plan_surface_contract_v1")
                self.assertTrue(row["source_case_id"].startswith("v15_"))
                self.assertEqual(assistant.strip(), assistant)
                self.assertNotRegex(assistant, ASCII_WORD_RE)
                self.assertNotRegex(assistant, FOREIGN_SCRIPT_RE)
                self.assertNotRegex(assistant, NONSTANDARD_CJK_RE)
                self.assertNotIn("です", assistant)
                self.assertNotIn("ます", assistant)
                self.assertNotIn("てあげ", assistant)
                self.assertNotIn("．", assistant)
                for group in payload["required_marker_groups"]:
                    self.assertTrue(any(str(marker) and str(marker) in assistant for marker in group), row)

    def test_covers_pr66_candidate_gate_failure_families(self):
        families = self.summary["failure_family_counts"]
        observed = self.summary["source_diagnostic_family_counts"]

        for family in (
            "unexpected_ascii_leak",
            "semantic_slots_missing",
            "polite_tone_drift",
            "nonstandard_cjk_surface",
            "cjk_language_leak",
            "over_max_chars",
            "foreign_script_leak",
            "nonstandard_punctuation",
            "missing_japanese_surface",
        ):
            self.assertIn(family, observed)
            self.assertIn(family, families)


if __name__ == "__main__":
    unittest.main()
