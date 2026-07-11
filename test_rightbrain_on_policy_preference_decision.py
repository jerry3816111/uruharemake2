import unittest

from eval_rightbrain_on_policy_preference_decision import (
    build_report,
    evaluate_candidate,
)


def _training_report(
    *,
    final_preference,
    final_target,
    margin_delta,
    chosen_delta,
    prompt_balance=False,
    chosen_nll_weight=0.0,
    optimizer_updates=1,
    nonfinite_skips=0,
):
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
        "method": "test_simpo",
        "base_model": "test-model",
        "dataset_sha256": "dataset-sha",
        "init_adapter_ref": "v10",
        "epochs": 1.0,
        "learning_rate": 1e-7,
        "beta": 2.5,
        "gamma_beta_ratio": 0.1,
        "seed": 7,
        "train_source_ids": ["train"],
        "eval_source_ids": ["eval"],
        "prompt_balance": {"enabled": prompt_balance},
        "chosen_nll_weight": chosen_nll_weight,
        "target_pair_steps": 4,
        "grad_accum": 4,
        "optimizer_updates": optimizer_updates,
        "nonfinite_skips": nonfinite_skips,
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

    def test_factorial_report_separates_clean_and_numerically_confounded_comparisons(self):
        common = {
            "final_target": 0.2,
            "chosen_delta": 0.01,
        }
        report = build_report(
            [
                (
                    "pairwise",
                    _training_report(
                        final_preference=0.4,
                        margin_delta=0.01,
                        **common,
                    ),
                ),
                (
                    "balanced",
                    _training_report(
                        final_preference=0.3,
                        margin_delta=-0.01,
                        prompt_balance=True,
                        **common,
                    ),
                ),
                (
                    "balanced+nll",
                    _training_report(
                        final_preference=0.4,
                        margin_delta=0.02,
                        prompt_balance=True,
                        chosen_nll_weight=1.0,
                        **common,
                    ),
                ),
                (
                    "pairwise+nll",
                    _training_report(
                        final_preference=0.5,
                        margin_delta=0.03,
                        chosen_nll_weight=1.0,
                        optimizer_updates=0,
                        nonfinite_skips=1,
                        **common,
                    ),
                ),
            ]
        )

        factorial = report["factorial_analysis"]
        self.assertTrue(factorial["complete_four_cell_design"])
        comparisons = {row["id"]: row for row in factorial["comparisons"]}
        self.assertTrue(
            comparisons["prompt_balance_without_nll"]["valid_single_factor_comparison"]
        )
        self.assertTrue(
            comparisons["chosen_nll_with_balance"]["valid_single_factor_comparison"]
        )
        self.assertFalse(
            comparisons["chosen_nll_without_balance"]["valid_single_factor_comparison"]
        )
        self.assertIn("排除因果解讀", report["diagnosis_zh"])


if __name__ == "__main__":
    unittest.main()
