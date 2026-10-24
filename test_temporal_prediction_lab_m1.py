import unittest

from uruha_temporal_prediction_lab import (
    DEFAULT_SAMPLE_ID,
    render_temporal_prediction_lab,
    sample_choices,
)


class TemporalPredictionLabTests(unittest.TestCase):
    def test_all_twelve_samples_are_selectable(self):
        self.assertEqual(12, len(sample_choices()))

    def test_default_render_shows_full_temporal_graph_and_claim_boundary(self):
        html = render_temporal_prediction_lab(DEFAULT_SAMPLE_ID)
        self.assertIn("TEMPORAL EVIDENCE GRAPH", html)
        self.assertIn("CUTOFF", html)
        self.assertIn("OBSERVED AFTER PREDICTION", html)
        self.assertIn("DATA_GATE_BLOCKED", html)
        self.assertIn("72 PREDICTIONS · B0–B5 COMPLETE", html)
        self.assertIn("現在不能宣稱", html)

    def test_render_contains_six_baselines_and_all_probability_labels(self):
        html = render_temporal_prediction_lab("s09")
        for label in ("B0｜", "B1｜", "B2｜", "B3｜", "B4｜", "B5｜"):
            self.assertIn(label, html)
        for label in ("承接後繼續", "玩笑卸壓／轉開", "延後承諾", "直接拒絕", "先問清楚", "暫停並重估"):
            self.assertIn(label, html)

    def test_failed_first_run_is_retained_visibly(self):
        html = render_temporal_prediction_lab("s03")
        self.assertIn("29 / 48 · INVALID", html)
        self.assertIn("nonfresh engineering rerun", html)

    def test_m1_boundary_is_archived_and_m2_is_visible(self):
        html = render_temporal_prediction_lab("s07")
        self.assertIn("M1 ONE-WEEK CHECKPOINT · ARCHIVED", html)
        self.assertIn("✓ M2｜強基線", html)


if __name__ == "__main__":
    unittest.main()
