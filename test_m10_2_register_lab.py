import unittest

from uruha_register_lab import DEFAULT_REGISTER_CASE_ID, register_case_choices, render_register_lab


class M102RegisterLabTests(unittest.TestCase):
    def test_renders_surface_gain_and_authority_cost(self):
        html = render_register_lab(DEFAULT_REGISTER_CASE_ID)
        self.assertIn("72% → 100%", html)
        self.assertIn("100% → 94.44%", html)
        self.assertIn("不能用自然度掩蓋", html)
        self.assertIn("0 raters", html)

    def test_all_cases_and_regression_are_switchable(self):
        self.assertEqual(len(register_case_choices()), 18)
        html = render_register_lab("R-JA-06")
        self.assertIn("同じミス三回もやらかすなら", html)
        self.assertIn("AUTHORITY REGRESSION", html)
        self.assertIn("defer_commitment", html)


if __name__ == "__main__":
    unittest.main()
