import json
import inspect
import unittest
from pathlib import Path

import uruha_brain_mac as ubm
import uruha_web_ui
from run_v2_17_long_dialogue_memory import (
    CASE_PATH,
    OUTPUT_PATH,
    _remove_value_from_decision_view,
)
from uruha_long_dialogue_memory_lab import (
    build_long_dialogue_payload,
    checkpoint_choices,
    render_long_dialogue_lab,
)


ROOT = Path(__file__).resolve().parent


class LongDialogueMemoryV217Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = json.loads(CASE_PATH.read_text(encoding="utf-8"))

    def test_case_has_seed_long_distractor_gap_correction_and_rerecall(self):
        turns = self.case["turns"]
        expected = self.case["expected"]
        self.assertEqual(len(turns), 25)
        self.assertEqual(turns[0]["role"], "memory_seed")
        self.assertEqual(turns[expected["first_recall_turn"] - 1]["role"], "delayed_recall")
        self.assertEqual(turns[expected["correction_source_turn"] - 1]["role"], "explicit_correction")
        self.assertEqual(turns[expected["corrected_recall_turn"] - 1]["role"], "corrected_recall")
        self.assertGreaterEqual(
            sum(row["role"] == "distractor" for row in turns[: expected["first_recall_turn"] - 1]),
            15,
        )
        self.assertEqual(
            sum(row["execution"] == "full_runtime" for row in turns),
            4,
        )

    def test_current_turn_preference_update_outranks_stale_profile_value(self):
        brain = object.__new__(ubm.UruhaBrainV4_Mac)
        memory_data = {
            "profile_structured": {
                "name": None,
                "likes": [],
                "dislikes": [],
                "favorites": ["草莓牛奶"],
            },
            "working_memory_items": [],
            "memory_provenance": {
                "passed_to_leftbrain": [
                    {
                        "source": "profile",
                        "channel": "profile_structured",
                        "text": "favorites=草莓牛奶",
                        "trace_id": "derived:profile:old",
                    }
                ]
            },
        }

        anchor = brain._extract_actionable_memory_anchor(
            "不過現在改了。我不能喝草莓牛奶了。我最喜歡 ginger ale。",
            memory_data,
        )

        self.assertEqual(anchor["kind"], "current_preference_update")
        self.assertEqual(anchor["value"], "ginger ale")
        self.assertEqual(anchor["jp_anchor"], "ジンジャーエール")
        self.assertEqual(anchor["source"], "current_input")

    def test_removing_target_from_decision_view_preserves_original_payload(self):
        original = {
            "profile_structured": {
                "favorites": ["ginger ale"],
                "likes": [],
                "dislikes": ["草莓牛奶"],
            },
            "working_memory_items": [
                {"trace_id": "target", "text": "favorite=ginger ale"},
                {"trace_id": "control", "text": "unrelated"},
            ],
            "memory_provenance": {
                "passed_to_leftbrain": [
                    {"trace_id": "target", "text": "favorites=ginger ale"},
                    {"trace_id": "control", "text": "unrelated"},
                ]
            },
        }

        removed = _remove_value_from_decision_view(original, "ginger ale")

        self.assertEqual(original["profile_structured"]["favorites"], ["ginger ale"])
        self.assertEqual(removed["profile_structured"]["favorites"], [])
        self.assertEqual([row["trace_id"] for row in removed["working_memory_items"]], ["control"])

    def test_withdrawn_preference_anchor_produces_explicit_noncurrent_reply(self):
        rightbrain = ubm.RightBrain(load_model=False)
        reply = rightbrain._memory_grounded_reply(
            {
                "intent": "memory_correction",
                "memory_use_expected": True,
                "memory_anchor": {
                    "kind": "preference_correction",
                    "value": "草莓牛奶",
                    "jp_anchor": "草莓牛奶",
                },
                "constraints": {"max_chars": 42},
            },
            "你沒有還把草莓牛奶當成我現在最喜歡的吧？",
        )

        self.assertIsNotNone(reply)
        self.assertRegex(reply, r"じゃない|前の情報|外してる")

    def test_latest_raw_result_retains_failure_or_bounded_success_honestly(self):
        if not OUTPUT_PATH.exists():
            self.skipTest("formal isolated run has not been executed")
        raw = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(raw["summary"]["turn_count"], 25)
        self.assertEqual(raw["summary"]["full_runtime_checkpoint_count"], 4)
        self.assertTrue(raw["summary"]["production_db_unchanged"])
        self.assertIn("bounded_success", raw["summary"])
        self.assertFalse(raw["execution_boundary"]["replayed_turns_are_fresh_model_generations"])

    def test_formal_result_passes_bounded_long_dialogue_gates(self):
        raw = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        summary = raw["summary"]
        self.assertTrue(summary["bounded_success"])
        self.assertTrue(summary["initial_delayed_recall_pass"])
        self.assertTrue(summary["corrected_delayed_recall_pass"])
        self.assertTrue(summary["withdrawn_value_not_current_pass"])
        self.assertTrue(summary["all_checkpoint_visible_japanese_pass"])
        self.assertTrue(summary["anchor_ablation_gate_pass"])
        self.assertTrue(summary["production_db_unchanged"])

    def test_visual_lab_exposes_all_turns_trace_chain_and_evidence_boundary(self):
        self.assertEqual(len(checkpoint_choices()), 4)
        payload = build_long_dialogue_payload("25")
        html = render_long_dialogue_lab("25")
        self.assertEqual(len(payload["rows"]), 25)
        self.assertIn("LONG CONVERSATION TIMELINE", html)
        self.assertEqual(html.count('class="lm-turn'), 25)
        self.assertIn("來源輪次", html)
        self.assertIn("傳給決策", html)
        self.assertIn("決策錨點", html)
        self.assertIn("日文回答", html)
        self.assertIn("25 輪都是 fresh generation", html)
        self.assertIn("失敗沒有被洗掉", html)
        self.assertNotIn("<script", html.lower())

    def test_web_ui_places_long_memory_lab_before_equation_and_chat(self):
        source = inspect.getsource(uruha_web_ui.build_demo)
        self.assertIn('gr.Tab("Long Memory Lab")', source)
        self.assertLess(source.index('gr.Tab("Long Memory Lab")'), source.index('gr.Tab("Equation Lab")'))
        self.assertLess(source.index('gr.Tab("Long Memory Lab")'), source.index('gr.Tab("Chat")'))


if __name__ == "__main__":
    unittest.main()
