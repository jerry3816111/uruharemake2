import unittest

from uruha_structured_memory_lab import (
    DEFAULT_QUERY_ID,
    query_choices,
    render_structured_memory_lab,
)


class StructuredMemoryLabTests(unittest.TestCase):
    def test_choices_cover_six_queries(self):
        choices = query_choices()
        self.assertEqual(6, len(choices))
        self.assertIn(DEFAULT_QUERY_ID, [value for _, value in choices])

    def test_default_render_exposes_trace_ablation_and_boundaries(self):
        html = render_structured_memory_lab()
        for marker in (
            "M3 · STRUCTURED TEMPORAL MEMORY",
            "M3 MECHANISM · PASS",
            "m13_future".upper(),
            "event_after_cutoff",
            "m14_expired".upper(),
            "expired",
            "移除「語意相關」",
            "移除「情緒顯著」",
            "Recall@2 100.0%",
            "future 0 · expired 0",
            "M4 HumanState",
            "現在不能宣稱",
        ):
            self.assertIn(marker, html)

    def test_query_selection_changes_selected_memories(self):
        cooperation = render_structured_memory_lab("q01_cooperation")
        technical = render_structured_memory_lab("q06_technical")
        self.assertIn("M01 · SELECTED", cooperation)
        self.assertIn("M02 · SELECTED", cooperation)
        self.assertIn("M11 · SELECTED", technical)
        self.assertIn("M12 · SELECTED", technical)
        self.assertNotEqual(cooperation, technical)


if __name__ == "__main__":
    unittest.main()
