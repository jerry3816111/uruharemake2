import unittest

from uruha_brain_mac import RightBrain


class TestHumanBlindGeneralizationSurface(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.right = RightBrain(load_model=False)

    def _reply(self, user_input, intent, surface_act, grounding):
        return self.right._compose_surface_reply(
            {
                "intent": intent,
                "scene": "support",
                "surface_act": surface_act,
                "grounding": grounding,
                "constraints": {"max_chars": 48},
                "payload_level": "medium",
            },
            user_input,
            memory_data={},
        )

    def test_reply_anxiety_keeps_uncertainty_and_stops_self_blame(self):
        reply = self._reply(
            "群組冷掉之後，我覺得自己很吵。",
            "friend_no_reply",
            "validate_then_hold",
            {"reply_self_blame": True},
        )

        self.assertIn("返事", reply)
        self.assertIn("決めつけ", reply)
        self.assertTrue("不安" in reply or "気になる" in reply)

    def test_reference_probe_uses_grounded_subject(self):
        reply = self._reply(
            "限定活動ED我想不起來。",
            "reference_probe",
            "reference_probe",
            {"reference_subject_jp": "限定イベントED"},
        )

        self.assertIn("限定イベントED", reply)
        self.assertTrue(any(marker in reply for marker in ("作品名", "曲名", "タイトル")))

    def test_apology_repair_apologizes_instead_of_asking_user_to_repeat(self):
        reply = self._reply(
            "你剛剛道歉太冷了，重新說。",
            "apology_repair",
            "rephrase_plain",
            {"apology_repair": True},
        )

        self.assertTrue(any(marker in reply for marker in ("冷た", "雑", "悪かった")))
        self.assertIn("ごめん", reply)

    def test_withdrawal_surface_is_risk_calibrated(self):
        mild = self._reply(
            "勿擾",
            "anxious_support",
            "protective_brake",
            {"withdrawal_risk": "mild", "withdrawal_kind": "do_not_disturb", "withdrawal_anchor_jp": "通知"},
        )
        high = self._reply("不留痕跡", "anxious_support", "protective_brake", {"withdrawal_risk": "high"})

        self.assertTrue(any(marker in mild for marker in ("通知", "表示")))
        self.assertIn("連絡", mild)
        self.assertIn("止ま", high)
        self.assertTrue(any(marker in high for marker in ("誰か", "連絡", "近くの人")))

    def test_withdrawal_surface_preserves_concrete_context(self):
        cases = [
            (
                "我不想讓朋友看到我還在線。",
                {"withdrawal_risk": "mild", "withdrawal_kind": "online_visibility", "withdrawal_anchor_jp": "オンライン表示"},
                "オンライン",
            ),
            (
                "我想躲在廁所裡。",
                {"withdrawal_risk": "medium", "withdrawal_kind": "private_location", "withdrawal_anchor_jp": "トイレ"},
                "トイレ",
            ),
            (
                "我想把聊天全部清掉。",
                {"withdrawal_risk": "high", "withdrawal_kind": "erase_trace", "withdrawal_anchor_jp": "チャット履歴"},
                "履歴",
            ),
        ]
        for utterance, grounding, expected_anchor in cases:
            with self.subTest(utterance=utterance):
                reply = self._reply(utterance, "anxious_support", "protective_brake", grounding)
                self.assertIn(expected_anchor, reply)
                _, hits = self.right._surface_semantic_group_hits(reply, {
                    "intent": "anxious_support",
                    "grounding": grounding,
                })
                self.assertTrue(all(hits), reply)

    def test_refinement_keeps_reply_anxiety_semantics(self):
        logic = {
            "intent": "friend_no_reply",
            "scene": "support",
            "surface_act": "validate_then_hold",
            "grounding": {"reply_self_blame": "True"},
            "constraints": {"max_chars": 48},
            "payload_level": "medium",
            "dialogue_act": "emotional_containment",
        }

        reply = self.right._refine_conversational_reply(
            "そのまま抱え込むなって。",
            logic,
            "群組冷掉之後，我覺得自己很吵。",
            memory_data={},
        )

        _, hits = self.right._surface_semantic_group_hits(reply, logic)
        self.assertTrue(all(hits), reply)

    def test_refinement_keeps_withdrawal_safety_semantics(self):
        logic = {
            "intent": "anxious_support",
            "scene": "support",
            "surface_act": "protective_brake",
            "grounding": {"withdrawal_risk": "high"},
            "constraints": {"max_chars": 48},
            "payload_level": "high",
            "dialogue_act": "emotional_containment",
        }

        reply = self.right._refine_conversational_reply(
            "そのまま抱え込むなって。",
            logic,
            "我想清掉聊天紀錄，不留痕跡。",
            memory_data={},
        )

        _, hits = self.right._surface_semantic_group_hits(reply, logic)
        self.assertTrue(all(hits), reply)

    def test_candidate_score_penalizes_dropped_planner_meaning(self):
        logic = {
            "intent": "friend_no_reply",
            "scene": "support",
            "grounding": {"reply_self_blame": "True"},
            "constraints": {"max_chars": 48},
            "payload_level": "medium",
        }

        specific = "返事がなくて不安でも、自分のせいだと決めつけるな。"
        generic = "そのまま一人で抱え込むなって。"

        self.assertGreater(
            self.right._score_candidate(specific, logic),
            self.right._score_candidate(generic, logic),
        )

    def test_plain_no_reply_does_not_invent_self_blame_contract(self):
        logic = {
            "intent": "friend_no_reply",
            "scene": "support",
            "surface_act": "validate_then_hold",
            "grounding": {"reply_self_blame": "False"},
            "constraints": {"max_chars": 48},
            "payload_level": "medium",
        }

        groups = self.right._required_surface_semantic_groups(logic)
        reply = self.right._compose_surface_reply(
            logic,
            "朋友都不回我訊息",
            memory_data={},
        )

        self.assertEqual(groups, [])
        self.assertNotIn("決めつけ", reply)

    def test_surface_sanitizer_collapses_duplicate_punctuation(self):
        reply = self.right._sanitize_reply("再起動。。そのくらいでいいだろ。", max_chars=48)

        self.assertEqual(reply, "再起動。そのくらいでいいだろ。")


if __name__ == "__main__":
    unittest.main()
