import json
import unittest

import uruha_brain_mac as brain_runtime
from test_personhood_loop_v2_13 import _IsolatedContractBrain
from uruha_memory_observatory import collect_cognitive_graph, render_memory_observatory


class SemanticRouteTaxonomyM22Tests(unittest.TestCase):
    @staticmethod
    def classify(text, **overrides):
        inputs = {
            "actual_signal": {"actual_intent": "chat", "seed_plan": {"scene": "casual"}},
            "route_info": {"route": "high_road", "reason": "m22_test"},
        }
        inputs.update(overrides)
        return brain_runtime.UruhaBrainV4_Mac._classify_task_shape_m22(text, **inputs)

    def test_source_disjoint_multilingual_route_matrix(self):
        cases = (
            (
                "Could you let me know you're still with me on the line?",
                "explicit_presence",
                "bounded_simple",
            ),
            (
                "I need to compare several options before I decide which one matters most.",
                "deliberation",
                "full_planner",
            ),
            (
                "你還記得我剛才提過最喜歡的飲料嗎？",
                "factual_or_memory",
                "grounded",
            ),
            (
                "Please call me Jerry from now on.",
                "factual_or_memory",
                "grounded",
            ),
            (
                "That isn't what I meant—you misunderstood my request.",
                "explicit_correction",
                "correction_authority",
            ),
            (
                "今天一早就很混亂，我整個人坐不住。",
                "emotional_bid",
                "pragmatic_adaptive_or_full",
            ),
            (
                "いくつかの案から優先順位を決めたい。",
                "deliberation",
                "full_planner",
            ),
        )

        for text, expected_type, expected_route in cases:
            with self.subTest(text=text):
                trace = self.classify(text)
                self.assertEqual(trace["schema"], "uruha_semantic_route_taxonomy_m22")
                self.assertEqual(trace["selected_type"], expected_type)
                self.assertEqual(trace["recommended_route"], expected_route)
                self.assertGreaterEqual(trace["confidence"], 0.4)
                self.assertFalse(trace["raw_dialogue_persisted"])
                self.assertNotIn(text, json.dumps(trace, ensure_ascii=False))

    def test_overlap_negation_prevents_old_need_to_reason_collision(self):
        overlap = self.classify(
            "Don't reason through anything; just say you are here."
        )
        retained_regression = self.classify(
            "I have several conflicting goals and need to reason through them."
        )

        self.assertEqual(overlap["selected_type"], "explicit_presence")
        self.assertIn("deliberation", overlap["negated_types"])
        self.assertEqual(overlap["recommended_route"], "bounded_simple")
        self.assertEqual(retained_regression["selected_type"], "deliberation")
        self.assertEqual(retained_regression["recommended_route"], "full_planner")

    def test_protected_factual_and_correction_evidence_outrank_convenience(self):
        protected = self.classify(
            "Are you still here?",
            route_info={"route": "low_road", "reason": "acute_crisis"},
        )
        factual = self.classify(
            "Are you still here, and what did I say my name was?",
            grounded_profile_logic={"intent": "recall_name"},
        )
        correction = self.classify(
            "Are you still here? You misunderstood what I wanted.",
            correction_directive={"authoritative": True},
        )

        self.assertEqual(protected["selected_type"], "safety_sensitive")
        self.assertEqual(protected["recommended_route"], "protected")
        self.assertIn("explicit_presence", protected["overlap_types"])
        self.assertEqual(factual["selected_type"], "factual_or_memory")
        self.assertEqual(factual["recommended_route"], "grounded")
        self.assertEqual(correction["selected_type"], "explicit_correction")
        self.assertEqual(correction["recommended_route"], "correction_authority")

    def test_real_runtime_performs_bounded_and_full_contracts(self):
        presence_brain = _IsolatedContractBrain()
        presence = presence_brain.run_turn_debug(
            "Could you let me know you're still with me on the line?"
        )
        deliberation_brain = _IsolatedContractBrain()
        deliberation = deliberation_brain.run_turn_debug(
            "I need to compare several options before I decide which one matters most."
        )

        presence_trace = presence["runtime_trace"]["semantic_route_m22"]
        deliberation_trace = deliberation["runtime_trace"]["semantic_route_m22"]
        self.assertEqual(presence["reply"], "うん、ここにいるよ。")
        self.assertEqual(presence_trace["selected_type"], "explicit_presence")
        self.assertEqual(presence_trace["performed_route"], "bounded_simple_presence")
        self.assertEqual(presence_trace["contract_status"], "matched")
        self.assertEqual(presence_brain.left_brain.think_calls, 0)
        self.assertEqual(deliberation_trace["selected_type"], "deliberation")
        self.assertEqual(deliberation_trace["performed_route"], "full_planner")
        self.assertEqual(deliberation_trace["contract_status"], "matched")
        self.assertEqual(deliberation_brain.left_brain.think_calls, 1)
        self.assertRegex(deliberation["reply"], r"[ぁ-んァ-ヶー一-龠]")
        labels = {
            row["label"] for row in presence["runtime_trace"]["blackboard"]
        }
        self.assertIn("semantic_route_classifier_m22", labels)
        self.assertIn("semantic_route_outcome_m22", labels)

    def test_explicit_profile_update_suppresses_unrelated_active_validation(self):
        brain = _IsolatedContractBrain()
        brain.run_turn_debug("Don't reason through anything; just say you are here.")
        result = brain.run_turn_debug("Please call me Jerry from now on.")

        semantic = result["runtime_trace"]["semantic_route_m22"]
        validation = result["logic"]["active_validation_strategy_v2_13"]
        self.assertEqual(semantic["selected_type"], "factual_or_memory")
        self.assertEqual(semantic["contract_status"], "matched")
        self.assertFalse(validation["changed_plan"])
        self.assertEqual(
            validation["direct_user_report"]["kind"],
            "current_name_update",
        )
        self.assertNotIn("放っといて", result["reply"])

    def test_typed_name_recall_bridges_exact_structured_profile_evidence(self):
        task_shape = self.classify("你還記得我剛才說要怎麼稱呼我嗎？")
        plan, trace = brain_runtime.UruhaBrainV4_Mac._build_typed_factual_plan_m22(
            "你還記得我剛才說要怎麼稱呼我嗎？",
            {"profile_structured": {"name": "Jerry"}},
            task_shape,
        )

        self.assertTrue(trace["applied"])
        self.assertEqual(trace["evidence_source"], "typed_session_profile")
        self.assertNotIn("你還記得", json.dumps(trace, ensure_ascii=False))
        self.assertEqual(plan["intent"], "recall_profile_grounded")
        self.assertEqual(plan["routing_path"], "high_road_m22_typed_grounded")
        self.assertIn("Jerry", json.dumps(plan, ensure_ascii=False))
        self.assertEqual(
            plan["profile_evidence_contract"]["value"],
            "Jerry",
        )

    def test_graph_card_exposes_type_overlap_route_and_contract(self):
        semantic = {
            "schema": "uruha_semantic_route_taxonomy_m22",
            "selected_type": "explicit_presence",
            "recommended_route": "bounded_simple",
            "performed_route": "bounded_simple_presence",
            "contract_status": "matched",
            "confidence": 0.9,
            "overlap_types": ["emotional_bid"],
            "negated_types": ["deliberation"],
            "raw_dialogue_persisted": False,
        }
        bounded = {
            "schema": "uruha_bounded_slow_path_planner_m21",
            "route": "bounded_simple_presence",
            "status": "completed_without_general_model",
            "budget_seconds": 8.0,
            "model_call_attempted": False,
            "budget_met": True,
            "stage_seconds": {"cognitive_total": 0.02},
        }
        result = {
            "user_text": "holdout",
            "reply": "うん、ここにいるよ。",
            "runtime_trace": {
                "semantic_route_m22": semantic,
                "bounded_slow_path_m21": bounded,
                "surface_delivery_m20": {
                    "schema": "uruha_lightweight_surface_delivery_m20",
                    "stream_chunk_count": 2,
                    "full_payload_update_count": 1,
                },
                "blackboard": [
                    {
                        "stage": "route",
                        "label": "semantic_route_classifier_m22",
                        "payload": semantic,
                    },
                    {
                        "stage": "plan",
                        "label": "bounded_slow_path_planner_m21",
                        "payload": bounded,
                    },
                ],
            },
        }

        graph = collect_cognitive_graph(result)
        html = render_memory_observatory(result)

        self.assertIn(
            "semantic_route_classifier_m22",
            {node["label"] for node in graph["nodes"]},
        )
        self.assertIn("TYPED SEMANTIC ROUTER · M22", html)
        self.assertIn("type explicit_presence → bounded_simple_presence", html)
        self.assertIn("contract matched", html)
        self.assertIn("overlaps 1", html)
        self.assertIn("negations 1", html)
        self.assertIn("BOUNDED SLOW-PATH PLANNER · M21", html)


if __name__ == "__main__":
    unittest.main()
