import json
import unittest

import uruha_adaptive_person_model as uapm
import uruha_brain_mac as brain_runtime
import uruha_personhood_loop as upl
import uruha_web_ui as web
from test_adaptive_person_model_m16 import AMBIGUOUS_INPUT
from test_outcome_calibrated_implicit_response_m26 import (
    PRACTICAL_CORRECTION,
    REPEATED_AMBIGUOUS,
)
from test_personhood_loop_v2_13 import _IsolatedContractBrain
from uruha_memory_observatory import collect_cognitive_graph, render_memory_observatory


class _Message:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Message(content)


class _Response:
    def __init__(self, content):
        self.choices = [_Choice(content)]


class _Completions:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _Response(json.dumps(self.payload, ensure_ascii=False))


class _Client:
    def __init__(self, payload):
        self.chat = type("Chat", (), {})()
        self.chat.completions = _Completions(payload)


def pragmatic_for(text, turn_index=4):
    return upl.build_human_pragmatic_understanding(text, turn_index=turn_index)


def unlinked_feedback():
    return {
        "status": "uncertain",
        "reason": "no_decisive_feedback_about_response_policy",
        "previous_prediction_id": "m18-0003-test",
        "feedback_linked_to_previous_prediction": False,
        "causal_outcome_calibration_m27": {
            "status": "resolved_unknown_excluded"
        },
    }


def valid_payload():
    return {
        "source_language": "zh",
        "source_anchors": ["明天", "考試"],
        "subject_jp": "明日の試験",
        "predicate_jp": "ある",
        "time_jp": "明日",
        "polarity": "affirmed",
        "literal_summary_jp": "ユーザーは明日試験があると言っている。",
        "surface_anchors_jp": ["明日", "試験"],
        "response_jp": "明日試験なんだ。今日は詰め込みすぎんなよ。",
        "confidence": 0.91,
    }


class GeneralizedLiteralTopicProjectionM29Tests(unittest.TestCase):
    def test_candidate_gate_accepts_unlinked_self_contained_non_weather_topic(self):
        text = "明天要考試。"
        candidate = uapm.build_literal_topic_projection_candidate_m29(
            text,
            unlinked_feedback(),
            pragmatic_for(text),
            {"schema": uapm.FEEDBACK_TOPIC_TRANSITION_SCHEMA_M28, "surface_authority": False},
        )

        self.assertEqual(candidate["status"], "projection_candidate")
        self.assertTrue(candidate["projection_required"])
        self.assertFalse(candidate["surface_authority"])
        self.assertEqual(candidate["m27_status"], "resolved_unknown_excluded")

    def test_m28_grounded_weather_and_incomplete_fragment_do_not_enter_m29(self):
        weather = uapm.build_literal_topic_projection_candidate_m29(
            "今天外面下雨。",
            unlinked_feedback(),
            pragmatic_for("今天外面下雨。"),
            {"schema": uapm.FEEDBACK_TOPIC_TRANSITION_SCHEMA_M28, "surface_authority": True},
        )
        fragment = uapm.build_literal_topic_projection_candidate_m29(
            "那個……",
            unlinked_feedback(),
            pragmatic_for("那個……"),
            {"schema": uapm.FEEDBACK_TOPIC_TRANSITION_SCHEMA_M28, "surface_authority": False},
        )

        self.assertEqual(weather["status"], "covered_by_bounded_m28_grounding")
        self.assertFalse(weather["projection_required"])
        self.assertEqual(fragment["status"], "not_candidate")

    def test_local_projection_validates_exact_source_and_visible_japanese_anchors(self):
        text = "明天要考試。"
        candidate = uapm.build_literal_topic_projection_candidate_m29(
            text,
            unlinked_feedback(),
            pragmatic_for(text),
        )
        left = brain_runtime.LeftBrain(_Client(valid_payload()))
        plan, contract = left.project_literal_topic_m29(text, candidate)

        self.assertEqual(contract["status"], "projected_and_validated")
        self.assertTrue(contract["surface_authority"])
        self.assertTrue(all(contract["validation_checks"].values()))
        self.assertEqual(contract["subject_jp"], "明日の試験")
        self.assertEqual(contract["predicate_jp"], "ある")
        self.assertEqual(plan["core_message_jp"], contract["response_jp"])
        self.assertNotIn(text, json.dumps(contract, ensure_ascii=False))
        self.assertNotIn("source_anchors", contract)

    def test_fabricated_source_anchor_fails_closed_without_surface_authority(self):
        payload = valid_payload()
        payload["source_anchors"] = ["不存在的原文"]
        text = "明天要考試。"
        candidate = uapm.build_literal_topic_projection_candidate_m29(
            text,
            unlinked_feedback(),
            pragmatic_for(text),
        )
        plan, contract = brain_runtime.LeftBrain(_Client(payload)).project_literal_topic_m29(
            text,
            candidate,
        )

        self.assertIsNone(plan)
        self.assertEqual(contract["status"], "projection_rejected")
        self.assertFalse(contract["surface_authority"])
        self.assertFalse(contract["validation_checks"]["source_anchor_exact_match"])

    def test_formal_trailing_sentence_is_removed_only_when_all_anchors_remain(self):
        payload = valid_payload()
        payload["response_jp"] = "明日試験なんだ。今日は早く寝ておきなさい。"
        text = "明天要考試。"
        candidate = uapm.build_literal_topic_projection_candidate_m29(
            text,
            unlinked_feedback(),
            pragmatic_for(text),
        )

        plan, contract = brain_runtime.LeftBrain(_Client(payload)).project_literal_topic_m29(
            text,
            candidate,
        )

        self.assertEqual(contract["status"], "projected_and_validated")
        self.assertEqual(contract["response_jp"], "明日試験なんだ。")
        self.assertTrue(contract["surface_register_sanitized"])
        self.assertTrue(contract["validation_checks"]["casual_register_only"])
        self.assertEqual(plan["core_message_jp"], "明日試験なんだ。")

    def test_generic_understanding_prefix_is_removed_before_surface_authority(self):
        payload = valid_payload()
        payload["response_jp"] = "了解だ。明日試験なんだ。"
        text = "明天要考試。"
        candidate = uapm.build_literal_topic_projection_candidate_m29(
            text,
            unlinked_feedback(),
            pragmatic_for(text),
        )

        plan, contract = brain_runtime.LeftBrain(_Client(payload)).project_literal_topic_m29(
            text,
            candidate,
        )

        self.assertEqual(contract["status"], "projected_and_validated")
        self.assertEqual(contract["response_jp"], "明日試験なんだ。")
        self.assertTrue(contract["surface_register_sanitized"])
        self.assertEqual(plan["core_message_jp"], "明日試験なんだ。")

    def test_protected_plan_retains_priority_over_even_a_valid_projection(self):
        projection = {
            "schema": uapm.LITERAL_TOPIC_PROJECTION_SCHEMA_M29,
            "status": "projected_and_validated",
            "surface_authority": True,
            "response_jp": "明日試験なんだ。",
            "surface_anchors_jp": ["試験"],
            "raw_dialogue_persisted": False,
        }
        plan, contract = uapm.apply_literal_topic_projection_m29(
            {
                "intent": "crisis_support",
                "scene": "crisis",
                "core_message_jp": "今は一人になるな。",
            },
            projection,
        )

        self.assertEqual(contract["status"], "protected_current_turn_retained")
        self.assertFalse(contract["surface_authority"])
        self.assertEqual(plan["core_message_jp"], "今は一人になるな。")

    def test_real_runtime_contract_graph_and_compact_payload(self):
        brain = _IsolatedContractBrain()

        def project(_text, candidate):
            contract = {
                **candidate,
                "status": "projected_and_validated",
                "reason": "isolated_valid_projection_fixture",
                "surface_authority": True,
                "source_language": "zh",
                "source_anchor_count": 2,
                "source_anchor_digests": ["a1", "a2"],
                "subject_jp": "明日の試験",
                "predicate_jp": "ある",
                "time_jp": "明日",
                "polarity": "affirmed",
                "literal_summary_jp": "ユーザーは明日試験があると言っている。",
                "surface_anchors_jp": ["明日", "試験"],
                "response_jp": "明日試験なんだ。今日は詰め込みすぎんなよ。",
                "confidence": 0.91,
                "validation_checks": {"isolated_fixture": True},
                "generalized_without_topic_phrase_inventory": True,
                "suppresses_new_pending_prediction": True,
                "raw_dialogue_persisted": False,
            }
            plan = {
                "intent": "grounded_literal_topic_m29",
                "scene": "casual",
                "reply_goal": "現在の字面に返す",
                "jp_summary": contract["literal_summary_jp"],
                "core_message_jp": contract["response_jp"],
                "response_mode": "grounded_literal_topic_response",
                "surface_act": "grounded_literal_topic_m29",
                "constraints": {"max_chars": 96},
                "mood_impact": 0,
                "trust_impact": 0,
            }
            return plan, contract

        brain.left_brain.project_literal_topic_m29 = project
        brain.run_turn_debug(AMBIGUOUS_INPUT)
        brain.run_turn_debug(PRACTICAL_CORRECTION)
        brain.run_turn_debug(REPEATED_AMBIGUOUS)
        result = brain.run_turn_debug("明天要考試。")
        contract = result["runtime_trace"]["literal_topic_projection_m29"]

        self.assertEqual(
            result["reply"],
            "明日試験なんだ。今日は詰め込みすぎんなよ。",
        )
        self.assertEqual(contract["status"], "projected_and_validated")
        self.assertEqual(contract["surface_status"], "matched")
        self.assertEqual(contract["surface_anchor_status"], "matched")
        self.assertEqual(contract["visible_anchor_count"], 2)
        self.assertEqual(
            result["runtime_trace"]["adaptive_person_feedback_m18"]
            ["causal_outcome_calibration_m27"]["status"],
            "resolved_unknown_excluded",
        )
        self.assertIsNone(brain.runtime.adaptive_person_model.get("pending_prediction"))

        rendered = {
            "user_text": "isolated",
            "reply": result["reply"],
            "memory_data": result["memory_data"],
            "runtime_trace": result["runtime_trace"],
            "runtime_state": result["runtime_state"],
        }
        graph = collect_cognitive_graph(rendered)
        html = render_memory_observatory(rendered)
        labels = {node["label"] for node in graph["nodes"]}
        self.assertIn("literal_topic_projection_m29", labels)
        self.assertIn("literal_topic_surface_m29", labels)
        self.assertIn("GENERALIZED LITERAL-TOPIC GROUNDING &amp; TRANSLATION · M29", html)
        self.assertIn("subject 明日の試験", html)
        self.assertTrue(graph["payload_budget_m24"]["budget_met"])

        compact = web._client_cognition_payload_m24(
            {"runtime_trace": result["runtime_trace"]}
        )
        self.assertIn("literal_topic_projection_m29", compact["runtime_trace"])
        self.assertNotIn(
            "明天要考試。",
            json.dumps(contract, ensure_ascii=False),
        )


if __name__ == "__main__":
    unittest.main()
