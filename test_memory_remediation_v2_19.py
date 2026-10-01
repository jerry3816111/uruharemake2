import unittest

import uruha_brain_mac as ubm
import uruha_personhood_loop as upl


class MemoryRemediationV219Test(unittest.TestCase):
    def test_favorite_claim_question_is_not_an_explicit_update(self):
        text = "那我有說過我最喜歡レモネード嗎？"
        self.assertEqual(ubm._extract_explicit_current_favorite(text), "")
        self.assertEqual(ubm._extract_favorite_claim_query(text), "レモネード")

    def test_explicit_favorite_statement_still_extracts(self):
        self.assertEqual(
            ubm._extract_explicit_current_favorite("現在改了，我最喜歡ほうじ茶。"),
            "ほうじ茶",
        )

    def test_direct_user_report_suppresses_new_provisional_clarification(self):
        model = upl.empty_longitudinal_model()
        model["layers"]["provisional"].append(
            {
                "model_item_id": "provisional-need",
                "kind": "pragmatic_implicit_need",
                "value": "先被傾聽",
                "confidence": 0.5,
                "status": "active",
                "linked_hypothesis_ids": ["hyp-current"],
                "consecutive_influence_count": 1,
                "influence_count": 1,
                "last_influenced_turn": 7,
            }
        )
        logic, _, strategy = upl.apply_longitudinal_model_to_plan(
            {"intent": "chat", "scene": "casual"},
            model,
            {"hypothesis_id": "hyp-current", "semantic_features": []},
            turn_index=8,
            direct_user_report={
                "kind": "current_preference_update",
                "value": "ほうじ茶",
                "source": "current_user_input",
            },
        )
        self.assertNotEqual(logic.get("intent"), "functional_understanding_active_verify")
        self.assertFalse(strategy["changed_plan"])
        self.assertTrue(strategy["clarification_suppressed_by_direct_user_report"])
        self.assertEqual(
            strategy["reason"],
            "explicit_user_report_outranks_provisional_clarification",
        )

    def test_relational_claim_query_builds_denial_anchor(self):
        brain = object.__new__(ubm.UruhaBrainV4_Mac)
        anchor = brain._extract_actionable_memory_anchor(
            "那我有說過我最喜歡レモネード嗎？",
            {
                "profile_structured": {"favorites": ["ほうじ茶"], "likes": [], "dislikes": ["麦茶"]},
                "working_memory_items": [
                    {
                        "text": "朋友剛剛點了レモネード。",
                        "source": "short_term",
                        "score": 2.8,
                        "trace_id": "trace-friend-lemonade",
                        "memory_id": "memory-friend-lemonade",
                    }
                ],
                "memory_provenance": {"passed_to_leftbrain": []},
            },
        )
        self.assertEqual(anchor["kind"], "favorite_claim_denied_relational")
        self.assertEqual(anchor["value"], "レモネード")
        self.assertEqual(anchor["trace_id"], "trace-friend-lemonade")

    def test_relational_claim_query_uses_recent_event_when_ranked_memory_misses(self):
        brain = object.__new__(ubm.UruhaBrainV4_Mac)
        anchor = brain._extract_actionable_memory_anchor(
            "那我有說過我最喜歡レモネード嗎？",
            {
                "profile_structured": {"favorites": ["ほうじ茶"], "likes": [], "dislikes": ["麦茶"]},
                "working_memory_items": [],
                "recent_turns": [
                    {"user": "我把報告標題定下來了。", "assistant": "決めたなら迷うな。"},
                    {"user": "朋友又說那杯レモネード很好喝。", "assistant": "友達、気に入ってんじゃん。"},
                    {"user": "現在只剩正式執行。", "assistant": "そのまま残せ。"},
                ],
                "memory_provenance": {"passed_to_leftbrain": []},
            },
        )
        self.assertEqual(anchor["kind"], "favorite_claim_denied_relational")
        self.assertEqual(anchor["source"], "recent_turn")
        self.assertIn("朋友", anchor["source_text"])
        self.assertTrue(str(anchor["trace_id"]).startswith("derived:recent_turn:"))

    def test_language_instruction_leak_falls_back_to_grounded_memory_reply(self):
        right = ubm.RightBrain(load_model=False)
        logic = {
            "intent": "recall_favorite",
            "memory_use_expected": True,
            "memory_anchor": {
                "kind": "favorite_drink",
                "value": "ほうじ茶",
                "jp_anchor": "ほうじ茶",
                "terms": ["ほうじ茶"],
            },
            "constraints": {"max_chars": 42},
        }
        reply = right.enforce_user_visible_japanese(
            "日本語だけで、元の意味を落とさず言い直す。",
            logic,
            user_input="今一番好きな飲み物は何？",
        )
        self.assertIn("ほうじ茶", reply)
        self.assertNotIn("日本語だけで", reply)
        self.assertEqual(
            logic["visible_language_guard"]["repair_action"],
            "safe_japanese_persona_fallback",
        )

    def test_relational_denial_has_value_owner_and_no_user_assertion(self):
        right = ubm.RightBrain(load_model=False)
        reply = right._memory_grounded_reply(
            {
                "memory_use_expected": True,
                "memory_anchor": {
                    "kind": "favorite_claim_denied_relational",
                    "value": "レモネード",
                    "jp_anchor": "レモネード",
                    "source_text": "友達がレモネードを頼んだ。",
                },
                "constraints": {"max_chars": 52},
            },
            "レモネードが一番好きって言った？",
        )
        self.assertIn("レモネード", reply)
        self.assertIn("友達", reply)
        self.assertRegex(reply, r"聞いてない|言ってない")

    def test_positive_surface_cannot_reverse_relational_denial_anchor(self):
        right = ubm.RightBrain(load_model=False)
        logic = {
            "intent": "recall_favorite",
            "memory_use_expected": True,
            "memory_anchor": {
                "kind": "favorite_claim_denied_relational",
                "value": "レモネード",
                "jp_anchor": "レモネード",
                "terms": ["レモネード"],
                "source_text": "友達がレモネードを頼んだ。",
            },
            "constraints": {"max_chars": 52},
        }
        reply = right.enforce_user_visible_japanese(
            "レモネードが好きなんだな。そこは覚えとく。",
            logic,
            user_input="那我有說過我最喜歡レモネード嗎？",
        )
        self.assertIn("レモネード", reply)
        self.assertIn("友達", reply)
        self.assertRegex(reply, r"聞いてない|言ってない")
        self.assertNotIn("好きなんだな", reply)
        reasons = logic["visible_language_guard"]["initial_rejection_reasons"]
        self.assertIn("relational_claim_polarity_lost", reasons)


if __name__ == "__main__":
    unittest.main()
