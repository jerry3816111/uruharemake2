import json
import unittest

from uruha_brain_mac import RightBrain


class RightBrainMemoryCueCanonicalizationV85Tests(unittest.TestCase):
    def setUp(self):
        self.rightbrain = RightBrain(load_model=False)
        self.logic = {
            "jp_summary": "前の会話について答える。",
            "core_message_jp": "ポテトなら普通にあり。少しもらう。",
            "memory_use_expected": True,
            "memory_speakability": "explicit_ok",
            "memory_anchor": {
                "kind": "context",
                "jp_anchor": "User:我愛吃薯條 -> Uruha:またポテ",
                "terms": ["User:我愛吃薯條 -> Uruha:またポテト", "またポテトの"],
            },
            "constraints": {"max_chars": 40},
            "human_speech_plan": {
                "content_units": ["ポテトについて答える"],
                "grounding_terms": ["ポテト"],
            },
            "must_avoid": [],
        }

    def test_disabled_flag_preserves_frozen_legacy_control(self):
        self.rightbrain.memory_cue_canonicalization_enabled = False
        brief = self.rightbrain._audited_memory_expression_brief(self.logic)
        self.assertIn("User:", brief["allowed_memory_cues"][0]["jp_anchor"])

    def test_enabled_flag_uses_clean_planner_meaning(self):
        self.rightbrain.memory_cue_canonicalization_enabled = True
        brief = self.rightbrain._audited_memory_expression_brief(self.logic)
        cue = brief["allowed_memory_cues"][0]
        serialized = json.dumps(cue, ensure_ascii=False)
        self.assertEqual(brief["policy"], "explicit_allowed")
        self.assertEqual(cue["jp_anchor"], self.logic["core_message_jp"])
        self.assertNotIn("User:", serialized)
        self.assertNotIn("Uruha:", serialized)
        self.assertNotIn("我愛", serialized)
        self.assertIn("ポテト", serialized)

    def test_semantic_groups_use_same_clean_cue(self):
        self.rightbrain.memory_cue_canonicalization_enabled = True
        groups = self.rightbrain._audited_memory_surface_semantic_groups(self.logic)
        serialized = json.dumps(groups, ensure_ascii=False)
        self.assertNotIn("User:", serialized)
        self.assertNotIn("我愛", serialized)
        self.assertTrue(any("ポテト" in marker for group in groups for marker in group))

    def test_payload_contains_trace_but_does_not_expose_raw_anchor(self):
        self.rightbrain.memory_cue_canonicalization_enabled = True
        payload = json.loads(self.rightbrain._build_model_surface_payload(self.logic, {"mood": 0, "trust": 60}, 40))
        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("User:", serialized)
        self.assertNotIn("Uruha:", serialized)
        self.assertNotIn("我愛", serialized)
        self.assertEqual(
            self.logic["memory_cue_canonicalization_trace"]["selected_source"],
            "core_message",
        )

    def test_unsafe_anchor_without_clean_plan_is_blocked(self):
        self.rightbrain.memory_cue_canonicalization_enabled = True
        logic = {
            **self.logic,
            "core_message_jp": "",
            "jp_summary": "",
            "human_speech_plan": {"content_units": [], "grounding_terms": []},
            "memory_anchor": {"kind": "context", "jp_anchor": "User:你好 -> Uruha:呢", "terms": []},
        }
        brief = self.rightbrain._audited_memory_expression_brief(logic)
        self.assertEqual(brief["policy"], "do_not_mention")
        self.assertEqual(brief["allowed_memory_cues"], [])
        self.assertEqual(self.rightbrain._audited_memory_surface_semantic_groups(logic), [])

    def test_localized_transcript_labels_are_blocked(self):
        self.rightbrain.memory_cue_canonicalization_enabled = True
        for anchor in ["ユーザー：前は麦茶が好き", "使用者：以前喜歡麥茶"]:
            with self.subTest(anchor=anchor):
                logic = {
                    **self.logic,
                    "core_message_jp": "",
                    "jp_summary": "",
                    "human_speech_plan": {"content_units": [], "grounding_terms": []},
                    "memory_anchor": {"kind": "context", "jp_anchor": anchor, "terms": []},
                }
                brief = self.rightbrain._audited_memory_expression_brief(logic)
                self.assertEqual(brief["policy"], "do_not_mention")
                self.assertEqual(brief["allowed_memory_cues"], [])

    def test_clean_japanese_anchor_remains_available_as_fallback(self):
        self.rightbrain.memory_cue_canonicalization_enabled = True
        logic = {
            **self.logic,
            "core_message_jp": "",
            "human_speech_plan": {"content_units": [], "grounding_terms": []},
            "memory_anchor": {"kind": "preference", "jp_anchor": "前は麦茶が好きだった", "terms": ["麦茶"]},
        }
        brief = self.rightbrain._audited_memory_expression_brief(logic)
        self.assertEqual(brief["policy"], "explicit_allowed")
        self.assertEqual(brief["allowed_memory_cues"][0]["jp_anchor"], "麦茶")


if __name__ == "__main__":
    unittest.main()
