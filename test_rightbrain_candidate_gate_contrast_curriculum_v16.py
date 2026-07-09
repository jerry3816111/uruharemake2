import json
import unittest

from build_rightbrain_candidate_gate_contrast_curriculum_v16 import build_curriculum
from rightbrain_language_quality import ASCII_WORD_RE, FOREIGN_SCRIPT_RE, NONSTANDARD_CJK_RE


class RightBrainCandidateGateContrastCurriculumV16Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.summary = build_curriculum()

    def test_builds_holdout_separated_watchlist_rows(self):
        self.assertEqual(self.summary["curriculum_row_count"], 32)
        self.assertEqual(self.summary["family_spec_count"], 8)
        self.assertEqual(self.summary["data_boundary"]["holdout_case_overlap_count"], 0)
        self.assertEqual(self.summary["data_boundary"]["holdout_target_overlap_count"], 0)
        self.assertFalse(self.summary["data_boundary"]["diagnostic_only"])

    def test_rows_use_runtime_watchlist_contract(self):
        for row in self.rows:
            with self.subTest(row=row["id"]):
                payload = json.loads(row["messages"][1]["content"])
                assistant = row["messages"][-1]["content"]

                self.assertEqual(payload["contract_version"], "plan_surface_contract_v1")
                self.assertTrue(row["source_case_id"].startswith("v16_"))
                self.assertEqual(row["training_role"], "rightbrain_candidate_gate_failure_watchlist_v16_sft")
                self.assertEqual(payload["surface_failure_watchlist"]["priority_order"][0], "semantic_contract_first")
                self.assertIn("semantic_slots_missing", payload["surface_failure_watchlist"]["reject_families"])
                self.assertIn("unexpected_ascii_leak", payload["surface_failure_watchlist"]["reject_families"])
                self.assertEqual(assistant.strip(), assistant)
                self.assertNotRegex(assistant, ASCII_WORD_RE)
                self.assertNotRegex(assistant, FOREIGN_SCRIPT_RE)
                self.assertNotRegex(assistant, NONSTANDARD_CJK_RE)
                self.assertNotIn("です", assistant)
                self.assertNotIn("ます", assistant)
                for group in payload["required_marker_groups"]:
                    self.assertTrue(any(str(marker) and str(marker) in assistant for marker in group), row)

    def test_targets_pr68_regressed_families(self):
        families = self.summary["failure_family_counts"]

        for family in (
            "semantic_slots_missing",
            "unexpected_ascii_leak",
            "cjk_language_leak",
            "polite_tone_drift",
            "nonstandard_cjk_surface",
            "unicode_replacement_character",
            "over_max_chars",
        ):
            self.assertIn(family, families)
            self.assertGreater(families[family], 0)


if __name__ == "__main__":
    unittest.main()
