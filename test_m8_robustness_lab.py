from __future__ import annotations

import unittest

from uruha_robustness_lab import render_robustness_lab, rolling_cutoff_choices


class RobustnessLabTests(unittest.TestCase):
    def test_four_cutoffs_and_negative_scientific_result_render(self):
        self.assertEqual(4,len(rolling_cutoff_choices()))
        html=render_robustness_lab("E4")
        self.assertIn("1 / 8 HYPOTHESES",html)
        self.assertIn("108 / 108 CALLS",html)
        self.assertIn("D7_ALL_AVAILABLE",html)
        self.assertIn("B5",html)

    def test_e4_failures_and_m7_sign_reversals_are_visible(self):
        html=render_robustness_lab("E4")
        self.assertIn("E4-02",html)
        self.assertIn("M7 removal helped; M8 removal harms",html)
        self.assertIn("下一步 M9",html)


if __name__=="__main__": unittest.main()
