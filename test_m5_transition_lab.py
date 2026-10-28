from __future__ import annotations

import unittest

from uruha_transition_lab import render_transition_lab, transition_choices


class TransitionLabTests(unittest.TestCase):
    def test_all_holdout_scenarios_render_graphical_comparison(self):
        choices = transition_choices()
        self.assertEqual(8, len(choices))
        for _, example_id in choices:
            html = render_transition_lab(example_id)
            self.assertIn("T0 · 靜止", html)
            self.assertIn("T3 · LLM 感知＋學習", html)
            self.assertIn("T3 IS NOT THE WINNER", html)
            self.assertIn("沒有預測行為", html)
            self.assertIn("tr-dimension-grid", html)


if __name__ == "__main__":
    unittest.main()
