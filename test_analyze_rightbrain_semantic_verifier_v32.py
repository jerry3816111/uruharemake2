import unittest

from analyze_rightbrain_semantic_verifier_v32 import (
    _select_treatment,
    analyze_calibration,
)


class AnalyzeRightBrainSemanticVerifierV32Test(unittest.TestCase):
    def test_calibration_separates_recall_specificity_and_new_critical_fp(self):
        calibration = {
            "cases": [
                {
                    "id": "literal",
                    "family": "literal_positive",
                    "marker": "提出",
                    "reply": "提出した。",
                    "expected_hit": True,
                },
                {
                    "id": "lemma",
                    "family": "lemma_inflection_positive",
                    "marker": "軽い",
                    "reply": "軽く食べる。",
                    "expected_hit": True,
                },
                {
                    "id": "homophone",
                    "family": "homophone_negative",
                    "marker": "かんじ",
                    "reply": "漢字を書く。",
                    "expected_hit": False,
                    "critical_negative": True,
                },
            ]
        }
        summaries, rows = analyze_calibration(
            calibration,
            lambda reply, marker: marker in reply,
        )
        self.assertEqual(len(rows), 9)
        self.assertEqual(
            summaries["legacy_control"]["positive_recall"],
            0.5,
        )
        self.assertEqual(
            summaries["lemma_polarity"]["positive_recall"],
            1.0,
        )
        self.assertEqual(
            summaries["lemma_polarity"]["new_critical_false_positive_count"],
            0,
        )
        self.assertEqual(
            summaries["lemma_polarity_reading"][
                "new_critical_false_positive_count"
            ],
            1,
        )

    def test_selection_rejects_reading_gain_when_it_adds_critical_fp(self):
        summaries = {
            "legacy_control": {
                "positive_recall": 0.4,
                "negative_specificity": 0.9,
                "new_critical_false_positive_count": 0,
                "match_mode_counts": {},
            },
            "lemma_polarity": {
                "positive_recall": 0.7,
                "negative_specificity": 0.9,
                "new_critical_false_positive_count": 0,
                "match_mode_counts": {"lemma": 3},
            },
            "lemma_polarity_reading": {
                "positive_recall": 1.0,
                "negative_specificity": 0.8,
                "new_critical_false_positive_count": 1,
                "match_mode_counts": {"lemma": 3, "reading": 3},
            },
        }
        self.assertEqual(_select_treatment(summaries), "lemma_polarity")

    def test_selection_returns_none_when_every_treatment_is_less_specific(self):
        summaries = {
            "legacy_control": {
                "positive_recall": 0.4,
                "negative_specificity": 1.0,
                "new_critical_false_positive_count": 0,
                "match_mode_counts": {},
            },
            "lemma_polarity": {
                "positive_recall": 0.8,
                "negative_specificity": 0.9,
                "new_critical_false_positive_count": 0,
                "match_mode_counts": {"lemma": 4},
            },
            "lemma_polarity_reading": {
                "positive_recall": 1.0,
                "negative_specificity": 0.8,
                "new_critical_false_positive_count": 2,
                "match_mode_counts": {"reading": 5},
            },
        }
        self.assertIsNone(_select_treatment(summaries))


if __name__ == "__main__":
    unittest.main()
