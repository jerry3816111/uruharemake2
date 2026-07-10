import unittest

from eval_rightbrain_hard_negative_preference_v20 import build_report


class RightBrainHardNegativePreferenceV20DecisionTest(unittest.TestCase):
    def test_combines_data_and_training_gates(self):
        dataset = {
            "all_pairs_single_slot_omission": True,
            "all_pairs_length_matched": True,
            "data_boundary": {"diagnostic_only": False},
            "pair_count": 32,
            "length_profile_chars": {
                "mean_delta_rejected_minus_chosen": 1.0,
                "max_absolute_delta": 6,
                "mean_character_similarity": 0.65,
            },
        }
        training = {
            "output_adapter_ref": "v20",
            "source_overlap_count": 0,
            "target_pair_steps": 24,
            "grad_accum": 4,
            "optimizer_updates": 6,
            "nonfinite_skips": 0,
            "max_observed_gradient_norm": 2.0,
            "initial_eval_preference": {
                "chosen_preference_rate": 0.5,
                "mean_raw_preference_margin": -0.1,
                "target_margin_rate": 0.0,
            },
            "final_train_preference": {
                "chosen_preference_rate": 0.8,
                "mean_raw_preference_margin": 0.1,
                "target_margin_rate": 0.6,
            },
            "final_eval_preference": {
                "chosen_preference_rate": 0.75,
                "mean_raw_preference_margin": 0.02,
                "target_margin_rate": 0.5,
            },
        }

        report = build_report(dataset, training)

        self.assertTrue(report["authorize_actual_model_holdout"])
        self.assertTrue(all(report["gates"].values()))


if __name__ == "__main__":
    unittest.main()
