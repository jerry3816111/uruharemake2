import unittest

from eval_rightbrain_group_mpo_v26_decision import build_decision


def _metrics(
    *,
    pairwise,
    strict,
    top,
    mass,
    margin,
    positive_log_prob,
    negative_log_prob=-2.0,
    reference_delta=0.0,
):
    return {
        "pairwise_positive_preference_rate": pairwise,
        "strict_positive_separation_rate": strict,
        "positive_top1_rate": top,
        "mean_positive_probability_mass": mass,
        "mean_positive_negative_margin": margin,
        "max_abs_policy_reference_log_prob_delta": reference_delta,
        "groups": [
            {
                "id": "g1",
                "responses": [
                    {
                        "id": "p1",
                        "label": "positive",
                        "policy_average_log_prob": positive_log_prob,
                    },
                    {
                        "id": "n1",
                        "label": "negative",
                        "policy_average_log_prob": negative_log_prob,
                    },
                ],
            }
        ],
    }


def _training_report(
    nonfinite_skips=0,
    final_eval_positive_log_prob=-0.9,
    initial_positive_log_prob=-1.0,
    initial_negative_log_prob=-0.5,
):
    initial = _metrics(
        pairwise=0.0,
        strict=0.0,
        top=0.0,
        mass=0.50,
        margin=0.0,
        positive_log_prob=initial_positive_log_prob,
        negative_log_prob=initial_negative_log_prob,
    )
    return {
        "output_adapter_ref": "v26",
        "source_overlap_count": 0,
        "target_group_steps": 8,
        "optimizer_updates": 8,
        "nonfinite_skips": nonfinite_skips,
        "frozen_v10_absolute_eval_pairwise_preference_rate": 0.2647,
        "frozen_v10_absolute_eval_misranked_pair_count": 25,
        "initial_train_group_metrics": initial,
        "initial_eval_group_metrics": initial,
        "final_train_group_metrics": _metrics(
            pairwise=0.8,
            strict=0.5,
            top=0.8,
            mass=0.60,
            margin=0.2,
            positive_log_prob=-0.8,
            negative_log_prob=-0.9,
        ),
        "final_eval_group_metrics": _metrics(
            pairwise=0.8,
            strict=0.5,
            top=0.75,
            mass=0.56,
            margin=0.1,
            positive_log_prob=final_eval_positive_log_prob,
            negative_log_prob=-1.0,
        ),
    }


class RightBrainGroupMPOV26DecisionTest(unittest.TestCase):
    def test_complete_group_learning_only_authorizes_runtime_holdout(self):
        report = build_decision(_training_report())

        self.assertTrue(report["run_actual_model_holdout"])
        self.assertEqual(report["selected_candidate_for_holdout"], "v26")
        self.assertEqual(report["runtime_adapter_before"], report["runtime_adapter_after"])

    def test_nonfinite_training_blocks_holdout_even_when_scores_pass(self):
        report = build_decision(_training_report(nonfinite_skips=1))

        self.assertFalse(report["run_actual_model_holdout"])
        self.assertFalse(report["gates"]["nonfinite_training_events_are_zero"])
        self.assertIsNone(report["selected_candidate_for_holdout"])

    def test_worse_absolute_ranking_is_reported_as_rejection(self):
        report = build_decision(
            _training_report(
                final_eval_positive_log_prob=-1.2,
                initial_positive_log_prob=-0.4,
            )
        )

        self.assertFalse(report["run_actual_model_holdout"])
        self.assertIn("絕對錯排反而增加", report["diagnosis_zh"])
        self.assertIn("必須拒絕", report["diagnosis_zh"])


if __name__ == "__main__":
    unittest.main()
