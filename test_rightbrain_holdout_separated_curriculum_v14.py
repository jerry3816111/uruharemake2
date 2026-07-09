import json
import unittest

from build_rightbrain_holdout_separated_curriculum_v14 import build_curriculum
from compare_rightbrain_runtime_adapter_multiseed import _curriculum_boundary


class RightBrainHoldoutSeparatedCurriculumV14Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.summary = build_curriculum()

    def test_builds_holdout_separated_rows(self):
        self.assertEqual(self.summary["curriculum_row_count"], 40)
        self.assertEqual(self.summary["family_spec_count"], 10)
        self.assertEqual(self.summary["data_boundary"]["holdout_case_overlap_count"], 0)
        self.assertEqual(self.summary["data_boundary"]["holdout_target_overlap_count"], 0)
        self.assertFalse(self.summary["data_boundary"]["diagnostic_only"])

    def test_curriculum_boundary_allows_promotion_evidence_when_no_overlap(self):
        boundary = _curriculum_boundary(self.rows, [])

        self.assertTrue(boundary["provided"])
        self.assertEqual(boundary["training_row_count"], 40)
        self.assertEqual(boundary["holdout_case_overlap_count"], 0)
        self.assertEqual(boundary["holdout_target_overlap_count"], 0)
        self.assertFalse(boundary["diagnostic_only"])

    def test_rows_use_canonical_contract_and_hit_required_groups(self):
        for row in self.rows:
            payload = json.loads(row["messages"][1]["content"])
            assistant = row["messages"][-1]["content"]
            self.assertEqual(payload["contract_version"], "plan_surface_contract_v1")
            self.assertTrue(row["source_case_id"].startswith("v14_"))
            self.assertEqual(assistant.strip(), assistant)
            self.assertNotRegex(assistant, r"[A-Za-z][A-Za-z0-9_-]{1,}")
            self.assertNotIn("です", assistant)
            self.assertNotIn("ます", assistant)
            for group in payload["required_marker_groups"]:
                self.assertTrue(any(str(marker) and str(marker) in assistant for marker in group), row)

    def test_failure_families_cover_v13_regression_modes(self):
        families = self.summary["failure_family_counts"]

        self.assertIn("unexpected_ascii_leak", families)
        self.assertIn("nonstandard_cjk_surface", families)
        self.assertIn("semantic_slots_missing", families)
        self.assertIn("over_max_chars", families)
        self.assertIn("polite_tone_drift", families)
        self.assertIn("duplicate_candidate", families)


if __name__ == "__main__":
    unittest.main()
