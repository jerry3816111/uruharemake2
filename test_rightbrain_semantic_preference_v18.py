import unittest

from build_rightbrain_semantic_preference_v18 import build_preference_pairs


class RightBrainSemanticPreferenceV18Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.summary = build_preference_pairs()

    def test_builds_complete_over_omitted_pairs(self):
        self.assertEqual(len(self.rows), 32)
        self.assertTrue(self.summary["all_chosen_cover_every_required_group"])
        self.assertTrue(self.summary["all_rejected_omit_required_group"])
        self.assertTrue(self.summary["all_rejected_keep_clean_direct_surface"])
        for row in self.rows:
            diagnostics = row["pair_diagnostics"]
            self.assertLess(
                diagnostics["rejected_hit_count"],
                diagnostics["required_group_count"],
            )
            self.assertNotEqual(row["chosen"], row["rejected"])
            self.assertNotIn("決めつけず。", row["rejected"])
            self.assertNotIn("分からないし。", row["rejected"])

    def test_uses_compact_runtime_contract_without_failure_watchlist(self):
        for row in self.rows:
            payload = row["prompt_messages"][1]["content"]
            self.assertNotIn("surface_failure_watchlist", payload)
            self.assertIn("required_marker_groups", payload)

    def test_promotion_holdout_remains_separated(self):
        boundary = self.summary["data_boundary"]
        self.assertFalse(boundary["diagnostic_only"])
        self.assertEqual(boundary["holdout_case_overlap_count"], 0)
        self.assertEqual(boundary["holdout_target_overlap_count"], 0)

    def test_source_ids_do_not_reuse_v16_or_holdout_case_ids(self):
        self.assertTrue(all(row["source_case_id"].startswith("v18_") for row in self.rows))


if __name__ == "__main__":
    unittest.main()
