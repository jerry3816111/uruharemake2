from __future__ import annotations

import unittest

from uruha_behavior_predictor_lab import behavior_sample_choices, render_behavior_predictor_lab


class BehaviorPredictorLabTests(unittest.TestCase):
    def test_all_eight_holdouts_render_seven_conditions_and_pipeline(self):
        choices = behavior_sample_choices()
        self.assertEqual(8, len(choices))
        for _, sample_id in choices:
            html = render_behavior_predictor_lab(sample_id)
            self.assertIn("B5 · B5_STRUCTURED_HISTORY", html)
            self.assertIn("OURS · OURS_HYBRID", html)
            self.assertIn("BEHAVIOR LOGITS", html)
            self.assertIn("CALIBRATION", html)
            self.assertIn("no utterance generation", html)

    def test_quiet_success_failure_is_not_hidden(self):
        html = render_behavior_predictor_lab("quiet_success::holdout")
        self.assertIn("PRESERVED FAILURE", html)
        self.assertIn("direct_rejection", html)
        self.assertIn("acknowledge_then_continue", html)


if __name__ == "__main__":
    unittest.main()
