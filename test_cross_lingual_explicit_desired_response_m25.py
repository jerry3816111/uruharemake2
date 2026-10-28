import json
import unittest

import uruha_adaptive_person_model as uapm
from test_adaptive_person_model_m16 import decision_for
from test_personhood_loop_v2_13 import _IsolatedContractBrain
from uruha_memory_observatory import collect_cognitive_graph, render_memory_observatory


class CrossLingualExplicitDesiredResponseM25Tests(unittest.TestCase):
    def test_chinese_english_and_japanese_requests_have_typed_current_authority(self):
        cases = {
            "今天先聽我說就好。": ("listen_presence", "listening", "zh"),
            "Just stay with me for a minute, okay?": ("share_arousal", "companionship", "en"),
            "今は質問しないで、そばにいて。": ("share_arousal", "companionship", "ja"),
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                contract = uapm.classify_explicit_desired_response_m25(text)
                self.assertTrue(contract["detected"])
                self.assertEqual(contract["selected_policy"], expected[0])
                self.assertEqual(contract["selected_mode"], expected[1])
                self.assertEqual(contract["matched_languages"], [expected[2]])
                self.assertEqual(contract["authority"], "current_explicit_desired_response")
                self.assertFalse(contract["raw_dialogue_persisted"])
                self.assertNotIn(text, json.dumps(contract, ensure_ascii=False))

    def test_negated_mode_is_removed_before_positive_mode_selection(self):
        cases = {
            "不要吐槽，告訴我現在能做的方法。": ("solve_regulation", "playful_tease"),
            "I do not want advice. Just listen to me.": ("listen_presence", "solve_regulation"),
            "質問しないで、そばにいて。": ("share_arousal", "calibrate_need"),
        }
        for text, (selected, blocked) in cases.items():
            with self.subTest(text=text):
                contract = uapm.classify_explicit_desired_response_m25(text)
                self.assertEqual(contract["selected_policy"], selected)
                self.assertIn(blocked, contract["negated_policies"])
                self.assertNotIn(
                    blocked,
                    {row["policy_id"] for row in contract["alternatives"]},
                )

    def test_current_explicit_request_overrides_an_opposed_ordinary_candidate(self):
        text = "I still cannot settle down. Just stay with me for a minute, okay?"
        state, _decision = decision_for(text, uapm.empty_model(), 1)
        for atom, value in {
            "solution_request": 0.99,
            "companionship_request": 0.01,
            "listening_request": 0.01,
            "positive_arousal": 0.01,
            "humor_invitation": 0.01,
        }.items():
            state["atoms"][atom]["value"] = value
            state["atoms"][atom]["confidence"] = 0.99

        decision = uapm.decide_response(state, uapm.empty_model())
        contract = decision["explicit_desired_response_m25"]

        self.assertEqual(contract["ordinary_selected_policy"], "solve_regulation")
        self.assertEqual(decision["selected"]["policy_id"], "share_arousal")
        self.assertTrue(contract["authoritative"])
        self.assertEqual(
            decision["selected"]["core_message_jp"],
            "うん。今は質問しないで、ちょっとここにいる。",
        )

    def test_real_runtime_executes_each_language_as_natural_japanese(self):
        cases = {
            "今天其實不想要方法了，你先聽我說就好。": ("listening", "方法出さない"),
            "I still cannot settle down. Just stay with me for a minute, okay?": ("companionship", "ここにいる"),
            "今は質問しないで、そばにいて。": ("companionship", "ここにいる"),
        }
        for text, (mode, reply_marker) in cases.items():
            with self.subTest(text=text):
                turn = _IsolatedContractBrain().run_turn_debug(text)
                m25 = turn["runtime_trace"]["explicit_desired_response_m25"]
                m23 = turn["runtime_trace"]["desired_response_mode_m23"]
                self.assertEqual(m25["performed_mode"], mode)
                self.assertEqual(m25["surface_status"], "matched")
                self.assertEqual(m23["selected_mode"], mode)
                self.assertEqual(m23["surface_status"], "matched")
                self.assertEqual(
                    turn["runtime_trace"]["bounded_slow_path_m21"]["route"],
                    "adaptive_fast_path_m18",
                )
                self.assertFalse(
                    turn["runtime_trace"]["bounded_slow_path_m21"][
                        "model_call_attempted"
                    ]
                )
                self.assertIn(reply_marker, turn["reply"])
                self.assertNotRegex(turn["reply"], r"[A-Za-z]{3,}")

    def test_protected_risk_cue_blocks_m25_surface_authority(self):
        text = "I want to die. Stay with me."
        contract = uapm.classify_explicit_desired_response_m25(text)
        state, decision = decision_for(text, uapm.empty_model(), 1)

        self.assertTrue(contract["detected"])
        self.assertTrue(contract["protected_risk_cue"])
        self.assertEqual(contract["authority"], "protected_risk_route")
        self.assertFalse(decision["explicit_desired_response_m25"]["authoritative"])
        self.assertFalse(decision["explicit_desired_response_m25"]["surface_required"])
        self.assertNotIn(
            "explicit_current_turn_desired_response_or_state_cue",
            state["activation_reasons"],
        )

    def test_graph_shows_m25_authority_negation_surface_and_m24_budget(self):
        turn = _IsolatedContractBrain().run_turn_debug(
            "I do not want advice. Just listen to me."
        )
        result = {
            "user_text": "holdout",
            "reply": turn["reply"],
            "memory_data": turn["memory_data"],
            "runtime_trace": turn["runtime_trace"],
            "runtime_state": turn["runtime_state"],
        }
        graph = collect_cognitive_graph(result)
        html = render_memory_observatory(result)
        labels = {node["label"] for node in graph["nodes"]}

        self.assertIn("explicit_desired_response_m25", labels)
        self.assertIn("explicit_desired_response_surface_m25", labels)
        self.assertIn("CROSS-LINGUAL EXPLICIT DESIRED RESPONSE · M25", html)
        self.assertIn("M25 explicit listening", html)
        self.assertIn("languages en", html)
        self.assertIn("negated 1", html)
        self.assertIn("surface matched", html)
        self.assertTrue(graph["payload_budget_m24"]["budget_met"])


if __name__ == "__main__":
    unittest.main()
