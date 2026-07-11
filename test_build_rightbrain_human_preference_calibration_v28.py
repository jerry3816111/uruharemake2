import unittest

from build_rightbrain_human_preference_calibration_v28 import (
    _classification_metrics,
    build_calibration_report,
)


def _row(index, system_id, programmatic_pass, decision, source_id="s1"):
    return {
        "source_id": source_id,
        "review_id": f"r{index}",
        "task_id": "t1",
        "system_id": system_id,
        "category": "daily",
        "input": "input",
        "output_text": f"output-{index}",
        "scores": {"naturalness_1_5": float(index)},
        "decision": decision,
        "programmatic_pass": programmatic_pass,
    }


def _report(rows, rater_count=1):
    return build_calibration_report(
        rows,
        [{"source_id": "s1", "missing_join_count": 0, "hashes": {}}],
        source_hashes_match=True,
        missing_key_review_ids=[],
        holdout_input_overlaps=set(),
        holdout_output_overlaps=set(),
        holdout_reports=[],
        explicit_pairs=[],
        explicit_pair_errors=[],
        rater_count=rater_count,
    )


class RightBrainHumanPreferenceCalibrationV28Test(unittest.TestCase):
    def test_system_identity_confound_blocks_preference_training(self):
        rows = [
            _row(1, "S0_URUHA_RIGHTBRAIN", True, "yes"),
            _row(2, "C1", False, "borderline"),
            _row(3, "C2", False, "no"),
            _row(4, "C3", False, "no"),
        ]
        report = _report(rows)

        self.assertTrue(
            report["system_identity_confound"][
                "programmatic_pass_identical_to_s0_identity"
            ]
        )
        self.assertEqual(report["within_policy_preference_evidence"]["pair_count"], 0)
        self.assertFalse(report["authorize_preference_training"])

    def test_same_policy_pairs_and_label_variation_can_pass_training_gate(self):
        rows = [
            _row(1, "S0_URUHA_RIGHTBRAIN", True, "yes"),
            _row(2, "S0_URUHA_RIGHTBRAIN", True, "yes"),
            _row(3, "S0_URUHA_RIGHTBRAIN", False, "borderline"),
            _row(4, "S0_URUHA_RIGHTBRAIN", False, "no"),
        ]
        report = _report(rows, rater_count=2)

        self.assertEqual(report["within_policy_preference_evidence"]["pair_count"], 6)
        self.assertFalse(
            report["system_identity_confound"][
                "programmatic_pass_identical_to_s0_identity"
            ]
        )
        self.assertTrue(report["authorize_preference_training"])
        self.assertFalse(report["authorize_population_human_preference_claim"])

    def test_duplicate_text_with_conflicting_human_decisions_blocks_training(self):
        rows = [
            _row(1, "S0_URUHA_RIGHTBRAIN", True, "yes"),
            _row(2, "S0_URUHA_RIGHTBRAIN", True, "yes"),
            _row(3, "S0_URUHA_RIGHTBRAIN", False, "borderline"),
            _row(4, "S0_URUHA_RIGHTBRAIN", False, "no"),
        ]
        rows[3]["output_text"] = rows[0]["output_text"]
        report = _report(rows, rater_count=2)

        self.assertEqual(
            report["duplicate_candidate_evidence"][
                "duplicate_decision_disagreement_group_count"
            ],
            1,
        )
        self.assertFalse(
            report["preference_training_gates"][
                "exact_duplicate_human_decisions_are_consistent"
            ]
        )
        self.assertFalse(report["authorize_preference_training"])

    def test_confusion_metrics_keep_strict_counts(self):
        rows = [
            _row(1, "S0", True, "yes"),
            _row(2, "S0", True, "no"),
            _row(3, "S0", False, "yes"),
            _row(4, "S0", False, "no"),
        ]
        metrics = _classification_metrics(rows, lambda row: row["decision"] == "yes")

        self.assertEqual(metrics["true_positive"], 1)
        self.assertEqual(metrics["false_positive"], 1)
        self.assertEqual(metrics["true_negative"], 1)
        self.assertEqual(metrics["false_negative"], 1)
        self.assertEqual(metrics["balanced_accuracy"], 0.5)
        self.assertEqual(metrics["matthews_correlation"], 0.0)

    def test_package_dimensions_are_not_collapsed(self):
        rows = [
            _row(1, "S0_URUHA_RIGHTBRAIN", True, "yes", source_id="v15"),
            {
                **_row(2, "S0_URUHA_RIGHTBRAIN", False, "no", source_id="v16"),
                "scores": {"human_likeness_1_5": 2.0},
            },
            _row(3, "S0_URUHA_RIGHTBRAIN", True, "yes", source_id="v15"),
            _row(4, "S0_URUHA_RIGHTBRAIN", False, "no", source_id="v15"),
        ]
        rows.append(
            {
                **_row(5, "S0_URUHA_RIGHTBRAIN", False, "no", source_id="v15"),
                "task_id": "t2",
            }
        )
        report = build_calibration_report(
            rows,
            [
                {"source_id": "v15", "missing_join_count": 0, "hashes": {}},
                {"source_id": "v16", "missing_join_count": 0, "hashes": {}},
            ],
            source_hashes_match=True,
            missing_key_review_ids=[],
            holdout_input_overlaps=set(),
            holdout_output_overlaps=set(),
            holdout_reports=[],
            explicit_pairs=[],
            explicit_pair_errors=[],
        )

        packages = {
            row["source_id"]: row["score_fields"]
            for row in report["package_specific_dimension_summaries"]
        }
        self.assertEqual(packages["v15"], ["naturalness_1_5"])
        self.assertEqual(packages["v16"], ["human_likeness_1_5"])


if __name__ == "__main__":
    unittest.main()
