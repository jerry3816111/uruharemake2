import unittest

from collect_rightbrain_on_policy_candidates_v29 import (
    DEFAULT_CANDIDATE_COUNT,
    DEFAULT_SEED,
    build_candidate_report,
)
from rightbrain_on_policy_dev_cases_v29 import case_inputs, validate_cases


class RightBrainOnPolicyDevV29Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = case_inputs()
        cls.validation = validate_cases(cls.cases)

    def test_fresh_cases_are_source_and_holdout_separated(self):
        self.assertTrue(self.validation["valid"], msg=self.validation["errors"])
        self.assertEqual(self.validation["case_count"], 12)
        self.assertEqual(self.validation["source_family_count"], 12)
        self.assertGreaterEqual(self.validation["category_count"], 8)
        self.assertEqual(self.validation["promotion_holdout_case_overlap_count"], 0)
        self.assertEqual(self.validation["promotion_holdout_input_overlap_count"], 0)
        self.assertEqual(self.validation["v21_case_overlap_count"], 0)
        self.assertEqual(self.validation["v21_input_overlap_count"], 0)
        self.assertEqual(self.validation["prior_human_blind_input_overlap_count"], 0)

    def test_every_case_has_an_observable_speech_contract(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                self.assertTrue(case["required_marker_groups"])
                self.assertTrue(case["logic"]["human_speech_plan"])
                self.assertEqual(case["source_case"]["id"], case["id"])

    def test_collection_defaults_are_small_but_multi_candidate(self):
        self.assertEqual(DEFAULT_CANDIDATE_COUNT, 3)
        self.assertEqual(DEFAULT_SEED, 20260712)

    def test_focused_collection_rejects_unknown_case_ids_before_model_loading(self):
        with self.assertRaisesRegex(ValueError, "Unknown V29 case IDs"):
            build_candidate_report(
                "unused",
                DEFAULT_CANDIDATE_COUNT,
                DEFAULT_SEED,
                load_model=False,
                case_ids=["not_a_v29_case"],
            )


if __name__ == "__main__":
    unittest.main()
