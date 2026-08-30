import json
import unittest

import uruha_adaptive_person_model as uapm
from test_adaptive_person_model_m16 import AMBIGUOUS_INPUT, TEASE_FEEDBACK, decision_for
from test_personhood_loop_v2_13 import _IsolatedContractBrain
from uruha_memory_observatory import collect_cognitive_graph, render_memory_observatory


PRACTICAL_CORRECTION = "不是要吐槽，是真的想要一個現在能做的方法。"


class DesiredResponseModeM23Tests(unittest.TestCase):
    def test_ambiguous_bid_exposes_six_modes_and_selects_low_pressure_clarification(self):
        state, decision = decision_for(AMBIGUOUS_INPUT, uapm.empty_model(), 1)
        contract = uapm.build_desired_response_mode_contract(
            {"selected_type": "emotional_bid"},
            state,
            decision,
        )

        self.assertTrue(contract["eligible"])
        self.assertEqual(contract["selected_mode"], "low_pressure_clarification")
        self.assertEqual(contract["authority"], "uncertainty_guarded_clarification")
        self.assertEqual(contract["uncertainty_band"], "high")
        self.assertTrue(contract["uncertainty_guard_passed"])
        self.assertEqual(
            {row["mode"] for row in contract["alternatives"]},
            set(uapm.POLICY_TO_RESPONSE_MODE_M23.values()),
        )
        raw = json.dumps(contract, ensure_ascii=False)
        self.assertNotIn(AMBIGUOUS_INPUT, raw)
        self.assertFalse(contract["raw_dialogue_persisted"])
        self.assertEqual(state["production_memory_write_count"], 0)

    def test_selected_mode_forces_the_real_japanese_surface(self):
        state, decision = decision_for(AMBIGUOUS_INPUT, uapm.empty_model(), 1)
        contract = uapm.build_desired_response_mode_contract(
            {"selected_type": "emotional_bid"},
            state,
            decision,
        )
        plan, _trace = uapm.apply_decision_to_plan(
            {"intent": "chat", "scene": "casual", "core_message_jp": "別の返事"},
            decision,
        )
        plan["desired_response_mode_m23"] = contract

        reply, performed = uapm.ensure_desired_response_mode_reaches_surface(
            "文字通りの返事だけ。",
            plan,
        )

        self.assertEqual(reply, decision["selected"]["core_message_jp"])
        self.assertEqual(performed["performed_mode"], "low_pressure_clarification")
        self.assertEqual(performed["surface_status"], "matched")
        self.assertTrue(performed["surface_changed"])

    def test_four_real_runtime_turns_repair_causal_scope_and_reuse_latest_mode(self):
        brain = _IsolatedContractBrain()
        first = brain.run_turn_debug(AMBIGUOUS_INPUT)
        tease = brain.run_turn_debug(TEASE_FEEDBACK)
        practical = brain.run_turn_debug(PRACTICAL_CORRECTION)
        repeated = brain.run_turn_debug("我今天又從早上就一直坐不住，腦子停不下來。")

        first_mode = first["runtime_trace"]["desired_response_mode_m23"]
        tease_mode = tease["runtime_trace"]["desired_response_mode_m23"]
        practical_mode = practical["runtime_trace"]["desired_response_mode_m23"]
        repeated_mode = repeated["runtime_trace"]["desired_response_mode_m23"]
        self.assertEqual(first_mode["selected_mode"], "low_pressure_clarification")
        self.assertEqual(tease_mode["selected_mode"], "playful_tease")
        self.assertEqual(tease_mode["revoked_previous_policy"], "calibrate_need")
        self.assertEqual(practical_mode["selected_mode"], "practical_help")
        self.assertEqual(practical_mode["revoked_previous_policy"], "playful_tease")
        self.assertTrue(
            practical["runtime_trace"]["adaptive_person_feedback_m18"][
                "causal_scope_repairs_m23"
            ]
        )
        self.assertEqual(repeated_mode["selected_mode"], "practical_help")
        self.assertEqual(repeated_mode["authority"], "verified_reversible_preference")
        self.assertEqual(
            {
                first_mode["surface_status"],
                tease_mode["surface_status"],
                practical_mode["surface_status"],
                repeated_mode["surface_status"],
            },
            {"matched"},
        )
        self.assertIn("どっち", first["reply"])
        self.assertIn("二十四時間営業", tease["reply"])
        self.assertIn("今すぐできる", practical["reply"])
        self.assertNotIn("どっち", practical["reply"])
        self.assertNotIn("延長戦", repeated["reply"])
        self.assertNotIn("二十四時間営業", repeated["reply"])
        self.assertRegex(repeated["reply"], r"メモ|五分|一個")
        labels = {row["label"] for row in practical["runtime_trace"]["blackboard"]}
        self.assertIn("desired_response_mode_m23", labels)
        self.assertIn("desired_response_surface_contract_m23", labels)

    def test_non_emotional_task_shape_cannot_override_deliberation(self):
        state, decision = decision_for(AMBIGUOUS_INPUT, uapm.empty_model(), 1)
        contract = uapm.build_desired_response_mode_contract(
            {"selected_type": "deliberation"},
            state,
            decision,
        )
        plan, _trace = uapm.apply_decision_to_plan(
            {"intent": "deliberation", "scene": "casual", "core_message_jp": "比較する。"},
            decision,
        )
        plan["desired_response_mode_m23"] = contract

        reply, performed = uapm.ensure_desired_response_mode_reaches_surface(
            "まず条件を整理しよ。",
            plan,
        )

        self.assertFalse(contract["eligible"])
        self.assertEqual(reply, "まず条件を整理しよ。")
        self.assertEqual(performed["surface_status"], "not_applicable")

    def test_graph_shows_mode_evidence_authority_alternatives_and_surface_contract(self):
        mode = {
            "schema": uapm.DESIRED_RESPONSE_MODE_SCHEMA,
            "eligible": True,
            "selected_mode": "playful_tease",
            "authority": "current_explicit_correction",
            "uncertainty": 0.06,
            "uncertainty_band": "low",
            "alternatives": [{"mode": mode} for mode in uapm.POLICY_TO_RESPONSE_MODE_M23.values()],
            "surface_status": "matched",
            "raw_dialogue_persisted": False,
        }
        result = {
            "user_text": "holdout",
            "reply": "朝から脳内だけ二十四時間営業かよ。",
            "runtime_trace": {
                "desired_response_mode_m23": mode,
                "blackboard": [
                    {"stage": "select", "label": "desired_response_mode_m23", "payload": mode},
                    {"stage": "surface", "label": "desired_response_surface_contract_m23", "payload": mode},
                ],
            },
        }

        graph = collect_cognitive_graph(result)
        html = render_memory_observatory(result)
        labels = {node["label"] for node in graph["nodes"]}
        self.assertIn("desired_response_mode_m23", labels)
        self.assertIn("desired_response_surface_contract_m23", labels)
        self.assertIn("DESIRED RESPONSE MODE · M23", html)
        self.assertIn("mode playful_tease", html)
        self.assertIn("authority current_explicit_correction", html)
        self.assertIn("alternatives 6", html)
        self.assertIn("surface matched", html)


if __name__ == "__main__":
    unittest.main()
