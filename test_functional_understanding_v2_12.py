import json
import os
import re
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ["URUHA_SKIP_AUTO_VENV"] = "1"
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

import uruha_functional_understanding as ufu
from uruha_memory_observatory import collect_cognitive_graph, render_memory_observatory
from uruha_runtime import RuntimeState


class FunctionalUnderstandingV212UnitTests(unittest.TestCase):
    def test_hypothesis_separates_known_inferred_unknown_and_alternatives(self):
        hypothesis = ufu.build_user_mental_state_hypothesis(
            "今天心情怪怪的",
            {"actual_intent": "chat", "actual_scene": "casual"},
            turn_index=1,
        )

        self.assertEqual(hypothesis["schema"], ufu.SCHEMA)
        self.assertEqual(hypothesis["epistemic_status"], "provisional_inference")
        self.assertEqual(hypothesis["known"][0]["epistemic_status"], "known_observation")
        self.assertEqual(hypothesis["inferred"]["possible_intent"]["epistemic_status"], "inferred")
        self.assertTrue(all(item["epistemic_status"] == "unknown" for item in hypothesis["unknown"]))
        self.assertGreaterEqual(len(hypothesis["alternative_hypotheses"]), 2)
        self.assertEqual(hypothesis["memory_policy"]["storage_scope"], "runtime_trace_only")
        self.assertFalse(hypothesis["memory_policy"]["fact_write_allowed"])
        self.assertEqual(hypothesis["prediction"]["epistemic_status"], "prediction")

    def test_next_turn_can_support_prediction_and_calibrate_slightly_up(self):
        first = ufu.build_user_mental_state_hypothesis(
            "我今天很累，可能要休息了",
            {"actual_intent": "tired_support", "actual_scene": "support"},
            turn_index=1,
        )
        outcome = ufu.verify_previous_hypothesis(
            first,
            "嗯，我先去睡了",
            {"actual_intent": "farewell"},
            turn_index=2,
        )
        calibration = ufu.update_calibration({}, outcome)

        self.assertEqual(outcome["status"], "supported")
        self.assertEqual(outcome["prediction_error"], 0.0)
        self.assertEqual(calibration["supported"], 1)
        self.assertEqual(calibration["last_adjustment"], 0.03)

    def test_next_turn_can_contradict_and_preserve_the_original_hypothesis(self):
        first = ufu.build_user_mental_state_hypothesis(
            "今天心情怪怪的",
            {"actual_intent": "chat", "actual_scene": "casual"},
            turn_index=1,
        )
        original_emotion = first["inferred"]["emotion_or_need"]["value"]
        outcome = ufu.verify_previous_hypothesis(
            first,
            "不是難過，我只是太興奮了",
            {"actual_intent": "correction_followup"},
            turn_index=2,
        )
        calibration = ufu.update_calibration({}, outcome)
        repaired = ufu.build_user_mental_state_hypothesis(
            "不是難過，我只是太興奮了",
            {"actual_intent": "correction_followup", "actual_scene": "casual"},
            turn_index=2,
            calibration_state=calibration,
        )

        self.assertEqual(outcome["status"], "contradicted")
        self.assertEqual(outcome["prediction_error"], 1.0)
        self.assertEqual(
            outcome["previous_hypothesis_snapshot"]["inferred"]["emotion_or_need"]["value"],
            original_emotion,
        )
        self.assertIn("興奮", repaired["inferred"]["emotion_or_need"]["value"])
        self.assertEqual(calibration["last_adjustment"], -0.1)
        self.assertLess(calibration["confidence_multiplier"], 1.0)

    def test_high_uncertainty_changes_planning_to_low_pressure_japanese_clarification(self):
        hypothesis = ufu.build_user_mental_state_hypothesis(
            "你知道吧",
            {"actual_intent": "chat", "actual_scene": "casual"},
            turn_index=1,
        )
        plan = ufu.apply_hypothesis_to_plan(
            {"intent": "chat", "scene": "casual", "constraints": {"max_chars": 28}},
            hypothesis,
            {"actual_intent": "chat", "actual_scene": "casual"},
        )

        self.assertGreaterEqual(hypothesis["uncertainty"], ufu.HIGH_UNCERTAINTY_THRESHOLD)
        self.assertEqual(plan["intent"], "functional_understanding_clarify")
        self.assertEqual(plan["response_mode"], "clarify_light")
        self.assertEqual(
            plan["functional_understanding_strategy"]["reason"],
            "high_uncertainty_do_not_pretend_to_know_user_mind",
        )
        self.assertRegex(plan["core_message_jp"], r"[ぁ-んァ-ヶー一-龠]")
        self.assertNotRegex(plan["core_message_jp"], r"[A-Za-z]")

    def test_safety_and_identity_direct_responses_are_not_replaced_by_clarification(self):
        for user_input, intent, scene in [
            ("你是誰？", "self_intro", "casual"),
            ("我不想活了", "crisis_support", "support"),
        ]:
            with self.subTest(intent=intent):
                hypothesis = ufu.build_user_mental_state_hypothesis(
                    user_input,
                    {"actual_intent": intent, "actual_scene": scene},
                    turn_index=1,
                )
                plan = ufu.apply_hypothesis_to_plan(
                    {"intent": intent, "scene": scene},
                    hypothesis,
                    {"actual_intent": intent, "actual_scene": scene},
                )
                self.assertEqual(plan["intent"], intent)
                self.assertTrue(plan["functional_understanding_strategy"]["protected_direct_response"])


class FunctionalUnderstandingV212RuntimeContractTests(unittest.TestCase):
    def test_runtime_history_appends_verification_without_overwriting_old_guess(self):
        runtime = RuntimeState()
        first = ufu.build_user_mental_state_hypothesis(
            "今天心情怪怪的", {"actual_intent": "chat"}, turn_index=1
        )
        runtime.remember_user_hypothesis(first)
        outcome = ufu.verify_previous_hypothesis(
            first,
            "不是難過，我只是太興奮了",
            {"actual_intent": "correction_followup"},
            turn_index=2,
        )
        runtime.remember_hypothesis_verification(outcome)

        record = runtime.hypothesis_history[0]
        self.assertEqual(record["hypothesis"], first)
        self.assertEqual(record["verification_after_next_turn"]["status"], "contradicted")
        self.assertEqual(
            record["verification_after_next_turn"]["update_policy"],
            "retain_original_append_verification_and_rebuild_current_hypothesis",
        )

    def _graph_fixture(self):
        hypothesis = ufu.build_user_mental_state_hypothesis(
            "不是難過，我只是太興奮了",
            {"actual_intent": "correction_followup"},
            turn_index=2,
        )
        previous = ufu.build_user_mental_state_hypothesis(
            "今天心情怪怪的", {"actual_intent": "chat"}, turn_index=1
        )
        outcome = ufu.verify_previous_hypothesis(
            previous,
            "不是難過，我只是太興奮了",
            {"actual_intent": "correction_followup"},
            turn_index=2,
        )
        calibration = ufu.update_calibration({}, outcome)
        return {
            "user_text": "不是難過，我只是太興奮了",
            "reply": "あ、そっちか。落ち込んでるんじゃなくて興奮してたのか。",
            "memory_data": {},
            "runtime_trace": {
                "blackboard": [
                    {"stage": "perception", "label": "actual_signal", "payload": {"actual_intent": "correction_followup"}},
                    {"stage": "verify", "label": "hypothesis_outcome_verification", "payload": outcome},
                    {"stage": "calibrate", "label": "hypothesis_calibration_update", "payload": calibration},
                    {"stage": "hypothesis", "label": "user_mental_state_hypothesis", "payload": hypothesis},
                    {
                        "stage": "evidence",
                        "label": "hypothesis_evidence",
                        "payload": {
                            "hypothesis_id": hypothesis["hypothesis_id"],
                            "known": hypothesis["known"],
                            "evidence": hypothesis["evidence"],
                            "unknown": hypothesis["unknown"],
                        },
                    },
                    {"stage": "predict", "label": "next_user_prediction_v2_12", "payload": hypothesis["prediction"]},
                    {"stage": "select", "label": "selected_plan", "payload": {"intent": "correction_followup"}},
                    {"stage": "surface", "label": "utterance", "payload": {"reply": "あ、そっちか。"}},
                ],
                "state_diff": {},
                "memory_writes": [],
            },
        }

    def test_node_graph_exposes_full_functional_understanding_flow_and_correction(self):
        graph = collect_cognitive_graph(self._graph_fixture())
        labels = {node["label"] for node in graph["nodes"]}
        self.assertTrue(
            {
                "hypothesis_outcome_verification",
                "hypothesis_calibration_update",
                "user_mental_state_hypothesis",
                "hypothesis_evidence",
                "next_user_prediction_v2_12",
            }.issubset(labels)
        )
        self.assertGreaterEqual(
            sum(edge["class"] == "is-understanding" for edge in graph["edges"]),
            5,
        )
        verification_node = next(
            node for node in graph["nodes"] if node["label"] == "hypothesis_outcome_verification"
        )
        self.assertIn("contradicted", verification_node["signal"])
        self.assertIn("previous_hypothesis_snapshot", verification_node["detail"])

    def test_product_visual_makes_the_adaptive_difference_visible(self):
        html = render_memory_observatory(self._graph_fixture())
        self.assertIn("DIRECT GENERATION PATH", html)
        self.assertIn("當輪輸入 → 當輪回答", html)
        self.assertIn("HIERARCHICAL ADAPTIVE MODEL · M18", html)
        self.assertIn("負遷移檢查", html)
        self.assertIn("hypothesis_outcome_verification", html)

    def test_provisional_hypothesis_is_not_a_fact_memory_payload(self):
        hypothesis = ufu.build_user_mental_state_hypothesis(
            "你知道吧", {"actual_intent": "chat"}, turn_index=1
        )
        runtime_payload = json.dumps(hypothesis, ensure_ascii=False)
        self.assertIn("runtime_trace_only", runtime_payload)
        self.assertNotIn('"fact_write_allowed": true', runtime_payload.lower())


if __name__ == "__main__":
    unittest.main()
