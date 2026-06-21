import unittest
from types import SimpleNamespace

from uruha_brain_mac import LeftBrain, MemoryManager, UruhaBrainV4_Mac
from uruha_runtime import RuntimeState


class TestPlannerSelfCorrection(unittest.TestCase):
    def setUp(self):
        self.left = LeftBrain(client_logic=None)
        self.psyche = {"mood": 0, "trust": 50}
        self.memory = {"working_memory_items": []}

    def test_final_tick_applies_safe_repair_instead_of_emitting_known_issue(self):
        seed = self.left._fallback_plan()
        seed.update(
            {
                "intent": "chat",
                "scene": "casual",
                "response_mode": "direct_answer",
                "surface_act": "plain_reply",
                "payload_level": "low",
                "core_message_jp": "軽く返す",
            }
        )
        candidates = self.left._derive_bayesian_candidates(seed, "今何してる？", self.psyche, self.memory)

        result = self.left._run_multitick_planner(
            candidates,
            "今何してる？",
            self.memory,
            self.psyche,
            tick_budget=1,
        )

        self.assertTrue(result["self_correction_applied"])
        self.assertTrue(result["planner_repair_applied"])
        self.assertTrue(result["planner_repair_success"])
        self.assertIn("too_flat", result["planner_detected_issues"])
        self.assertEqual(result["planner_unresolved_issues"], [])
        self.assertEqual(result["surface_act"], "status_reply")
        self.assertEqual(result["payload_level"], "medium")
        self.assertEqual(result["planner_tick_trace"][-1]["resolution"], "final_tick_repair")
        self.assertEqual(len(result["bayes_candidates"]), 3)

    def test_clean_plan_does_not_trigger_unnecessary_repair(self):
        seed = self.left._fallback_plan()
        seed.update(
            {
                "intent": "what_are_you_doing",
                "scene": "casual",
                "response_mode": "direct_answer",
                "surface_act": "status_reply",
                "payload_level": "medium",
                "core_message_jp": "今は少し休んでる",
            }
        )
        candidates = self.left._derive_bayesian_candidates(seed, "今何してる？", self.psyche, self.memory)

        result = self.left._run_multitick_planner(
            candidates,
            "今何してる？",
            self.memory,
            self.psyche,
            tick_budget=1,
        )

        self.assertFalse(result["self_correction_applied"])
        self.assertFalse(result["planner_repair_applied"])
        self.assertEqual(result["planner_detected_issues"], [])
        self.assertEqual(result["planner_unresolved_issues"], [])
        self.assertEqual(result["planner_tick_trace"][-1]["resolution"], "accepted")

    def test_false_premise_challenge_is_not_mistaken_for_overthinking(self):
        seed = self.left._fallback_plan()
        seed.update(
            {
                "intent": "premise_doubt",
                "hidden_intent": "premise_trap",
                "scene": "boundary",
                "response_mode": "premise_challenge",
                "premise_check": "reject",
                "surface_act": "plain_reply",
                "payload_level": "high",
                "user_belief": "相手は北海道で育ったという前提を置いている。",
                "user_expectation": "自然な返答。",
            }
        )

        critique = self.left._critique_plan(
            seed,
            "You grew up in Hokkaido, right?",
            self.memory,
            self.psyche,
        )

        self.assertNotIn("bdi_direct_miss", critique["issues"])
        self.assertNotIn("overthink_simple_query", critique["issues"])

    def test_short_false_premise_keeps_deliberate_challenge(self):
        seed = self.left._fallback_plan()
        seed.update(
            {
                "intent": "premise_doubt",
                "hidden_intent": "premise_trap",
                "scene": "boundary",
                "response_mode": "premise_challenge",
                "premise_check": "reject",
                "payload_level": "high",
            }
        )

        critique = self.left._critique_plan(
            seed,
            "你養過Shiro嗎",
            self.memory,
            self.psyche,
        )

        self.assertNotIn("overthink_simple_query", critique["issues"])
        self.assertNotIn("overchallenge_short_input", critique["issues"])

    def test_grounded_apology_repair_is_not_misread_as_scope_overload(self):
        seed = self.left._fallback_plan()
        seed.update(
            {
                "intent": "apology_repair",
                "scene": "casual",
                "response_mode": "direct_answer",
                "surface_act": "rephrase_plain",
                "grounding": {"apology_repair": True},
                "payload_level": "medium",
            }
        )

        critique = self.left._critique_plan(
            seed,
            "你剛才那個抱歉聽起來很敷衍，請認真再說一次。",
            self.memory,
            self.psyche,
        )

        self.assertNotIn("scope_too_open", critique["issues"])

    def test_apology_repair_normalization_keeps_trace_cognitively_consistent(self):
        seed = self.left._fallback_plan()
        seed.update(
            {
                "intent": "apology_repair",
                "hidden_intent": "scope_overload",
                "user_belief": "広い問いだ。",
                "my_hidden_knowledge": "範囲を絞らせる。",
                "user_expectation": "万能解。",
                "internal_monologue": "論点が多すぎる。",
            }
        )

        normalized = self.left._normalize_plan(seed)

        self.assertEqual(normalized["hidden_intent"], "plain_request")
        self.assertIn("冷た", normalized["user_belief"])
        self.assertIn("謝り直す", normalized["my_hidden_knowledge"])
        self.assertIn("repair,apology", normalized["internal_monologue"])

    def test_grounded_withdrawal_is_not_misread_as_scope_overload(self):
        seed = self.left._fallback_plan()
        seed.update(
            {
                "intent": "anxious_support",
                "scene": "support",
                "response_mode": "direct_answer",
                "surface_act": "protective_brake",
                "grounding": {
                    "withdrawal_risk": "high",
                    "withdrawal_kind": "erase_trace",
                },
                "payload_level": "medium",
            }
        )

        critique = self.left._critique_plan(
            seed,
            "我想把聊天全部清掉，不想留下痕跡。",
            self.memory,
            self.psyche,
        )

        self.assertNotIn("scope_too_open", critique["issues"])

    def test_self_monitor_allows_explicitly_grounded_ascii_name(self):
        brain = object.__new__(UruhaBrainV4_Mac)
        brain.memory = SimpleNamespace(session_turns=[])
        brain.runtime = RuntimeState()
        logic = {
            "grounding": {"profile_name": "Jerry"},
            "payload_level": "medium",
            "scene": "casual",
            "human_speech_plan": {
                "dialogue_act": "profile_update_ack",
                "content_units": ["呼び方を受け取る", "覚えておく"],
                "content_density_target": "medium",
                "grounding_terms": ["Jerry"],
                "turn_opening_potential": False,
            },
        }

        monitor = brain._self_monitor_reply(
            "Call me Jerry.",
            "Jerryって呼べばいいんだろ。覚えとく。",
            logic,
            {"profile_structured": {"name": "Jerry"}},
        )

        self.assertNotIn("non_japanese_leak", monitor["issues"])

    def test_self_monitor_still_rejects_ungrounded_english_fragment(self):
        brain = object.__new__(UruhaBrainV4_Mac)
        brain.memory = SimpleNamespace(session_turns=[])
        brain.runtime = RuntimeState()
        logic = {
            "grounding": {},
            "payload_level": "medium",
            "scene": "casual",
            "human_speech_plan": {
                "dialogue_act": "plain_reply",
                "content_units": ["普通に返す", "短く返す"],
                "content_density_target": "medium",
                "grounding_terms": [],
                "turn_opening_potential": False,
            },
        }

        monitor = brain._self_monitor_reply(
            "普通に返して",
            "just answer でいいだろ。",
            logic,
            {},
        )

        self.assertIn("non_japanese_leak", monitor["issues"])

    def test_density_repair_preserves_semantic_core_instead_of_plan_instructions(self):
        class FakeRightBrain:
            def __init__(self):
                self.received_logic = None

            def speak(self, _user_input, logic, _memory_data, _psyche_after):
                self.received_logic = logic
                return logic["core_message_jp"]

            def _refine_conversational_reply(self, reply, _logic, _user_input, _memory_data):
                return reply

        brain = object.__new__(UruhaBrainV4_Mac)
        brain.memory = SimpleNamespace(session_turns=[])
        brain.runtime = RuntimeState()
        brain.right_brain = FakeRightBrain()
        logic = {
            "core_message_jp": "その前提どこから出たんだよ",
            "payload_level": "high",
            "constraints": {"sentence_count": 2, "max_chars": 40},
            "human_speech_plan": {
                "dialogue_act": "premise_challenge",
                "content_units": ["問いの前提を止める", "次に絞る場所を示す"],
                "grounding_terms": [],
                "forbidden_repetition": [],
            },
        }

        repaired = brain._repair_reply_from_self_monitor(
            "薄い返事",
            logic,
            {"issues": ["low_speech_content_density"], "needs_repair": True},
            "You grew up in Hokkaido, right?",
            {},
            self.psyche,
        )

        self.assertEqual(brain.right_brain.received_logic["core_message_jp"], "その前提どこから出たんだよ")
        self.assertEqual(repaired, "その前提どこから出たんだよ")

    def test_memory_profile_capture_uses_same_name_speech_act_boundary(self):
        memory = object.__new__(MemoryManager)

        self.assertIn(("name", "Jerry"), memory._extract_profile_facts("Call me Jerry."))
        self.assertNotIn(("name", "Jerry"), memory._extract_profile_facts("Why did you call me Jerry?"))


if __name__ == "__main__":
    unittest.main()
