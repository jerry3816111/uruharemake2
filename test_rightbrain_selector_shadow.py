import json
import unittest
from pathlib import Path
from unittest.mock import patch

from eval_rightbrain_selector_shadow_v1 import build_shadow_report
from project_paths import RIGHTBRAIN_REPAIR_SELECTOR_V1_NATURAL_HOLDOUT_SOURCE_PATH
from test_rightbrain_model_candidate_gate import MEMORY, build_rightbrain, reply_anxiety_logic
from uruha_brain_mac import RightBrain


class RightBrainSelectorShadowTest(unittest.TestCase):
    def test_default_selector_artifact_loads_without_loading_generation_model(self):
        rightbrain = RightBrain(load_model=False)

        self.assertTrue(rightbrain.selector_shadow_enabled)
        self.assertIsNotNone(rightbrain.selector_model)
        self.assertEqual(rightbrain.selector_model_load_error, "")

    def test_wrong_shadow_preference_cannot_take_over_visible_reply(self):
        rightbrain = build_rightbrain(["好了、既読だけ気にするな。<|im_end|>"])
        logic = reply_anxiety_logic()

        def prefer_polluted(_model, candidate, _payload):
            return 0.99 if "好了" in candidate["text"] else 0.01

        with patch("uruha_brain_mac.score_learned_repair_candidate", side_effect=prefer_polluted):
            reply = rightbrain.speak(
                "他已讀但沒回，是不是我講錯話？",
                logic,
                MEMORY,
                {"mood": 0, "trust": 50},
            )

        shadow = logic["model_surface_selector_shadow"]
        self.assertNotIn("好了", reply)
        self.assertEqual(shadow["status"], "active")
        self.assertTrue(shadow["learned_selected_was_gate_rejected"])
        self.assertFalse(shadow["learned_selected_strict_valid"])
        self.assertTrue(shadow["would_change_output"])
        self.assertFalse(shadow["changes_user_visible_reply"])
        self.assertEqual(reply, logic["model_surface_selection"]["selected_candidate"])

    def test_shadow_can_be_disabled_as_a_clean_ablation(self):
        rightbrain = build_rightbrain(["好了、既読だけ気にするな。<|im_end|>"])
        rightbrain.selector_shadow_enabled = False
        logic = reply_anxiety_logic()

        reply = rightbrain.speak(
            "他已讀但沒回，是不是我講錯話？",
            logic,
            MEMORY,
            {"mood": 0, "trust": 50},
        )

        shadow = logic["model_surface_selector_shadow"]
        self.assertNotIn("好了", reply)
        self.assertEqual(shadow["status"], "disabled")
        self.assertFalse(shadow["enabled"])
        self.assertFalse(shadow["changes_user_visible_reply"])

    def test_valid_shadow_disagreement_is_recorded_without_takeover(self):
        model_reply = "既読のままだと気になるよな。でも理由はまだ分からない。自分のせいと決めつけず、急がず少し待て。"
        rightbrain = build_rightbrain([model_reply + "<|im_end|>"])
        rightbrain.model_selection_margin = 999.0
        logic = reply_anxiety_logic()

        def prefer_model(_model, candidate, _payload):
            return 0.99 if "急がず" in candidate["text"] else 0.01

        with patch("uruha_brain_mac.score_learned_repair_candidate", side_effect=prefer_model):
            reply = rightbrain.speak(
                "他已讀但沒回，是不是我講錯話？",
                logic,
                MEMORY,
                {"mood": 0, "trust": 50},
            )

        shadow = logic["model_surface_selector_shadow"]
        self.assertNotIn("急がず", reply)
        self.assertTrue(shadow["learned_selected_strict_valid"])
        self.assertFalse(shadow["learned_selected_was_gate_rejected"])
        self.assertTrue(shadow["would_change_output"])
        self.assertIn("急がず", shadow["learned_selected_text"])
        self.assertFalse(shadow["changes_user_visible_reply"])

    def test_real_generated_holdout_replay_passes_shadow_gate(self):
        source_report = json.loads(
            Path(RIGHTBRAIN_REPAIR_SELECTOR_V1_NATURAL_HOLDOUT_SOURCE_PATH).read_text(encoding="utf-8")
        )
        report = build_shadow_report(source_report)

        self.assertTrue(report["gate_passed"], msg=report["gate"])
        self.assertEqual(report["summary"]["learned_strict_valid_rate"], 1.0)
        self.assertEqual(report["summary"]["learned_gate_rejected_selection_count"], 0)
        self.assertEqual(report["summary"]["user_visible_output_unchanged_rate"], 1.0)
        self.assertGreater(report["summary"]["input_rejected_candidate_count"], 0)


if __name__ == "__main__":
    unittest.main()
