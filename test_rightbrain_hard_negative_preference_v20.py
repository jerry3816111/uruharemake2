import unittest

from build_rightbrain_hard_negative_preference_v20 import build_pairs


class RightBrainHardNegativePreferenceV20Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.summary = build_pairs()

    def test_builds_32_single_slot_hard_negatives(self):
        self.assertEqual(len(self.rows), 32)
        self.assertTrue(self.summary["all_pairs_single_slot_omission"])
        for row in self.rows:
            self.assertEqual(len(row["pair_diagnostics"]["omitted_group_indexes"]), 1)

    def test_all_pairs_are_length_matched(self):
        self.assertTrue(self.summary["all_pairs_length_matched"])
        self.assertLessEqual(self.summary["length_profile_chars"]["max_absolute_delta"], 10)

    def test_promotion_holdout_is_untouched(self):
        boundary = self.summary["data_boundary"]
        self.assertFalse(boundary["diagnostic_only"])
        self.assertEqual(boundary["holdout_case_overlap_count"], 0)
        self.assertEqual(boundary["holdout_target_overlap_count"], 0)


if __name__ == "__main__":
    unittest.main()
