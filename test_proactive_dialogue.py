import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import uruha_brain_mac as brain_mod
from fast_eval_brain import build_fast_brain


class TestProactiveDialogueLifecycle(unittest.TestCase):
    def setUp(self):
        self.brain = build_fast_brain(brain_mod)
        self.brain.memory.has_unconsolidated_turns = lambda _minimum: False
        self.brain.memory.consolidate_recent_experiences = lambda *_args, **_kwargs: None
        self.brain.memory.save_episode = self._save_proactive_episode
        self.brain.right_brain._sanitize_reply = lambda text, max_chars: text[:max_chars]
        self.brain.memory.short_term_buffer = []
        self.loop = {
            "kind": "clarification",
            "label": "等待使用者補充或修正前提",
            "reason": "premise_challenge",
            "key": "clarification:premise_challenge",
        }
        self.brain.runtime.open_loops = [dict(self.loop)]

    def _save_proactive_episode(self, user_input, reply, _psyche, logic):
        self.brain.memory.record_turn(user_input, reply, logic)
        return f"{user_input} -> {reply}"

    def _set_long_idle(self):
        simulated_idle_at = time.time() - (brain_mod.AUTONOMOUS_IDLE_SECONDS * 2.5)
        self.brain._last_external_input_at = simulated_idle_at
        self.brain.runtime.last_interaction_timestamp = simulated_idle_at
        self.brain._last_background_tick_at = 0.0

    def test_open_loop_has_stable_delivery_key(self):
        loops = self.brain._derive_open_loops(
            {
                "response_mode": "premise_challenge",
                "surface_act": "plain_reply",
                "intent": "premise_doubt",
                "hidden_intent": "premise_trap",
            }
        )

        self.assertEqual(loops[0]["key"], "clarification:premise_challenge")

    def test_specific_fragment_creates_one_specific_loop(self):
        loops = self.brain._derive_open_loops(
            {
                "response_mode": "clarify_light",
                "surface_act": "version_fragment_clarify",
                "intent": "version_fragment_clarify",
                "hidden_intent": "plain_request",
            }
        )

        self.assertEqual(len(loops), 1)
        self.assertEqual(loops[0]["kind"], "followup")
        self.assertEqual(loops[0]["key"], "followup:version_fragment_clarify")

    def test_completed_relationship_answer_does_not_create_open_loop(self):
        loops = self.brain._derive_open_loops(
            {
                "response_mode": "direct_answer",
                "surface_act": "affection_tease_soften",
                "intent": "ask_miss_me",
                "hidden_intent": "relationship_temperature_check",
            }
        )

        self.assertEqual(loops, [])

    def test_followup_copy_matches_the_unfinished_obligation(self):
        cases = [
            ("lyric_probe", "reference_probe", ("歌詞", "曲")),
            ("reference_probe", "reference_probe", ("ネタ", "元")),
            ("version_fragment_clarify", "version_fragment_clarify", ("作品", "版")),
            ("correction_followup", "correction_followup", ("違う", "直せ")),
            ("premise_challenge", "premise_doubt", ("前提", "どこ")),
            ("crisis_support", "crisis_support", ("ひとり", "連絡")),
        ]

        for reason, expected_intent, required_markers in cases:
            with self.subTest(reason=reason):
                proactive = self.brain._build_proactive_turn(
                    {
                        "kind": "proactive_followup",
                        "detail": {
                            "open_loop": {"reason": reason},
                            "delivery_key": f"followup:{reason}",
                        },
                    }
                )

                self.assertEqual(proactive["intent"], expected_intent)
                self.assertTrue(any(marker in proactive["line"] for marker in required_markers))

    def test_idle_followup_is_delivered_once_and_suppressed_until_user_returns(self):
        self.brain.memory.short_term_buffer = [
            {"strength": 0.9, "intent": "chat", "scene": "casual", "text": "まだ残っている話題"}
        ]
        self._set_long_idle()

        first = self.brain.run_background_cycle(force=False)
        first_pending = dict(self.brain.runtime.pending_proactive_turn)
        self.brain._last_background_tick_at = 0.0
        while_pending = self.brain.run_background_cycle(force=False)

        self.assertEqual(first["proactive_turn"]["kind"], "proactive_followup")
        self.assertEqual(first["proactive_turn"]["delivery_key"], self.loop["key"])
        self.assertEqual(self.brain.runtime.pending_proactive_turn, first_pending)
        self.assertEqual(while_pending["proactive_turn"], {})
        self.assertEqual(self.brain.runtime.consecutive_proactive_count, 0)

        delivered = self.brain.consume_pending_proactive_turn()

        self.assertEqual(delivered["delivery_key"], self.loop["key"])
        self.assertTrue(delivered["memory_recorded"])
        self.assertEqual(self.brain.memory.session_turns[-1]["reply"], delivered["line"])
        self.assertEqual(self.brain.runtime.pending_proactive_turn, {})
        self.assertEqual(self.brain.runtime.consecutive_proactive_count, 1)
        self.assertIn(self.loop["key"], self.brain.runtime.proactive_delivery_keys)

        self.brain._last_background_tick_at = 0.0
        duplicate_attempt = self.brain.run_background_cycle(force=False)

        self.assertEqual(duplicate_attempt["proactive_turn"], {})
        self.assertEqual(self.brain.runtime.pending_proactive_turn, {})

        self.brain.runtime.register_user_input()
        self.assertEqual(self.brain.runtime.proactive_delivery_keys, [])

    def test_sleep_mode_blocks_new_proactive_output(self):
        self._set_long_idle()
        self.brain.runtime.proactive_sleep_mode = True

        result = self.brain.run_background_cycle(force=False)

        self.assertEqual(result["proactive_turn"], {})
        self.assertEqual(self.brain.runtime.pending_proactive_turn, {})

    def test_web_poll_places_pending_line_in_chat_history(self):
        import uruha_web_ui as web

        self._set_long_idle()
        self.brain.run_background_cycle(force=False)
        fake_runtime = SimpleNamespace(
            _brain=self.brain,
            _lock=threading.Lock(),
            _mouth=None,
            _session_id="test_session",
        )
        fake_record = {"session_id": "test_session", "turn_index": 1}

        with (
            patch.object(web, "RUNTIME", fake_runtime),
            patch.object(web, "_append_conversation_log", return_value=fake_record),
            patch.object(web, "_status_markdown", return_value="status"),
            patch.object(web, "_annotation_context_markdown", return_value="annotation"),
        ):
            result = web.poll_proactive_turn([{"role": "user", "content": "..."}], False)

        self.assertEqual(result[0][-1]["role"], "assistant")
        self.assertEqual(result[0][-1]["content"], "さっきの前提、結局どこから来たんだよ。そこ先だろ。")
        self.assertEqual(result[1], result[0])
        self.assertIsNone(result[2])
        self.assertEqual(result[3], "status")
        self.assertEqual(result[4], fake_record)
        self.assertEqual(result[5], "annotation")
        self.assertEqual(self.brain.runtime.pending_proactive_turn, {})


if __name__ == "__main__":
    unittest.main()
