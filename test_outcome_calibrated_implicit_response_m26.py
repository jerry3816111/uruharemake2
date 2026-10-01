import json
import unittest

import uruha_adaptive_person_model as uapm
import uruha_web_ui as web
from test_adaptive_person_model_m16 import AMBIGUOUS_INPUT, decision_for
from test_personhood_loop_v2_13 import _IsolatedContractBrain
from uruha_memory_observatory import collect_cognitive_graph, render_memory_observatory


PRACTICAL_CORRECTION = "不是要吐槽，我是真的想要一個現在能做的方法。"
REPEATED_AMBIGUOUS = "我今天又從早上就一直坐不住，腦子停不下來。"


def gated_decision(text, model, turn_index, feedback=None):
    state, decision = decision_for(text, model, turn_index)
    contract = uapm.build_implicit_desired_response_distribution_m26(
        state,
        decision,
        adaptive_feedback=feedback,
    )
    decision = uapm.apply_implicit_response_gate_m26(state, decision, contract)
    return state, decision, decision["implicit_desired_response_m26"]


class OutcomeCalibratedImplicitResponseM26Tests(unittest.TestCase):
    def test_initial_ambiguous_turn_abstains_instead_of_claiming_understanding(self):
        state, decision, contract = gated_decision(
            AMBIGUOUS_INPUT,
            uapm.empty_model(),
            1,
        )

        self.assertEqual(contract["status"], "abstain_low_pressure_clarification")
        self.assertFalse(contract["execute_implicit"])
        self.assertEqual(decision["selected"]["policy_id"], "calibrate_need")
        self.assertGreater(contract["top_probability"], 0.40)
        self.assertFalse(contract["threshold_checks"]["non_clarifier_top"])
        self.assertEqual(
            contract["external_calibration_status"],
            "not_established_without_fresh_holdout",
        )
        self.assertEqual(state["production_memory_write_count"], 0)

    def test_verified_reversible_preference_passes_on_repeated_ambiguous_turn(self):
        model = uapm.empty_model()
        _state1, first, _contract1 = gated_decision(AMBIGUOUS_INPUT, model, 1)
        model = uapm.set_pending_prediction(model, first, 1)
        model, correction_feedback = uapm.observe_next_turn(
            model,
            PRACTICAL_CORRECTION,
            2,
        )
        _state2, corrected, explicit_contract = gated_decision(
            PRACTICAL_CORRECTION,
            model,
            2,
            correction_feedback,
        )
        self.assertEqual(explicit_contract["status"], "explicit_authority_bypass")
        model = uapm.set_pending_prediction(model, corrected, 2)
        model, unresolved = uapm.observe_next_turn(model, REPEATED_AMBIGUOUS, 3)
        state3, repeated, contract3 = gated_decision(
            REPEATED_AMBIGUOUS,
            model,
            3,
            unresolved,
        )

        self.assertEqual(contract3["status"], "execute_implicit")
        self.assertTrue(contract3["execute_implicit"])
        self.assertEqual(contract3["implicit_top_policy"], "solve_regulation")
        self.assertEqual(repeated["selected"]["policy_id"], "solve_regulation")
        self.assertIn("solution_request", contract3["learned_relevant_atoms"])
        self.assertIn("solution_request", state3["learned_atoms_used"])
        self.assertGreaterEqual(
            contract3["top_probability"], contract3["top_probability_threshold"]
        )
        self.assertGreaterEqual(
            contract3["probability_margin"], contract3["probability_margin_threshold"]
        )

    def test_near_tie_abstains_even_when_ordinary_utility_selected_action(self):
        state, decision = decision_for(
            "我需要一個現在能做的方法，怎麼停？",
            uapm.empty_model(),
            1,
        )
        decision["explicit_desired_response_m25"] = {}
        decision["correction_aware_surface_m20"] = {}
        for candidate in decision["candidates"]:
            candidate["expected_utility"] = 0.50
            candidate["learned_reliability"] = 0.50
            candidate["learned_evidence_count"] = 0
        contract = uapm.build_implicit_desired_response_distribution_m26(
            state,
            decision,
        )
        gated = uapm.apply_implicit_response_gate_m26(state, decision, contract)

        self.assertEqual(contract["status"], "abstain_low_pressure_clarification")
        self.assertLess(contract["probability_margin"], 0.20)
        self.assertEqual(gated["selected"]["policy_id"], "calibrate_need")
        self.assertTrue(gated["implicit_desired_response_m26"]["abstention_changed_policy"])

    def test_m25_explicit_current_request_bypasses_implicit_gate(self):
        text = "Just stay with me for a minute, okay?"
        state, decision, contract = gated_decision(text, uapm.empty_model(), 1)

        self.assertEqual(contract["status"], "explicit_authority_bypass")
        self.assertTrue(contract["explicit_authority_bypass"])
        self.assertFalse(contract["execute_implicit"])
        self.assertEqual(decision["selected"]["policy_id"], "share_arousal")
        self.assertEqual(
            decision["selected"]["core_message_jp"],
            "うん。今は質問しないで、ちょっとここにいる。",
        )
        self.assertFalse(state["production_memory_write_count"])

    def test_next_turn_outcome_records_support_contradiction_and_unknown(self):
        cases = [
            ("對就是這樣。", "supported", 1),
            # M38 intentionally fails closed when a rejection does not name a
            # unique replacement response.  It must not calibrate an arbitrary
            # previous policy as wrong from this targetless wording alone.
            ("你搞錯了，我不是要這個。", "uncertain", 0),
            ("今天外面下雨。", "uncertain", 0),
        ]
        for next_text, expected_status, delta_sign in cases:
            with self.subTest(status=expected_status):
                model = uapm.empty_model()
                _state, decision = decision_for(
                    "我需要一個現在能做的方法，怎麼停？",
                    model,
                    1,
                )
                model = uapm.set_pending_prediction(model, decision, 1)
                model, feedback = uapm.observe_next_turn(model, next_text, 2)
                state2, decision2 = decision_for(AMBIGUOUS_INPUT, model, 2)
                contract = uapm.build_implicit_desired_response_distribution_m26(
                    state2,
                    decision2,
                    adaptive_feedback=feedback,
                )
                outcome = contract["outcome_update"]

                self.assertEqual(outcome["status"], expected_status)
                if delta_sign > 0:
                    self.assertGreater(outcome["scoped_reliability_delta"], 0)
                elif delta_sign < 0:
                    self.assertLess(outcome["scoped_reliability_delta"], 0)
                else:
                    self.assertEqual(outcome["scoped_reliability_delta"], 0)
                self.assertNotIn(next_text, json.dumps(contract, ensure_ascii=False))
                self.assertFalse(contract["raw_dialogue_persisted"])

    def test_real_runtime_and_graph_show_distribution_gate_outcome_and_budget(self):
        brain = _IsolatedContractBrain()
        first = brain.run_turn_debug(AMBIGUOUS_INPUT)
        correction = brain.run_turn_debug(PRACTICAL_CORRECTION)
        repeated = brain.run_turn_debug(REPEATED_AMBIGUOUS)
        m26_first = first["runtime_trace"]["implicit_desired_response_m26"]
        m26_correction = correction["runtime_trace"]["implicit_desired_response_m26"]
        m26_repeated = repeated["runtime_trace"]["implicit_desired_response_m26"]

        self.assertEqual(m26_first["status"], "abstain_low_pressure_clarification")
        self.assertEqual(m26_correction["status"], "explicit_authority_bypass")
        self.assertEqual(m26_repeated["status"], "execute_implicit")
        self.assertEqual(repeated["logic"]["desired_response_policy_m18"], "solve_regulation")
        self.assertRegex(repeated["reply"], r"メモ|五分|一個")
        self.assertNotRegex(repeated["reply"], r"[A-Za-z]{3,}")

        result = {
            "user_text": "isolated",
            "reply": repeated["reply"],
            "memory_data": repeated["memory_data"],
            "runtime_trace": repeated["runtime_trace"],
            "runtime_state": repeated["runtime_state"],
        }
        graph = collect_cognitive_graph(result)
        html = render_memory_observatory(result)
        labels = {node["label"] for node in graph["nodes"]}
        self.assertIn("implicit_response_distribution_m26", labels)
        self.assertIn("implicit_desired_response_outcome_m26", labels)
        self.assertIn("OUTCOME-CALIBRATED IMPLICIT DESIRED RESPONSE · M26", html)
        self.assertIn("gate execute_implicit", html)
        self.assertIn("previous outcome uncertain", html)
        self.assertTrue(graph["payload_budget_m24"]["budget_met"])

        cognition = {"runtime_trace": repeated["runtime_trace"]}
        compact = web._client_cognition_payload_m24(cognition)
        self.assertIn("implicit_desired_response_m26", compact["runtime_trace"])
        self.assertTrue(compact["payload_budget_m24"]["budget_met"])


if __name__ == "__main__":
    unittest.main()
