import unittest

from uruha_human_state_lab import DEFAULT_STATE_ID, render_human_state_lab, state_choices


class HumanStateLabTests(unittest.TestCase):
    def test_two_snapshots_are_selectable(self):
        choices = state_choices()
        self.assertEqual(2, len(choices))
        self.assertIn(DEFAULT_STATE_ID, [value for _, value in choices])

    def test_default_render_exposes_all_state_dimensions_and_boundaries(self):
        html = render_human_state_lab()
        for marker in (
            "M4 · TIMESTAMPED HUMANSTATE SNAPSHOT",
            "M4 SNAPSHOT · PASS",
            "NO TRANSITION / NO PREDICTOR",
            "Memory",
            "Emotion estimate",
            "Personality tendency",
            "Relationship",
            "Preference / value",
            "Goal",
            "Habit",
            "Context",
            "Uncertainty",
            "private_fatigue",
            "ROUNDTRIP REPLAY",
            "M5 · T0–T3",
            "現在不能宣稱",
        ):
            self.assertIn(marker, html)

    def test_switching_snapshot_changes_state_and_evidence(self):
        technical = render_human_state_lab("q06_technical")
        privacy = render_human_state_lab("q04_privacy")
        self.assertIn("diagnose_repeated_failure", technical)
        self.assertIn("protect_private_information", privacy)
        self.assertIn("memory:m11", technical)
        self.assertIn("memory:m07", privacy)
        self.assertNotEqual(technical, privacy)


if __name__ == "__main__":
    unittest.main()
