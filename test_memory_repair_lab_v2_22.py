import inspect
import unittest

import uruha_memory_repair_lab as lab
import uruha_web_ui


class MemoryRepairLabV222Test(unittest.TestCase):
    def test_default_view_is_failure_transparent(self):
        html = lab.render_memory_repair_lab("50")
        self.assertIn("三個錯誤修掉兩個，最後一個還在", html)
        self.assertIn("4 / 5 · GATE FAILED", html)
        self.assertIn("PARTIAL · T50", html)
        self.assertIn("T41 不在 recent 8", html)
        self.assertIn("人物來源仍會因檢索視窗漏失", html)

    def test_view_contains_three_current_comparison_arms(self):
        html = lab.render_memory_repair_lab("48")
        self.assertIn("UruhaBrain · 修正後", html)
        self.assertIn("單純 LLM · 最近 8 輪", html)
        self.assertIn("單純 LLM · 完整 50 輪", html)
        self.assertIn("ほうじ茶", html)

    def test_timeline_has_fifty_turns_and_all_choices(self):
        html = lab.render_memory_repair_lab("26")
        self.assertEqual(html.count('<div class="rp-turn'), 50)
        self.assertEqual([value for _, value in lab.checkpoint_choices()], ["25", "26", "48", "49", "50"])

    def test_t50_shows_real_before_and_after_answers(self):
        html = lab.render_memory_repair_lab("50")
        self.assertIn("レモネードが好きなんだな", html)
        self.assertIn("お前がレモネードを一番好きとは聞いてない", html)
        self.assertIn("レモネードが本命って記録はない", html)

    def test_web_places_repair_lab_before_historical_comparison(self):
        source = inspect.getsource(uruha_web_ui.build_demo)
        self.assertIn('gr.Tab("50-Turn Repair")', source)
        self.assertLess(
            source.index('gr.Tab("50-Turn Repair")'),
            source.index('gr.Tab("50-Turn A/B")'),
        )
        self.assertIn("memory_repair_checkpoint.change", source)


if __name__ == "__main__":
    unittest.main()
