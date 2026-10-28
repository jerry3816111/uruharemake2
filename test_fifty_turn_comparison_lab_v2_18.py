import unittest

import uruha_fifty_turn_comparison_lab as lab


class FiftyTurnComparisonLabTest(unittest.TestCase):
    def test_default_view_is_failure_transparent_and_has_three_conditions(self):
        html = lab.render_fifty_turn_comparison("48")
        self.assertIn("FORMAL GATE FAILED", html)
        self.assertIn("UruhaBrain · 外部記憶", html)
        self.assertIn("單純 LLM · 最近 8 輪", html)
        self.assertIn("單純 LLM · 完整 50 輪", html)
        self.assertIn("日本語だけで、元の意味を落とさず言い直す", html)
        self.assertIn("favorite_drink", html)
        self.assertIn("カモミールティー", html)
        self.assertIn("錯誤發生在 final surface", html)

    def test_timeline_renders_all_fifty_turn_cells(self):
        html = lab.render_fifty_turn_comparison("25")
        self.assertEqual(html.count('<div class="fc-turn'), 50)
        self.assertIn("コーヒー", html)

    def test_false_memory_control_exposes_question_as_assertion_misparse(self):
        html = lab.render_fifty_turn_comparison("50")
        self.assertIn("current_preference_update", html)
        self.assertIn("疑問句錯當 current update", html)
        self.assertIn("朋友與使用者", html)
        self.assertIn("REVIEW FAIL", html)
        self.assertIn("凍結 auto proxy ✓", html)
        self.assertIn("人工複核：回答不完整或失敗", html)

    def test_choices_cover_all_comparison_checkpoints(self):
        self.assertEqual([value for _, value in lab.checkpoint_choices()], ["25", "26", "48", "49", "50"])


if __name__ == "__main__":
    unittest.main()
