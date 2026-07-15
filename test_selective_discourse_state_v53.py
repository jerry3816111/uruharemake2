#!/usr/bin/env python3

import json
import unittest
from pathlib import Path

from action_candidate_perception_v47 import load_v47_anchor_ontology
from grounded_commitment_classifier_v42 import ground_supported_targets
from selective_discourse_state_v53 import resolve_target_state, select_commitment


ROOT = Path(__file__).resolve().parent
V52_CONFIG = json.loads(
    (ROOT / "configs" / "precise_target_mentions_v52_preregistration.json").read_text(
        encoding="utf-8"
    )
)
PATTERNS = V52_CONFIG["causal_change"]["target_mention_patterns"]


class SelectiveDiscourseStateV53Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ontology = load_v47_anchor_ontology()

    def resolve(self, text, target_id):
        candidates = ground_supported_targets(text, self.ontology)
        self.assertIn(target_id, {row["target_id"] for row in candidates})
        return resolve_target_state(text, candidates, target_id, PATTERNS)

    def test_direct_request_is_requested(self):
        row = self.resolve("正面を見てください。", "gaze.user")
        self.assertTrue(row["resolved"])
        self.assertEqual(row["commitment"], "requested")
        self.assertEqual(row["resolution_rule"], "explicit_request_force")

    def test_descriptive_third_party_action_is_mentioned(self):
        row = self.resolve("彼女は右を見ていた。", "gaze.right")
        self.assertEqual(row["commitment"], "mentioned")
        self.assertEqual(row["resolution_rule"], "descriptive_or_habitual_mention")

    def test_question_about_action_is_not_a_request(self):
        row = self.resolve("どうして私を見てるの？", "gaze.user")
        self.assertEqual(row["commitment"], "mentioned")
        self.assertEqual(row["resolution_rule"], "nonrequest_question")

    def test_request_question_remains_requested(self):
        row = self.resolve("こちらを見てもらえる？", "gaze.user")
        self.assertEqual(row["commitment"], "requested")

    def test_quoted_data_is_mentioned(self):
        row = self.resolve(
            "例文の『手を振って』は文字列として保存する。", "motion.wave"
        )
        self.assertEqual(row["commitment"], "mentioned")
        self.assertEqual(row["resolution_rule"], "quoted_or_metalinguistic_mention")

    def test_quoted_data_with_nonexecution_is_negated(self):
        row = self.resolve(
            "引用文は『左を向いて』。この指示は実行しないで。", "gaze.left"
        )
        self.assertEqual(row["commitment"], "negated")

    def test_local_negation_does_not_spread_to_alternative(self):
        text = "右を見ないで、左を向いて。"
        right = self.resolve(text, "gaze.right")
        left = self.resolve(text, "gaze.left")
        self.assertEqual(right["commitment"], "negated")
        self.assertEqual(left["commitment"], "requested")

    def test_idle_lexical_negation_is_positive_request(self):
        row = self.resolve("しばらく動かないでいてください。", "motion.idle")
        self.assertEqual(row["commitment"], "requested")
        self.assertEqual(row["resolution_rule"], "positive_idle_request")

    def test_explicit_hypothesis_and_pending_choice_do_not_execute(self):
        hypothetical = self.resolve("もし合図が来たら手を振って。", "motion.wave")
        pending = self.resolve("うなずくかは後で決めよう。", "motion.nod")
        self.assertEqual(hypothetical["commitment"], "hypothetical")
        self.assertEqual(pending["commitment"], "ambiguous")

    def test_late_cross_target_correction_cancels_old_request(self):
        text = "右を見て。いや、左を向いて。"
        right = self.resolve(text, "gaze.right")
        left = self.resolve(text, "gaze.left")
        self.assertEqual(right["commitment"], "cancelled")
        self.assertEqual(left["commitment"], "requested")

    def test_unresolved_case_uses_frozen_fallback(self):
        row = self.resolve("笑顔のことかな。", "expression.happy")
        self.assertFalse(row["resolved"])
        selected = select_commitment(row, "mentioned")
        self.assertEqual(selected["commitment"], "mentioned")
        self.assertTrue(selected["fallback_used"])

    def test_state_output_contains_no_execution_call(self):
        row = self.resolve("左を向いてください。", "gaze.left")
        self.assertNotIn("expected_calls", row)
        self.assertNotIn("execute_now", row)
        self.assertNotIn("accepted_calls", row)


if __name__ == "__main__":
    unittest.main()
