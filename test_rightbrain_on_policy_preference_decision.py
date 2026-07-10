import unittest

from eval_rightbrain_on_policy_preference_decision import (
    build_report,
    evaluate_candidate,
)


def _training_report(*, final_preference, final_target, margin_delta, chosen_delta):
    initial_rows = [
        {"id": f"pair_{index}", "chosen_average_log_prob": -2.0}
        for index in range(4)
    ]
    final_rows = [
        {
            "id": f"pair_{index}",
            "chosen_average_log_prob": -2.0 + chosen_delta,
        }
        for index in range(4)
    ]
    return {
        "output_adapter_ref": "candidate",
        "epochs": 1.0,
        "learning_rate": 1e-7,
        "target_pair_steps": 4,
        "grad_accum": 4,
        "optimizer_updates": 1,
        "nonfinite_skips": 0,
        "max_observed_gradient_norm": 1.0,
        "source_overlap_count": 0,
        "eval_pair_count": 4,
        "initial_eval_preference": {
            "chosen_preference_rate": 0.5,
            "target_margin_rate": 0.25,
            "mean_raw_preference_margin": -0.2,
            "rows": initial_rows,
        },
        "final_train_preference": {"chosen_preference_rate": 0.8},
        "final_eval_preference": {
            "chosen_preference_rate": final_preference,
            "target_margin_rate": final_target,
            "mean_raw_preference_margin": -0.2 + margin_delta,
            "rows": final_rows,
        },
    }


class RightBrainOnPolicyPreferenceDecisionTest(unittest.TestCase):
    def test_candidate_requires_learning_and_likelihood_gates(self):
        row = evaluate_candidate(
            "pass",
            _training_report(
                final_preference=0.8,
                final_target=0.6,
                margin_delta=0.1,
                chosen_delta=0.1,
            ),
        )

        self.assertTrue(row["authorize_actual_model_holdout"])

    def test_failed_candidate_keeps_v10_and_blocks_holdout(self):
        report = build_report(
            [
                (
                    "fail",
                    _training_report(
                        final_preference=0.4,
                        final_target=0.2,
                        margin_delta=0.01,
                        chosen_delta=0.01,
                    ),
                )
            ]
        )

        self.assertEqual(report["authorized_candidate_count"], 0)
        self.assertFalse(report["run_actual_model_holdout"])
        self.assertEqual(report["runtime_adapter_after"], report["runtime_adapter_before"])


if __name__ == "__main__":
    unittest.main()
