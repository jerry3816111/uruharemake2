import unittest

from reflection_classifier_v1_external_holdout_core import analyze_matched


CASES = [
    {"id": "s", "language": "eng", "text": "s", "expected_type": "semantic"},
    {"id": "p", "language": "eng", "text": "p", "expected_type": "procedural"},
    {"id": "i", "language": "eng", "text": "i", "expected_type": "interpretive"},
    {"id": "n", "language": "eng", "text": "n", "expected_type": "none"},
]
PASS_GATES = {
    "candidate_correct_count_min": 4,
    "candidate_overall_accuracy_min": 1.0,
    "candidate_semantic_correct_min": 1,
    "candidate_procedural_correct_min": 1,
    "candidate_interpretive_correct_min": 1,
    "candidate_none_correct": 1,
    "critical_false_positive_count_max": 0,
    "regression_vs_legacy_count_max": 0,
    "newly_correct_vs_legacy_count_min": 1,
}


class ReflectionClassifierV1ExternalHoldoutCoreTest(unittest.TestCase):
    def test_matched_improvement_passes_all_gates(self):
        raw = [
            {
                "id": case["id"],
                "legacy_observed_type": "none",
                "candidate_observed_type": case["expected_type"],
            }
            for case in CASES
        ]
        result = analyze_matched(CASES, raw, PASS_GATES)
        self.assertTrue(result["all_gates_pass"])
        self.assertEqual(result["legacy"]["correct_count"], 1)
        self.assertEqual(result["candidate"]["correct_count"], 4)
        self.assertEqual(result["newly_correct_count"], 3)
        self.assertEqual(result["regression_count"], 0)

    def test_none_false_positive_and_regression_fail_closed(self):
        raw = [
            {
                "id": case["id"],
                "legacy_observed_type": case["expected_type"],
                "candidate_observed_type": (
                    "semantic" if case["expected_type"] == "none" else "none"
                ),
            }
            for case in CASES
        ]
        result = analyze_matched(CASES, raw, PASS_GATES)
        self.assertFalse(result["all_gates_pass"])
        self.assertEqual(result["critical_false_positive_count"], 1)
        self.assertEqual(result["regression_count"], 4)

    def test_duplicate_or_unknown_predictions_are_rejected(self):
        duplicate = [
            {"id": "s", "legacy_observed_type": "none", "candidate_observed_type": "none"},
            {"id": "s", "legacy_observed_type": "none", "candidate_observed_type": "none"},
        ]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            analyze_matched(CASES, duplicate, PASS_GATES)

        raw = [
            {
                "id": case["id"],
                "legacy_observed_type": "none",
                "candidate_observed_type": "unknown" if case["id"] == "s" else "none",
            }
            for case in CASES
        ]
        with self.assertRaisesRegex(ValueError, "unknown observed type"):
            analyze_matched(CASES, raw, PASS_GATES)


if __name__ == "__main__":
    unittest.main()
