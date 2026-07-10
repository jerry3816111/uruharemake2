import unittest

from eval_rightbrain_hard_negative_preference_v20_final import build_report


class RightBrainHardNegativePreferenceV20FinalDecisionTest(unittest.TestCase):
    def test_rejects_synthetic_pass_that_does_not_transfer_to_runtime(self):
        dataset = {
            "pair_count": 32,
            "family_spec_count": 8,
            "all_pairs_single_slot_omission": True,
            "all_pairs_length_matched": True,
            "data_boundary": {
                "holdout_case_overlap_count": 0,
                "holdout_target_overlap_count": 0,
            },
        }
        training = {
            "output_adapter_ref": "v20",
            "epochs": 1.0,
            "optimizer_updates": 6,
            "nonfinite_skips": 0,
            "initial_eval_preference": {
                "chosen_preference_rate": 1.0,
                "mean_raw_preference_margin": 1.25,
            },
            "final_eval_preference": {
                "chosen_preference_rate": 1.0,
                "mean_raw_preference_margin": 1.27,
            },
        }
        pre_holdout = {"authorize_actual_model_holdout": True}
        runtime = {
            "promotion_recommended": False,
            "quality_guard_pass": False,
            "all_seed_noninferior": False,
            "all_seed_selection_noninferior": False,
            "seeds": [1, 2],
            "aggregate": {
                "raw_candidate_acceptance_delta": -0.05,
                "baseline": {
                    "case_count": 22,
                    "generated_candidate_count": 60,
                    "accepted_candidate_count": 26,
                    "raw_candidate_acceptance_rate": 0.4333,
                    "model_selected_case_count": 3,
                    "final_quality_pass_rate": 1.0,
                },
                "promoted": {
                    "case_count": 22,
                    "generated_candidate_count": 60,
                    "accepted_candidate_count": 23,
                    "raw_candidate_acceptance_rate": 0.3833,
                    "model_selected_case_count": 2,
                    "final_quality_pass_rate": 0.9546,
                },
            },
            "rejection_reason_deltas": {
                "family": [
                    {
                        "reason": "semantic_slots_missing",
                        "baseline_count": 10,
                        "candidate_count": 17,
                        "delta": 7,
                    }
                ]
            },
        }

        report = build_report(dataset, training, pre_holdout, runtime, "v10")

        self.assertFalse(report["gates"]["promote_adapter"])
        self.assertTrue(report["diagnosis"]["synthetic_to_runtime_transfer_gap"])
        self.assertEqual(report["runtime_evidence"]["raw_candidate_acceptance_delta"], -0.05)
        self.assertEqual(report["baseline_adapter"], "v10")


if __name__ == "__main__":
    unittest.main()
