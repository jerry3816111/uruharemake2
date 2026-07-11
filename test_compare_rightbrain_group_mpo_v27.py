import unittest

from compare_rightbrain_group_mpo_v27 import CONTROLLED_FIELDS, build_comparison


def _training(learning_rate):
    report = {field: f"fixed-{field}" for field in CONTROLLED_FIELDS}
    report.update(
        {
            "learning_rate": learning_rate,
            "epochs": 1.0,
            "optimizer_updates": 8,
            "nonfinite_skips": 0,
            "max_observed_gradient_norm": 10.0,
        }
    )
    return report


def _decision(final_absolute, relative, mass_gain):
    return {
        "runtime_adapter_before": "v10",
        "runtime_adapter_after": "v10",
        "run_actual_model_holdout": False,
        "gates": {"a": True, "b": False},
        "metrics": {
            "final_train_pairwise_preference": 0.6,
            "final_eval_pairwise_preference": relative,
            "initial_eval_absolute_policy_ranking": {
                "pairwise_positive_preference_rate": 0.25,
                "mean_positive_negative_margin": -1.0,
            },
            "final_eval_absolute_policy_ranking": {
                "pairwise_positive_preference_rate": final_absolute,
                "mean_positive_negative_margin": -0.9,
            },
            "eval_positive_mass_gain": mass_gain,
            "positive_likelihood": {
                "mean_positive_average_log_prob_delta": 0.01,
            },
        },
    }


class RightBrainGroupMPOV27ComparisonTest(unittest.TestCase):
    def test_rejects_higher_lr_when_only_variable_and_absolute_ranking_worsens(self):
        report = build_comparison(
            _training(1e-7),
            _decision(0.25, 0.79, 0.006),
            _training(3e-7),
            _decision(0.20, 0.62, 0.004),
        )

        self.assertTrue(report["only_learning_rate_changed"])
        self.assertEqual(report["decision"], "reject_learning_rate_increase")
        self.assertFalse(report["run_actual_model_holdout"])
        self.assertEqual(report["runtime_adapter_after"], "v10")

    def test_controlled_field_mismatch_makes_comparison_inconclusive(self):
        v27_training = _training(3e-7)
        v27_training["seed"] = "changed"
        report = build_comparison(
            _training(1e-7),
            _decision(0.25, 0.79, 0.006),
            v27_training,
            _decision(0.20, 0.62, 0.004),
        )

        self.assertFalse(report["only_learning_rate_changed"])
        self.assertEqual(report["decision"], "inconclusive")
        self.assertIn("seed", report["controlled_field_mismatches"])


if __name__ == "__main__":
    unittest.main()
