import json
import unittest
from copy import deepcopy
from pathlib import Path

from analyze_rightbrain_on_policy_blind_v29 import (
    _read_jsonl,
    build_analysis_report,
)
from project_paths import (
    RIGHTBRAIN_ON_POLICY_V29_BLIND_KEY_PATH,
    RIGHTBRAIN_ON_POLICY_V29_BLIND_PACKAGE_PATH,
)


def _complete_ratings(package, key_rows, base_choices=None):
    base_choices = dict(base_choices or {})
    key_map = {row["comparison_id"]: row for row in key_rows}
    for row in key_rows:
        if not row["is_consistency_repeat"]:
            base_choices.setdefault(row["comparison_id"], "left_better")
    ratings = []
    for comparison in package["comparisons"]:
        comparison_id = comparison["comparison_id"]
        key = key_map[comparison_id]
        if key["is_consistency_repeat"]:
            base_choice = base_choices[key["repeat_of"]]
            choice = {
                "left_better": "right_better",
                "right_better": "left_better",
                "tie": "tie",
                "both_bad": "both_bad",
            }[base_choice]
        else:
            choice = base_choices[comparison_id]
        ratings.append(
            {
                "comparison_id": comparison_id,
                "choice": choice,
                "note": "",
            }
        )
    return {
        "schema_version": 1,
        "package_sha256": package["package_sha256"],
        "completed": True,
        "rated_count": len(ratings),
        "comparison_count": len(package["comparisons"]),
        "ratings": ratings,
    }


class RightBrainOnPolicyBlindV29AnalysisTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package = json.loads(
            Path(RIGHTBRAIN_ON_POLICY_V29_BLIND_PACKAGE_PATH).read_text(
                encoding="utf-8"
            )
        )
        cls.key_rows = _read_jsonl(RIGHTBRAIN_ON_POLICY_V29_BLIND_KEY_PATH)
        cls.base_ids = [
            row["comparison_id"]
            for row in cls.key_rows
            if not row["is_consistency_repeat"]
        ]

    def test_complete_side_swap_consistent_choices_authorize_only_probe(self):
        ratings = _complete_ratings(self.package, self.key_rows)
        report = build_analysis_report(self.package, self.key_rows, ratings)

        self.assertTrue(report["authorize_diagnostic_use"])
        self.assertEqual(report["summary"]["decisive_pair_count"], 9)
        self.assertEqual(report["consistency_evidence"]["consistency_rate"], 1.0)
        self.assertTrue(report["authorize_preference_dataset_build"])
        self.assertTrue(report["authorize_frozen_v10_training_probe"])
        self.assertFalse(report["authorize_runtime_promotion"])
        self.assertFalse(report["authorize_population_human_preference_claim"])

    def test_partial_ratings_are_diagnostic_but_never_training_data(self):
        ratings = _complete_ratings(self.package, self.key_rows)
        ratings["ratings"] = ratings["ratings"][:3]
        ratings["rated_count"] = 3
        ratings["completed"] = False
        report = build_analysis_report(self.package, self.key_rows, ratings)

        self.assertTrue(report["authorize_diagnostic_use"])
        self.assertEqual(report["summary"]["rated_comparison_count"], 3)
        self.assertFalse(report["authorize_preference_dataset_build"])
        self.assertFalse(report["preference_probe_gates"]["all_comparisons_are_rated"])

    def test_same_button_on_swapped_repeat_is_detected_as_inconsistent(self):
        ratings = _complete_ratings(self.package, self.key_rows)
        repeat_ids = {
            row["comparison_id"]
            for row in self.key_rows
            if row["is_consistency_repeat"]
        }
        for row in ratings["ratings"]:
            if row["comparison_id"] in repeat_ids:
                row["choice"] = "left_better"
        report = build_analysis_report(self.package, self.key_rows, ratings)

        self.assertLess(report["consistency_evidence"]["consistency_rate"], 1.0)
        self.assertFalse(report["authorize_preference_dataset_build"])

    def test_tie_and_both_bad_never_become_chosen_rejected_pairs(self):
        choices = {
            self.base_ids[0]: "tie",
            self.base_ids[1]: "both_bad",
        }
        ratings = _complete_ratings(self.package, self.key_rows, choices)
        report = build_analysis_report(self.package, self.key_rows, ratings)

        self.assertEqual(report["summary"]["tie_count"], 1)
        self.assertEqual(report["summary"]["both_bad_count"], 1)
        self.assertEqual(report["summary"]["decisive_pair_count"], 7)
        decisive_ids = {
            row["comparison_id"] for row in report["decisive_preference_pairs"]
        }
        self.assertNotIn(self.base_ids[0], decisive_ids)
        self.assertNotIn(self.base_ids[1], decisive_ids)

    def test_wrong_ratings_hash_fails_closed(self):
        ratings = _complete_ratings(self.package, self.key_rows)
        ratings["package_sha256"] = "wrong"
        report = build_analysis_report(self.package, self.key_rows, ratings)

        self.assertFalse(report["authorize_diagnostic_use"])
        self.assertFalse(report["authorize_preference_dataset_build"])
        self.assertFalse(
            report["integrity_gates"]["ratings_bind_the_same_package_hash"]
        )

    def test_key_text_mismatch_fails_closed(self):
        ratings = _complete_ratings(self.package, self.key_rows)
        key_rows = deepcopy(self.key_rows)
        key_rows[0]["left_candidate"]["text"] = "改ざん"
        report = build_analysis_report(self.package, key_rows, ratings)

        self.assertFalse(report["authorize_diagnostic_use"])
        self.assertFalse(report["authorize_preference_dataset_build"])
        self.assertFalse(
            report["integrity_gates"]["key_rows_match_blind_package_text"]
        )

    def test_declared_comparison_count_mismatch_fails_closed(self):
        ratings = _complete_ratings(self.package, self.key_rows)
        ratings["comparison_count"] += 1
        report = build_analysis_report(self.package, self.key_rows, ratings)

        self.assertFalse(report["authorize_diagnostic_use"])
        self.assertFalse(
            report["integrity_gates"][
                "declared_comparison_count_matches_package"
            ]
        )

    def test_unknown_choice_never_becomes_a_preference_pair(self):
        ratings = _complete_ratings(self.package, self.key_rows)
        target_id = self.base_ids[0]
        for row in ratings["ratings"]:
            if row["comparison_id"] == target_id:
                row["choice"] = "unknown"
        report = build_analysis_report(self.package, self.key_rows, ratings)

        self.assertFalse(report["authorize_diagnostic_use"])
        self.assertFalse(report["authorize_preference_dataset_build"])
        decisive_ids = {
            row["comparison_id"] for row in report["decisive_preference_pairs"]
        }
        self.assertNotIn(target_id, decisive_ids)


if __name__ == "__main__":
    unittest.main()
