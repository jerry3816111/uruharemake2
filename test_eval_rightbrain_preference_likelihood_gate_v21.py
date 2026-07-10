import unittest

from eval_rightbrain_preference_likelihood_gate_v21 import (
    preferred_likelihood_diagnostic,
    replay_training_report,
)


def _training_report(initial_chosen, final_chosen, *, margin_improved=True):
    initial_margin = 0.1
    final_margin = 0.2 if margin_improved else 0.05
    initial_rows = []
    final_rows = []
    for index, (before, after) in enumerate(zip(initial_chosen, final_chosen)):
        initial_rows.append(
            {
                "id": str(index),
                "chosen_average_log_prob": before,
                "rejected_average_log_prob": before - initial_margin,
                "raw_preference_margin": initial_margin,
            }
        )
        final_rows.append(
            {
                "id": str(index),
                "chosen_average_log_prob": after,
                "rejected_average_log_prob": after - final_margin,
                "raw_preference_margin": final_margin,
            }
        )
    return {
        "output_adapter_ref": "candidate",
        "source_overlap_count": 0,
        "eval_pair_count": len(initial_rows),
        "target_pair_steps": 8,
        "grad_accum": 4,
        "optimizer_updates": 2,
        "nonfinite_skips": 0,
        "max_observed_gradient_norm": 2.0,
        "initial_eval_preference": {
            "chosen_preference_rate": 0.75,
            "mean_raw_preference_margin": initial_margin,
            "target_margin_rate": 0.5,
            "rows": initial_rows,
        },
        "final_train_preference": {
            "chosen_preference_rate": 0.8,
            "mean_raw_preference_margin": 0.2,
            "target_margin_rate": 0.6,
        },
        "final_eval_preference": {
            "chosen_preference_rate": 0.75,
            "mean_raw_preference_margin": final_margin,
            "target_margin_rate": 0.5,
            "rows": final_rows,
        },
    }


class RightBrainPreferenceLikelihoodGateV21Test(unittest.TestCase):
    def test_diagnostic_detects_margin_improvement_with_preferred_displacement(self):
        report = _training_report([-1.0, -2.0], [-1.1, -2.2])

        diagnostic = preferred_likelihood_diagnostic(report)

        self.assertAlmostEqual(diagnostic["mean_chosen_average_log_prob_delta"], -0.15)
        self.assertEqual(diagnostic["preferred_likelihood_decreased_count"], 2)
        self.assertEqual(diagnostic["preferred_likelihood_decrease_rate"], 1.0)

    def test_new_gate_blocks_displacement_even_when_original_margin_gate_passes(self):
        report = _training_report(
            [-1.0, -2.0, -3.0, -4.0],
            [-1.1, -2.1, -3.1, -3.9],
        )

        replay = replay_training_report("candidate", report)

        self.assertTrue(replay["original_gate_authorized_holdout"])
        self.assertFalse(replay["v21_gate_authorizes_holdout"])
        self.assertFalse(
            replay["added_gates"]["unseen_mean_preferred_log_prob_non_decreasing"]
        )
        self.assertFalse(
            replay["added_gates"][
                "unseen_preferred_likelihood_decrease_rate_at_most_50pct"
            ]
        )

    def test_new_gate_allows_non_decreasing_preferred_likelihood(self):
        report = _training_report(
            [-1.0, -2.0, -3.0, -4.0],
            [-0.9, -2.1, -2.9, -3.9],
        )

        replay = replay_training_report("candidate", report)

        self.assertTrue(replay["v21_gate_authorizes_holdout"])


if __name__ == "__main__":
    unittest.main()
