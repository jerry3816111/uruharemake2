import json
import unittest

import uruha_adaptive_person_model as uapm
import uruha_counterfactual_pragmatic_branch_m34 as m34
from uruha_m38_memory_observatory import render_memory_observatory_m38
from uruha_runtime import RuntimeState  # noqa: F401 - installs the shared adapter
from uruha_target_guarded_feedback_m38 import (
    classify_target_guarded_feedback_m38,
)


def _pending_model(policy_id="playful_tease"):
    return uapm.set_pending_prediction(
        uapm.empty_model(),
        {
            "prediction_id": "m38-dev-prediction",
            "selected": {
                "policy_id": policy_id,
                "expected_utility": 0.8,
                "response_dimensions": {},
                "realization": {},
            },
            "utility_margin": 0.2,
            "state": {
                "input_digest": "m38-dev-current",
                "context_scope": {
                    "domain": "general_conversation",
                    "scene": "emotional_support",
                    "topic": "current_disclosure",
                    "relationship_band": "familiar",
                },
            },
            "implicit_desired_response_m26": {
                "status": "execute_implicit",
                "implicit_top_policy": policy_id,
                "implicit_top_mode": "development_probe",
                "top_probability": 0.8,
                "probability_margin": 0.2,
                "evidence_quality": 0.8,
            },
        },
        turn_index=3,
    )


class TargetGuardedMultiscriptFeedbackM38Tests(unittest.TestCase):
    def test_multilingual_unique_replacement_links_to_pending_prediction(self):
        examples = {
            "不對，先聽我把整件事說完，暫時別分析。": "listen_presence",
            "You misunderstood; give me one practical step I can take now.": "solve_regulation",
            "読み違えてる。今はそばにいて。": "share_arousal",
        }
        for text, expected in examples.items():
            with self.subTest(text=text):
                trace = classify_target_guarded_feedback_m38(
                    text,
                    {"prediction_id": "p1", "policy_id": "playful_tease"},
                )
                self.assertEqual(trace["outcome"], "contradicted")
                self.assertTrue(trace["feedback_linked_to_previous_prediction"])
                self.assertEqual(trace["replacement_policy_id"], expected)
                self.assertFalse(trace["raw_dialogue_persisted"])

    def test_ordinary_negation_is_not_feedback_about_previous_response(self):
        examples = (
            "票不是今天到，是星期六。",
            "The package does not arrive today; it arrives Saturday.",
            "締切は木曜日じゃなくて、金曜日だよ。",
        )
        for text in examples:
            with self.subTest(text=text):
                trace = classify_target_guarded_feedback_m38(
                    text,
                    {"prediction_id": "p1", "policy_id": "solve_regulation"},
                )
                self.assertEqual(trace["status"], "ordinary_negation_not_feedback")
                self.assertEqual(trace["outcome"], "uncertain")
                self.assertFalse(trace["feedback_linked_to_previous_prediction"])
                self.assertIsNone(trace["replacement_policy_id"])

    def test_targetless_and_multiple_target_corrections_fail_closed(self):
        targetless = classify_target_guarded_feedback_m38(
            "不對，完全不是這樣。",
            {"prediction_id": "p1", "policy_id": "solve_regulation"},
        )
        multiple = classify_target_guarded_feedback_m38(
            "No, either listen until I finish or give me one practical step.",
            {"prediction_id": "p1", "policy_id": "playful_tease"},
        )
        self.assertEqual(targetless["status"], "fail_closed_no_replacement_target")
        self.assertEqual(multiple["status"], "fail_closed_multiple_replacement_targets")
        self.assertFalse(targetless["feedback_linked_to_previous_prediction"])
        self.assertFalse(multiple["feedback_linked_to_previous_prediction"])

    def test_exposed_chinese_m36_failure_updates_feedback_and_m34_revision(self):
        model, feedback = uapm.observe_next_turn(
            _pending_model("playful_tease"),
            "不對，這回先聽我把整段講完，不要急著建議。",
            turn_index=4,
        )
        ledger = m34.build_counterfactual_pragmatic_branch_m34(
            pragmatic_understanding={"pragmatic_label": "correction"},
            desired_response_state={
                "input_digest": "m38-feedback",
                "context_scope": {"scope_id": "general:emotional_support"},
                "scope_match": {"status": "exact", "used": []},
            },
            desired_response_decision={
                "prediction_id": "m38-new",
                "selected": {"policy_id": "listen_presence", "expected_utility": 0.8},
                "candidates": [
                    {"policy_id": "listen_presence", "expected_utility": 0.8},
                    {"policy_id": "playful_tease", "expected_utility": 0.2},
                ],
            },
            implicit_response_contract={"execute_implicit": False, "distribution": []},
            adaptive_feedback=feedback,
            previous_branch_m34={
                "branch_id": "m34-previous",
                "prediction_id": "m38-dev-prediction",
                "selected_branch": {"policy_id": "playful_tease"},
            },
            turn_index=4,
        )
        self.assertEqual(feedback["status"], "contradicted")
        self.assertTrue(feedback["feedback_linked_to_previous_prediction"])
        self.assertEqual(feedback["explicit_target_policy"], "listen_presence")
        self.assertEqual(ledger["previous_branch_verification"]["status"], "contradicted")
        self.assertEqual(ledger["revision"]["revoked_policy_id"], "playful_tease")
        self.assertEqual(ledger["revision"]["replacement_policy_id"], "listen_presence")
        self.assertNotIn("不對，這回先聽", json.dumps(model, ensure_ascii=False))

    def test_runtime_adapter_forces_ordinary_negation_to_uncertain(self):
        model, feedback = uapm.observe_next_turn(
            _pending_model("solve_regulation"),
            "這張票不是今天到，是星期六。",
            turn_index=4,
        )
        self.assertEqual(feedback["status"], "uncertain")
        self.assertFalse(feedback["feedback_linked_to_previous_prediction"])
        self.assertIsNone(feedback["explicit_target_policy"])
        self.assertEqual(
            feedback["target_guarded_feedback_m38"]["status"],
            "ordinary_negation_not_feedback",
        )
        self.assertNotIn("這張票不是今天到", json.dumps(model, ensure_ascii=False))

    def test_observatory_overlay_explains_link_or_fail_closed(self):
        trace = classify_target_guarded_feedback_m38(
            "You got that wrong; just listen until I finish.",
            {"prediction_id": "p1", "policy_id": "solve_regulation"},
        )
        html = render_memory_observatory_m38(
            {"runtime_trace": {"adaptive_person_feedback_m18": {"target_guarded_feedback_m38": trace}}}
        )
        self.assertIn("TARGET-GUARDED MULTISCRIPT FEEDBACK LINKAGE · M38", html)
        self.assertIn("solve_regulation → listen_presence", html)
        self.assertIn("普通「不／not／ない」", html)


if __name__ == "__main__":
    unittest.main()
