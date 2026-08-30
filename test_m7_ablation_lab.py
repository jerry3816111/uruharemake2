from __future__ import annotations

import unittest

from uruha_ablation_lab import ablation_component_choices, render_ablation_lab


class AblationLabTests(unittest.TestCase):
    def test_all_ten_components_and_claim_boundary_render(self):
        self.assertEqual(10, len(ablation_component_choices()))
        html = render_ablation_lab("habit")
        self.assertIn("10 / 10 COMPONENTS", html)
        self.assertIn("DIAGNOSTIC · NOT NEW LIFT", html)
        self.assertIn("habit", html)
        self.assertIn("0 model calls", html)

    def test_negative_temporal_result_and_quiet_success_flip_remain_visible(self):
        html = render_ablation_lab("temporal_dynamics")
        self.assertIn("可能有噪音", html)
        self.assertIn("quiet_success", html)
        self.assertIn("correct p 22.5%", html)
        self.assertIn("correct p 99.995%", html)
        self.assertIn("Δ +0.775", html)
        self.assertNotIn('{quiet[', html)


if __name__ == "__main__":
    unittest.main()
