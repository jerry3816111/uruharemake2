import unittest

from uruha_pragmatic_annotation_integrity_m36 import (
    classify_explicit_feedback_target_m36,
    validate_annotation_rows_m36,
)


class PragmaticAnnotationIntegrityM36Tests(unittest.TestCase):
    def test_independent_classifier_handles_compositional_multilingual_targets(self):
        examples = {
            "No, give me one concrete step this time.": "solve_regulation",
            "No, I want you to hear me out, no advice.": "listen_presence",
            "不是，先聽我把話講完，不要給建議。": "listen_presence",
            "違う、今は一つだけやることを教えて。": "solve_regulation",
            "違う、軽くツッコんで。": "playful_tease",
            "不是，先陪我一下。": "share_arousal",
        }
        for text, expected in examples.items():
            with self.subTest(text=text):
                result = classify_explicit_feedback_target_m36(text)
                self.assertEqual(result["status"], "explicit_target")
                self.assertEqual(result["policy"], expected)
                self.assertFalse(result["raw_feedback_persisted"])

    def test_validator_rejects_the_m35_annotation_failure_shape(self):
        rows = [
            {
                "case_id": "bad-contradiction",
                "expected_current_policy": "playful_tease",
                "feedback_input": "No, give me one concrete step this time.",
                "expected_feedback_outcome": "contradicted",
                "expected_feedback_policy": "not_scored",
                "feedback_policy_scoring": "not_scored",
            },
            {
                "case_id": "bad-support",
                "expected_current_policy": "listen_presence",
                "feedback_input": "Exactly.",
                "expected_feedback_outcome": "supported",
                "expected_feedback_policy": "listen_presence",
                "feedback_policy_scoring": "scored",
            },
        ]
        result = validate_annotation_rows_m36(rows)
        self.assertFalse(result["passed"])
        self.assertIn(
            "bad-contradiction:contradiction_feedback_policy_must_be_scored",
            result["errors"],
        )
        self.assertIn(
            "bad-support:noncontradiction_feedback_policy_must_be_not_scored",
            result["errors"],
        )

    def test_validator_accepts_scored_corrections_and_outcome_only_other_rows(self):
        rows = [
            {
                "case_id": "correction",
                "expected_current_policy": "playful_tease",
                "feedback_input": "No, let me talk, don't give me advice.",
                "expected_feedback_outcome": "contradicted",
                "expected_feedback_policy": "listen_presence",
                "feedback_policy_scoring": "scored",
            },
            {
                "case_id": "support",
                "expected_current_policy": "listen_presence",
                "feedback_input": "Exactly, keep listening.",
                "expected_feedback_outcome": "supported",
                "expected_feedback_policy": "not_scored",
                "feedback_policy_scoring": "not_scored",
            },
            {
                "case_id": "uncertain",
                "expected_current_policy": "share_arousal",
                "feedback_input": "Anyway, tomorrow is another day.",
                "expected_feedback_outcome": "uncertain",
                "expected_feedback_policy": None,
                "feedback_policy_scoring": "not_scored",
            },
        ]
        result = validate_annotation_rows_m36(rows)
        self.assertTrue(result["passed"], result["errors"])
        self.assertEqual(result["error_count"], 0)
        self.assertTrue(all(not row["raw_feedback_persisted"] for row in result["audits"]))

    def test_ambiguous_multiple_targets_fail_closed(self):
        target = classify_explicit_feedback_target_m36(
            "No, tease me first and then give me one step."
        )
        self.assertEqual(target["status"], "ambiguous_multiple_targets")
        self.assertIsNone(target["policy"])


if __name__ == "__main__":
    unittest.main()
