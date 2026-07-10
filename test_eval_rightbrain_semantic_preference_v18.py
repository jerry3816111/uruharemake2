import copy
import unittest

from eval_rightbrain_semantic_preference_v18 import build_report


def _dataset_report():
    return {
        "data_boundary": {"diagnostic_only": False},
        "length_profile_chars": {
            "chosen_mean": 30.0,
            "rejected_mean": 18.0,
            "mean_delta": 12.0,
            "chosen_longer_pair_count": 32,
        },
    }


def _training_report():
    return {
        "output_adapter_ref": "v18",
        "source_overlap_count": 0,
        "optimizer_updates": 6,
        "target_pair_steps": 24,
        "grad_accum": 4,
        "nonfinite_skips": 0,
        "max_observed_gradient_norm": 1.0,
        "final_train_preference": {
            "positive_reward_margin_rate": 0.9,
            "mean_reward_margin": 0.1,
        },
        "final_eval_preference": {
            "positive_reward_margin_rate": 0.75,
            "mean_reward_margin": 0.02,
        },
    }


class RightBrainSemanticPreferenceV18DecisionTest(unittest.TestCase):
    def test_authorizes_only_stable_heldout_preference_gain(self):
        report = build_report(_dataset_report(), _training_report())

        self.assertTrue(report["authorize_actual_model_holdout"])
        self.assertTrue(all(report["gates"].values()))

    def test_blocks_nonfinite_and_weak_unseen_margin(self):
        training = copy.deepcopy(_training_report())
        training["optimizer_updates"] = 5
        training["nonfinite_skips"] = 1
        training["final_train_preference"]["mean_reward_margin"] = -0.01
        training["final_eval_preference"]["positive_reward_margin_rate"] = 0.5

        report = build_report(_dataset_report(), training)

        self.assertFalse(report["authorize_actual_model_holdout"])
        self.assertFalse(report["gates"]["nonfinite_training_events_are_zero"])
        self.assertIn("SimPO", report["next_method"]["name"])


if __name__ == "__main__":
    unittest.main()
