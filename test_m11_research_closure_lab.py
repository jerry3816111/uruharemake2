import unittest

import uruha_research_closure_lab as closure


class M11ResearchClosureLabTests(unittest.TestCase):
    def test_all_hash_bound_sources_and_twelve_stages_load(self):
        payload = closure.load_evidence_map()
        self.assertEqual(len(payload["stages"]), 12)
        self.assertEqual(len(payload["sources"]), 13)
        self.assertEqual(payload["maturity_axes"][2]["percent_high"], 0)

    def test_negative_results_and_zero_human_counts_are_visible(self):
        html = closure.render_research_closure("M9")
        self.assertIn("full adaptation 43.75% &lt; B4/B5 75%", html)
        self.assertIn("formal Uruha evidence 0%", html)
        self.assertIn("0/3 language raters", html)
        self.assertIn("系統已穩定優於相同基礎模型", html)
        self.assertIn("M8/M9 負結果必須被解決或接受", html)

    def test_each_stage_is_switchable_and_selected_detail_changes(self):
        for stage_id in closure.closure_stage_choices():
            html = closure.render_research_closure(stage_id)
            self.assertIn(f"{stage_id} ·", html)
            self.assertEqual(html.count(" selected'>"), 1)


if __name__ == "__main__":
    unittest.main()
