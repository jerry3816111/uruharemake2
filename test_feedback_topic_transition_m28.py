import json
import unittest

import uruha_adaptive_person_model as uapm
import uruha_personhood_loop as upl
import uruha_web_ui as web
from test_adaptive_person_model_m16 import AMBIGUOUS_INPUT
from test_outcome_calibrated_implicit_response_m26 import (
    PRACTICAL_CORRECTION,
    REPEATED_AMBIGUOUS,
)
from test_personhood_loop_v2_13 import _IsolatedContractBrain
from uruha_memory_observatory import collect_cognitive_graph, render_memory_observatory


def pragmatic_for(text, turn_index=1):
    return upl.build_human_pragmatic_understanding(text, turn_index=turn_index)


class FeedbackTopicTransitionM28Tests(unittest.TestCase):
    def test_pure_linked_support_becomes_short_acknowledgement(self):
        feedback = {
            "status": "supported",
            "reason": "explicit_generic_support",
            "previous_prediction_id": "m18-0001-test",
            "feedback_linked_to_previous_prediction": True,
            "causal_outcome_calibration_m27": {"status": "resolved_decisive"},
        }
        contract = uapm.build_feedback_topic_transition_m28(
            "對，就是這樣。",
            feedback,
            pragmatic_for("對，就是這樣。"),
        )

        self.assertEqual(contract["status"], "pure_feedback_acknowledgement")
        self.assertEqual(contract["expected_surface_jp"], "ん、分かった。")
        self.assertTrue(contract["surface_authority"])
        self.assertTrue(contract["suppresses_new_pending_prediction"])
        self.assertTrue(contract["m27_outcome_preserved"])

    def test_support_plus_new_request_is_not_mistaken_for_pure_feedback(self):
        feedback = {
            "status": "supported",
            "reason": "generic_support_precedes_new_explicit_request",
            "previous_prediction_id": "m18-0001-test",
            "feedback_linked_to_previous_prediction": True,
        }
        text = "對，就是這樣。現在請給我一個方法。"
        contract = uapm.build_feedback_topic_transition_m28(
            text,
            feedback,
            pragmatic_for(text),
        )

        self.assertEqual(contract["status"], "not_applied")
        self.assertFalse(contract["surface_authority"])

    def test_unlinked_rain_observation_rebases_to_current_topic(self):
        feedback = {
            "status": "uncertain",
            "reason": "no_decisive_feedback_about_response_policy",
            "previous_prediction_id": "m18-0003-test",
            "feedback_linked_to_previous_prediction": False,
            "causal_outcome_calibration_m27": {
                "status": "resolved_unknown_excluded"
            },
        }
        text = "今天外面下雨。"
        contract = uapm.build_feedback_topic_transition_m28(
            text,
            feedback,
            pragmatic_for(text),
        )

        self.assertEqual(contract["status"], "current_topic_rebase")
        self.assertEqual(contract["topic_kind"], "weather_rain")
        self.assertEqual(
            contract["expected_surface_jp"],
            "雨なんだ。出るなら傘忘れんなよ。",
        )
        self.assertTrue(contract["surface_authority"])
        self.assertEqual(
            contract["previous_outcome"]["m27_status"],
            "resolved_unknown_excluded",
        )

    def test_genuinely_incomplete_deictic_fragment_keeps_clarification_path(self):
        feedback = {
            "status": "uncertain",
            "previous_prediction_id": "m18-0003-test",
            "feedback_linked_to_previous_prediction": False,
        }
        contract = uapm.build_feedback_topic_transition_m28(
            "那個……",
            feedback,
            pragmatic_for("那個……"),
        )

        self.assertEqual(contract["status"], "not_applied")
        self.assertFalse(contract["surface_authority"])

    def test_protected_current_turn_cannot_be_overridden(self):
        contract = {
            "schema": uapm.FEEDBACK_TOPIC_TRANSITION_SCHEMA_M28,
            "status": "current_topic_rebase",
            "surface_authority": True,
            "expected_surface_jp": "そっか。",
            "suppresses_new_pending_prediction": True,
            "raw_dialogue_persisted": False,
        }
        plan, applied = uapm.apply_feedback_topic_transition_m28(
            {
                "intent": "crisis_support",
                "scene": "crisis",
                "core_message_jp": "今は一人になるな。",
            },
            contract,
        )

        self.assertEqual(applied["status"], "protected_current_turn_retained")
        self.assertFalse(applied["surface_authority"])
        self.assertEqual(plan["core_message_jp"], "今は一人になるな。")

    def test_real_runtime_support_and_topic_shift_keep_m27_and_show_graph(self):
        support_brain = _IsolatedContractBrain()
        support_brain.run_turn_debug(AMBIGUOUS_INPUT)
        support_brain.run_turn_debug(PRACTICAL_CORRECTION)
        support_brain.run_turn_debug(REPEATED_AMBIGUOUS)
        supported = support_brain.run_turn_debug("對，就是這樣。")

        support_contract = supported["runtime_trace"][
            "feedback_topic_transition_m28"
        ]
        self.assertEqual(supported["reply"], "ん、分かった。")
        self.assertEqual(
            support_contract["status"],
            "pure_feedback_acknowledgement",
        )
        self.assertEqual(support_contract["surface_status"], "matched")
        self.assertEqual(
            supported["runtime_trace"]["causal_outcome_calibration_m27"]
            ["effective_decisive_executed_samples"],
            1,
        )
        self.assertIsNone(
            support_brain.runtime.adaptive_person_model.get("pending_prediction")
        )

        topic_brain = _IsolatedContractBrain()
        topic_brain.run_turn_debug(AMBIGUOUS_INPUT)
        topic_brain.run_turn_debug(PRACTICAL_CORRECTION)
        topic_brain.run_turn_debug(REPEATED_AMBIGUOUS)
        shifted = topic_brain.run_turn_debug("今天外面下雨。")
        transition = shifted["runtime_trace"]["feedback_topic_transition_m28"]

        self.assertEqual(shifted["reply"], "雨なんだ。出るなら傘忘れんなよ。")
        self.assertEqual(transition["status"], "current_topic_rebase")
        self.assertEqual(transition["surface_status"], "matched")
        self.assertEqual(
            shifted["runtime_trace"]["adaptive_person_feedback_m18"]
            ["causal_outcome_calibration_m27"]["status"],
            "resolved_unknown_excluded",
        )

        result = {
            "user_text": "isolated",
            "reply": shifted["reply"],
            "memory_data": shifted["memory_data"],
            "runtime_trace": shifted["runtime_trace"],
            "runtime_state": shifted["runtime_state"],
        }
        graph = collect_cognitive_graph(result)
        html = render_memory_observatory(result)
        labels = {node["label"] for node in graph["nodes"]}
        self.assertIn("feedback_topic_transition_m28", labels)
        self.assertIn("feedback_topic_surface_m28", labels)
        self.assertIn("FEEDBACK ACKNOWLEDGEMENT &amp; TOPIC-SHIFT CONTINUITY · M28", html)
        self.assertIn("M27 outcome preserved", html)
        self.assertTrue(graph["payload_budget_m24"]["budget_met"])

        compact = web._client_cognition_payload_m24(
            {"runtime_trace": shifted["runtime_trace"]}
        )
        self.assertIn(
            "feedback_topic_transition_m28",
            compact["runtime_trace"],
        )
        self.assertNotIn(
            "今天外面下雨。",
            json.dumps(transition, ensure_ascii=False),
        )


if __name__ == "__main__":
    unittest.main()
