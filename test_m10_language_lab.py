import unittest

from uruha_language_lab import (
    DEFAULT_LANGUAGE_SAMPLE_ID,
    language_case_choices,
    render_language_lab,
)


class M10LanguageLabTests(unittest.TestCase):
    def test_renders_authority_outcome_and_oracle_boundary(self):
        html = render_language_lab(DEFAULT_LANGUAGE_SAMPLE_ID)
        self.assertIn("語言層會聽命", html)
        self.assertIn("87.5%", html)
        self.assertIn("56.25%", html)
        self.assertIn("ORACLE CEILING", html)
        self.assertIn("不能宣稱", html)
        self.assertIn("要求を断る。", html)

    def test_all_sixteen_cases_switch(self):
        choices = language_case_choices()
        self.assertEqual(len(choices), 16)
        html = render_language_lab("M-E2-03")
        self.assertIn("資料生成が三度も落ちた", html)
        self.assertIn("LLM bypassed authority", html)


if __name__ == "__main__":
    unittest.main()
