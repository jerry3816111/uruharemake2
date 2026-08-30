import inspect
import threading
import unittest
from unittest.mock import patch

from rightbrain_language_quality import (
    ASCII_WORD_RE,
    AUDITED_CHINESE_SPECIFIC_RE,
    AUDITED_NONSTANDARD_CJK_RE,
    CHINESE_SPECIFIC_RE,
    FOREIGN_SCRIPT_RE,
    NONSTANDARD_CJK_RE,
)
from uruha_brain_mac import RightBrain, UruhaBrainV4_Mac
import uruha_web_ui


class UserVisibleJapaneseGuardV211Tests(unittest.TestCase):
    def setUp(self):
        self.rightbrain = RightBrain(load_model=False)

    def assertJapaneseVisibleSurface(self, reply, allowed_ascii=()):
        self.assertRegex(reply, r"[ぁ-んァ-ヶー一-龠]")
        self.assertIsNone(CHINESE_SPECIFIC_RE.search(reply))
        self.assertIsNone(AUDITED_CHINESE_SPECIFIC_RE.search(reply))
        self.assertIsNone(NONSTANDARD_CJK_RE.search(reply))
        self.assertIsNone(AUDITED_NONSTANDARD_CJK_RE.search(reply))
        self.assertIsNone(FOREIGN_SCRIPT_RE.search(reply))
        leaked_ascii = {
            token.lower()
            for token in ASCII_WORD_RE.findall(reply)
            if token.lower() not in {item.lower() for item in allowed_ascii}
        }
        self.assertEqual(leaked_ascii, set())

    def guard(self, reply, user_input, logic=None, memory_data=None):
        logic = dict(logic or {})
        final = self.rightbrain.enforce_user_visible_japanese(
            reply,
            logic,
            user_input=user_input,
            memory_data=memory_data or {},
        )
        return final, logic["visible_language_guard"]

    def test_reproduced_strawberry_milk_leak_is_localized_before_ui(self):
        raw = "Strawberry milk.。そのくらいでいいだろ。"
        # This documents the real gap: the earlier candidate gate trusted ASCII
        # copied from user input/core_message_jp and therefore accepted it.
        old_reasons = self.rightbrain._model_candidate_rejection_reasons(
            raw,
            {"core_message_jp": "Strawberry milk"},
            80,
            user_input="Strawberry milk",
        )
        self.assertEqual(old_reasons, [])

        final, trace = self.guard(
            raw,
            "Strawberry milk",
            {"core_message_jp": "Strawberry milk"},
        )

        self.assertEqual(final, "いちごミルク。そのくらいでいいだろ。")
        self.assertJapaneseVisibleSurface(final)
        self.assertTrue(trace["changed"])
        self.assertEqual(trace["repair_action"], "localized_known_terms")
        self.assertEqual(trace["original_reply"], raw)
        self.assertEqual(trace["final_reply"], final)

    def test_chinese_surface_fails_closed_to_casual_japanese(self):
        final, trace = self.guard(
            "可以啊，我覺得今天不用太擔心。",
            "你今天心情好嗎？",
            {"scene": "casual"},
        )

        self.assertEqual(final, "ん、その話もう少し聞かせて。")
        self.assertJapaneseVisibleSurface(final)
        self.assertIn("cjk_language_leak", trace["initial_rejection_reasons"])
        self.assertEqual(trace["repair_action"], "safe_japanese_persona_fallback")
        self.assertEqual(trace["final_rejection_reasons"], [])

    def test_english_surface_fails_closed_to_in_character_support_japanese(self):
        final, trace = self.guard(
            "You should rest today.",
            "I am exhausted today.",
            {"scene": "support"},
        )

        self.assertEqual(final, "しんどいなら、今日は無理すんな。")
        self.assertJapaneseVisibleSurface(final)
        self.assertIn("missing_japanese_surface", trace["initial_rejection_reasons"])
        self.assertIn("unexpected_ascii_leak", trace["initial_rejection_reasons"])

    def test_clean_japanese_surface_is_unchanged(self):
        raw = "今日は無理すんな、ちゃんと休め。"
        final, trace = self.guard(raw, "今日は疲れた。", {"scene": "support"})

        self.assertEqual(final, raw)
        self.assertJapaneseVisibleSurface(final)
        self.assertFalse(trace["changed"])
        self.assertEqual(trace["repair_action"], "none")

    def test_broken_punctuation_after_legacy_ascii_removal_fails_closed_naturally(self):
        final, trace = self.guard(
            "ん、。そのくらいでいいだろ。",
            "我最喜歡草莓牛奶。",
            {
                "scene": "casual",
                "grounding": {"offered_item": "ストロベリーミルク"},
            },
        )

        self.assertEqual(final, "ストロベリーミルクが好きなんだな。そこは覚えとく。")
        self.assertJapaneseVisibleSurface(final)
        self.assertIn(
            "malformed_japanese_punctuation",
            trace["initial_rejection_reasons"],
        )
        self.assertEqual(trace["repair_action"], "safe_japanese_persona_fallback")

    def test_runtime_transcript_prefix_cannot_leak_through_ascii_stripping(self):
        raw = "User:我叫小傑。 -> Uruha:ん、小傑の余韻まだあるし。急に切り替えるのも雑だろ。"
        final, trace = self.guard(
            raw,
            "我最喜歡草莓牛奶。",
            {
                "scene": "casual",
                "intent": "直接回答用户的问题",
                "grounding": {"offered_item": "ストロベリーミルクティー"},
            },
        )

        self.assertEqual(final, "ストロベリーミルクが好きなんだな。そこは覚えとく。")
        self.assertJapaneseVisibleSurface(final)
        self.assertIn("runtime_trace_artifact", trace["initial_rejection_reasons"])
        self.assertEqual(trace["repair_action"], "safe_japanese_persona_fallback")

    def test_favorite_confirmation_cannot_publish_an_orphaned_particle(self):
        final, trace = self.guard(
            "はいはい、は好きだね。そのくらいでいいだろ。",
            "我最喜歡草莓牛奶。",
            {
                "scene": "casual",
                "intent": "直接回答",
                "grounding": {"offered_item": "Strawberry Milk"},
            },
        )

        self.assertEqual(final, "ストロベリーミルクが好きなんだな。そこは覚えとく。")
        self.assertJapaneseVisibleSurface(final)
        self.assertIn("orphaned_japanese_particle", trace["initial_rejection_reasons"])
        self.assertIn("favorite_grounding_missing", trace["initial_rejection_reasons"])
        self.assertEqual(trace["repair_action"], "safe_japanese_persona_fallback")

    def test_chinese_input_echo_is_rejected_even_without_ascii_trace_labels(self):
        final, trace = self.guard(
            "我叫小傑。ん、小傑の余韻まだあるし。",
            "我叫小傑。",
            {"scene": "casual", "intent": "profile_name_update"},
        )

        self.assertEqual(final, "ん、その話もう少し聞かせて。")
        self.assertJapaneseVisibleSurface(final)
        self.assertIn("chinese_input_echo", trace["initial_rejection_reasons"])
        self.assertEqual(trace["repair_action"], "safe_japanese_persona_fallback")

    def test_chinese_favorite_value_is_localized_for_recall_surface(self):
        final, trace = self.guard(
            "草莓牛奶って前に言ってただろ。",
            "我最喜歡的飲料是什麼？",
            {"scene": "casual", "intent": "recall_favorite"},
        )

        self.assertEqual(final, "いちごミルクって前に言ってただろ。")
        self.assertJapaneseVisibleSurface(final)
        self.assertEqual(trace["repair_action"], "localized_known_terms")

    def test_malformed_identity_surface_falls_back_to_explicit_uruha_identity(self):
        final, trace = self.guard(
            "うるはだよ、小傑。覚えてないの？。そのくらいでいいだろ。",
            "お前は誰？自分がうるはだって分かってる？",
            {"scene": "casual", "intent": "self_intro"},
        )

        self.assertEqual(final, "うちは一ノ瀬うるは。そこは間違えてない。")
        self.assertJapaneseVisibleSurface(final)
        self.assertIn(
            "malformed_japanese_punctuation",
            trace["initial_rejection_reasons"],
        )
        self.assertEqual(trace["repair_action"], "safe_japanese_persona_fallback")

    def test_self_intro_cannot_confuse_the_user_profile_name_for_uruha(self):
        final, trace = self.guard(
            "小傑って呼べばいいんだろ。",
            "你是誰？你自己叫什麼名字？請直接回答你是誰。",
            {
                "scene": "casual",
                "intent": "self_intro",
                "grounding": {"profile_name": "小傑"},
            },
            {"profile_structured": {"name": "小傑"}},
        )

        self.assertEqual(final, "うちは一ノ瀬うるは。そこは間違えてない。")
        self.assertJapaneseVisibleSurface(final)
        self.assertIn(
            "self_identity_anchor_missing",
            trace["initial_rejection_reasons"],
        )
        self.assertEqual(trace["repair_action"], "safe_japanese_persona_fallback")

    def test_self_intro_cannot_deny_being_uruha(self):
        final, trace = self.guard(
            "うるはじゃないよ。小傑だし。",
            "Who are you?",
            {"scene": "casual", "intent": "self_intro"},
        )

        self.assertEqual(final, "うちは一ノ瀬うるは。そこは間違えてない。")
        self.assertJapaneseVisibleSurface(final)
        self.assertIn(
            "self_identity_contradiction",
            trace["initial_rejection_reasons"],
        )
        self.assertEqual(trace["repair_action"], "safe_japanese_persona_fallback")

    def test_valid_but_awkward_self_intro_is_canonicalized(self):
        final, trace = self.guard(
            "一回、うちは一ノ瀬うるは。まず名前はそれで覚えとけ。",
            "你是誰？你自己叫什麼名字？請直接回答你是誰。",
            {"scene": "casual", "intent": "self_intro"},
        )

        self.assertEqual(final, "うちは一ノ瀬うるは。そこは間違えてない。")
        self.assertJapaneseVisibleSurface(final)
        self.assertEqual(trace["initial_rejection_reasons"], [])
        self.assertEqual(trace["repair_action"], "canonical_self_identity_surface")

    def test_unknown_color_query_cannot_reuse_a_known_drink_memory(self):
        final, trace = self.guard(
            "前にいちごミルクが好きって言ってた。",
            "What is my favorite color? If I never told you, say you don't remember.",
            {"scene": "casual", "intent": "memory_uncertain"},
        )

        self.assertEqual(final, "好きな色はまだ聞いてない。そこは勝手に埋めない。")
        self.assertJapaneseVisibleSurface(final)
        self.assertIn(
            "memory_uncertainty_not_disclosed",
            trace["initial_rejection_reasons"],
        )
        self.assertEqual(trace["repair_action"], "safe_japanese_persona_fallback")

    def test_narrow_unavoidable_proper_noun_exception_is_preserved(self):
        final, trace = self.guard(
            "GPT-4oなら、そのくらいでいいだろ。",
            "Can GPT-4o do it?",
            {"scene": "casual"},
        )

        self.assertEqual(final, "GPT-4oなら、そのくらいでいいだろ。")
        self.assertJapaneseVisibleSurface(final, allowed_ascii={"GPT-4o"})
        self.assertEqual(trace["allowed_ascii_proper_nouns"], ["gpt-4o"])

    def test_trusted_profile_name_is_preserved_but_memory_value_words_are_not(self):
        final, trace = self.guard(
            "Jerry、Strawberry milkなら覚えてる。",
            "Do you remember my favorite drink?",
            {"grounding": {"profile_name": "Jerry"}},
            {"profile_structured": {"name": "Jerry", "favorite_drink": "Strawberry milk"}},
        )

        self.assertEqual(final, "Jerry、いちごミルクなら覚えてる。")
        self.assertJapaneseVisibleSurface(final, allowed_ascii={"Jerry"})
        self.assertEqual(trace["allowed_ascii_proper_nouns"], ["jerry"])

    def test_english_drink_memory_is_localized_instead_of_stripped_empty(self):
        final, trace = self.guard(
            "忘れてないし、ginger aleだろ。",
            "私の好きな飲み物、覚えてる？",
            {"intent": "recall_preference", "scene": "casual"},
            {"profile_structured": {"favorites": ["ginger ale"]}},
        )

        self.assertEqual(final, "忘れてないし、ジンジャーエールだろ。")
        self.assertJapaneseVisibleSurface(final)
        self.assertEqual(trace["repair_action"], "localized_known_terms")

    def test_negated_old_favorite_does_not_override_current_memory_answer(self):
        final, trace = self.guard(
            "忘れてないし、ジンジャーエールだろ。",
            "你沒有還把草莓牛奶當成我現在最喜歡的吧？",
            {
                "intent": "memory_correction",
                "scene": "casual",
                "memory_anchor": {
                    "kind": "favorite_drink",
                    "value": "ginger ale",
                    "jp_anchor": "ジンジャーエール",
                },
            },
            {
                "profile_structured": {
                    "favorites": ["ginger ale"],
                    "dislikes": ["草莓牛奶"],
                }
            },
        )

        self.assertEqual(final, "忘れてないし、ジンジャーエールだろ。")
        self.assertJapaneseVisibleSurface(final)
        self.assertNotIn("favorite_grounding_missing", trace["initial_rejection_reasons"])
        self.assertEqual(trace["repair_action"], "none")

    def test_reactive_and_proactive_boundaries_run_before_persistence_or_publication(self):
        reactive_source = inspect.getsource(UruhaBrainV4_Mac.emit_response_if_ready)
        proactive_source = inspect.getsource(UruhaBrainV4_Mac._handle_internal_urge_event)

        reactive_guard = reactive_source.index("enforce_user_visible_japanese")
        self.assertLess(reactive_guard, reactive_source.index("save_episode"))
        self.assertLess(reactive_guard, reactive_source.index('"reply": reply'))
        proactive_guard = proactive_source.index("enforce_user_visible_japanese")
        self.assertLess(proactive_guard, proactive_source.index("save_episode"))
        self.assertLess(proactive_guard, proactive_source.index('"reply": reply'))

    def test_web_runtime_graph_receives_the_actual_turn_input(self):
        class FakeBrain:
            def run_turn_debug(self, _user_text):
                return {
                    "reply": "今日は休め。",
                    "logic": {"intent": "tired_support"},
                    "memory_data": {},
                    "runtime_trace": {
                        "blackboard": [
                            {
                                "stage": "surface",
                                "label": "utterance",
                                "payload": {"reply": "今日は休め。"},
                            }
                        ],
                        "memory_writes": [],
                    },
                    "runtime_state": {},
                }

        class FakeRuntime:
            _lock = threading.Lock()

            def mark_activity(self):
                return None

            def get_brain(self):
                return FakeBrain()

        with patch.object(uruha_web_ui, "RUNTIME", FakeRuntime()):
            result = uruha_web_ui._run_turn("I am exhausted today.", auto_tts=False)

        self.assertEqual(result["user_text"], "I am exhausted today.")
        self.assertIn("I am exhausted today.", result["flow_html"])
        self.assertNotIn("USER SIGNAL</span><span class=\"brain-node-signal\">等待輸入", result["flow_html"])


if __name__ == "__main__":
    unittest.main()
