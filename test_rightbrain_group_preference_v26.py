import unittest

from build_rightbrain_group_preference_v26 import build_groups


class RightBrainGroupPreferenceV26Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.groups, cls.summary = build_groups(promotion_holdout_outputs=set())

    def test_builder_recovers_cross_seed_multi_response_groups(self):
        self.assertTrue(self.summary["authorize_group_probe"])
        self.assertEqual(self.summary["raw_unique_candidate_count"], 94)
        self.assertEqual(self.summary["group_count"], 12)
        self.assertEqual(self.summary["positive_candidate_count"], 33)
        self.assertEqual(self.summary["negative_candidate_count"], 37)
        self.assertEqual(self.summary["training_candidate_count"], 70)
        self.assertEqual(self.summary["source_family_count"], 7)

    def test_each_group_keeps_multiple_valid_answers_unordered(self):
        self.assertTrue(
            all(group["positives"] and group["negatives"] for group in self.groups)
        )
        self.assertTrue(any(len(group["positives"]) > 1 for group in self.groups))
        self.assertTrue(
            all(group["group_rule"].startswith("unordered_") for group in self.groups)
        )
        for group in self.groups:
            texts = [
                row["text"] for row in [*group["positives"], *group["negatives"]]
            ]
            self.assertEqual(len(texts), len(set(texts)))

    def test_holdout_output_is_removed_before_dataset_authorization(self):
        held_out_text = self.groups[0]["negatives"][0]["text"]

        groups, summary = build_groups(
            promotion_holdout_outputs={held_out_text},
        )

        final_texts = {
            row["text"]
            for group in groups
            for row in [*group["positives"], *group["negatives"]]
        }
        self.assertNotIn(held_out_text, final_texts)
        self.assertEqual(summary["excluded_promotion_holdout_candidate_count"], 1)
        self.assertTrue(
            summary["gates"]["promotion_holdout_candidate_text_overlap_is_zero"]
        )


if __name__ == "__main__":
    unittest.main()
