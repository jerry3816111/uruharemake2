"""Zero-model, source-disjoint checks for the opt-in deterministic surface gate."""

from collections import Counter
from copy import deepcopy
from unittest import TestCase

from uruha_brain_mac import RightBrain
import uruha_deterministic_plan_leak_surface_p4 as guard
from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1


def logic(*, intent="short_confusion", route="low_road", selected="deterministic", third_party=False):
    return {
        "intent": intent,
        "routing_path": route,
        "surface_act": "plain_reply",
        "scene": "casual",
        "constraints": {"max_chars": 48},
        "core_message_jp": "短く聞き返す",
        "model_surface_selection": {
            "selected_source": selected,
            "selected_candidate": "短く聞き返す。そのくらいでいいだろ。",
        },
        "semantic_persona_surface_verifier_m39": {
            "source_frame": {"third_party_present": third_party}
        },
        "visible_language_guard": {
            "schema": "uruha_visible_language_guard_v1",
            "final_reply": "短く聞き返す。そのくらいでいいだろ。",
        },
    }


class DeterministicPlanLeakSurfaceTests(TestCase):
    def setUp(self):
        self.right = RightBrain.__new__(RightBrain)
        self.right.forbidden_conflict_projection_enabled = False
        self.leaked = "短く聞き返す。そのくらいでいいだろ。"
        self.source = "My cousin suddenly changed the stage ending."

    def test_existing_model_gate_identifies_deterministic_strategy_sentence(self):
        reasons = self.right._model_candidate_rejection_reasons(
            self.leaked, logic(), 48, user_input=self.source
        )
        self.assertIn("japanese_response_plan_leak", reasons)

    def test_third_party_report_becomes_actual_low_pressure_question(self):
        state = logic(third_party=True)
        visible = guard.guard_selected_deterministic_surface_p4(
            self.right, self.leaked, state, user_input=self.source
        )
        self.assertEqual(visible, "ん、そう聞いたのか。あんたはどう聞いてる？")
        self.assertNotIn("聞き返す", visible)
        self.assertEqual(state[guard.LABEL]["speech_act"], "ask_user_view_without_adopting_third_party_claim")
        self.assertEqual(state["visible_language_guard"]["final_reply"], visible)
        self.assertEqual(state["visible_language_guard"]["final_reply_sha256"], guard._sha(visible))
        self.assertFalse(state[guard.LABEL]["raw_dialogue_persisted"])
        self.assertFalse(state[guard.LABEL]["private_state_truth_claimed"])
        self.assertEqual(state[guard.LABEL]["model_calls_added"], 0)

    def test_other_surprise_gets_open_clarification_not_false_hearing_claim(self):
        state = logic(third_party=False)
        visible = guard.guard_selected_deterministic_surface_p4(
            self.right, self.leaked, state, user_input="急に予定が変わった。"
        )
        self.assertEqual(visible, "ん、そこもうちょい聞かせて。")
        self.assertNotIn("聞こえなかった", visible)

    def test_current_assistant_short_history_is_the_final_spoken_sentence(self):
        state = logic()
        self.right.history = [
            {"role": "user", "content": self.source, "intent": "short_confusion"},
            {"role": "assistant", "content": self.leaked, "intent": "short_confusion"},
        ]
        old_normalized = self.right._normalize_reply_key(self.leaked)
        self.right.reply_variant_counts = Counter({self.leaked: 1})
        self.right.intent_variant_counts = Counter({("short_confusion", self.leaked): 1})
        self.right.normalized_reply_counts = Counter({old_normalized: 1})
        self.right.intent_normalized_counts = Counter({("short_confusion", old_normalized): 1})
        visible = guard.guard_selected_deterministic_surface_p4(
            self.right, self.leaked, state, user_input=self.source
        )
        new_normalized = self.right._normalize_reply_key(visible)
        self.assertEqual(self.right.history[0]["content"], self.source)
        self.assertEqual(self.right.history[-1]["content"], visible)
        self.assertEqual(self.right.reply_variant_counts[self.leaked], 0)
        self.assertEqual(self.right.reply_variant_counts[visible], 1)
        self.assertEqual(self.right.intent_variant_counts[("short_confusion", visible)], 1)
        self.assertEqual(self.right.normalized_reply_counts[new_normalized], 1)
        self.assertEqual(self.right.intent_normalized_counts[("short_confusion", new_normalized)], 1)
        self.assertEqual(state[guard.LABEL]["short_history_sync_status"], "current_assistant_synced")

    def test_short_history_does_not_rewrite_unrelated_last_turn(self):
        state = logic()
        self.right.history = [{"role": "assistant", "content": "別の修正済みの句", "intent": "short_confusion"}]
        self.right.reply_variant_counts = Counter({"別の修正済みの句": 1})
        self.right.intent_variant_counts = Counter({("short_confusion", "別の修正済みの句"): 1})
        self.right.normalized_reply_counts = Counter()
        self.right.intent_normalized_counts = Counter()
        guard.guard_selected_deterministic_surface_p4(
            self.right, self.leaked, state, user_input=self.source
        )
        self.assertEqual(self.right.history[-1]["content"], "別の修正済みの句")
        self.assertEqual(state[guard.LABEL]["short_history_sync_status"], "current_assistant_mismatch")

    def test_protected_and_model_selected_controls_are_unchanged(self):
        for state in (
            logic(intent="crisis_support"),
            logic(intent="abuse_pushback"),
            logic(route="high_road"),
            logic(selected="model"),
        ):
            with self.subTest(state=(state["intent"], state["routing_path"], state["model_surface_selection"])):
                original = deepcopy(state)
                visible = guard.guard_selected_deterministic_surface_p4(
                    self.right, self.leaked, state, user_input=self.source
                )
                self.assertEqual(visible, self.leaked)
                self.assertEqual(state, original)

    def test_legitimate_reply_is_not_rewritten_when_user_quotes_strategy(self):
        state = logic(third_party=True)
        state["visible_language_guard"]["final_reply"] = "ん、そう聞いたのか。"
        visible = guard.guard_selected_deterministic_surface_p4(
            self.right, "ん、そう聞いたのか。", state,
            user_input="『短く聞き返す』って何の説明？",
        )
        self.assertEqual(visible, "ん、そう聞いたのか。")
        self.assertNotIn(guard.LABEL, state)

    def test_guard_mismatch_fails_closed(self):
        state = logic()
        state["visible_language_guard"]["final_reply"] = "別の句"
        with self.assertRaisesRegex(RuntimeError, "guard_trace_mismatch"):
            guard.guard_selected_deterministic_surface_p4(
                self.right, self.leaked, state, user_input=self.source
            )

    def test_replacement_must_pass_full_candidate_gate_including_length(self):
        state = logic()
        state["constraints"]["max_chars"] = 2
        with self.assertRaisesRegex(RuntimeError, "repair_not_visible_safe"):
            guard.guard_selected_deterministic_surface_p4(
                self.right, self.leaked, state, user_input=self.source
            )
        self.assertNotIn(guard.LABEL, state)
        self.assertEqual(state["visible_language_guard"]["final_reply"], self.leaked)

    def test_node_uses_digest_only_and_sits_before_utterance(self):
        state = logic(third_party=False)
        final = guard.guard_selected_deterministic_surface_p4(
            self.right, self.leaked, state, user_input=self.source
        )
        result = {
            "logic": state,
            "runtime_trace": {
                "blackboard": [
                    {"stage": "decision", "label": "selected_plan", "payload": {}},
                    {"stage": "surface", "label": "utterance", "payload": {"reply": final}},
                ]
            },
        }
        guard._append_node(result)
        rows = result["runtime_trace"]["blackboard"]
        self.assertEqual([row["label"] for row in rows], ["selected_plan", guard.LABEL, "utterance"])
        payload = result["runtime_trace"][guard.LABEL]
        self.assertEqual(payload["final_sha256"], guard._sha(final))
        self.assertNotIn(self.source, str(payload))
        self.assertNotIn(final, str(payload))

    def test_inserted_node_synchronizes_same_cycle_snapshot_history(self):
        state = logic()
        final = guard.guard_selected_deterministic_surface_p4(
            self.right, self.leaked, state, user_input=self.source
        )
        prior = {"cycle_index": 6, "blackboard": [{"label": "prior"}]}
        current = {
            "cycle_index": 7,
            "blackboard": [{"stage": "surface", "label": "utterance", "payload": {"reply": final}}],
        }
        result = {
            "logic": state,
            "runtime_trace": deepcopy(current),
            "runtime_state": {
                "blackboard": deepcopy(current["blackboard"]),
                "recent_turn_traces": [deepcopy(prior), deepcopy(current)],
            },
        }
        guard._append_node(result)
        sync_current_history_m41_1(result)
        self.assertEqual(result["runtime_state"]["blackboard"], result["runtime_trace"]["blackboard"])
        self.assertEqual(result["runtime_state"]["recent_turn_traces"][-1], result["runtime_trace"])
        self.assertEqual(result["runtime_state"]["recent_turn_traces"][0], prior)
