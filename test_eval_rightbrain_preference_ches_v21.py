import unittest

import torch

from eval_rightbrain_preference_ches_v21 import (
    _pearson,
    length_normalized_ches,
    training_delta_map,
)


class RightBrainPreferenceChesV21Test(unittest.TestCase):
    def test_length_normalized_ches_matches_centered_hidden_formula(self):
        preferred = torch.tensor(
            [[[1.0, 0.0], [2.0, 0.0], [4.0, 0.0], [99.0, 99.0]]]
        )
        dispreferred = torch.tensor(
            [[[0.0, 1.0], [2.0, 2.0], [6.0, 0.0], [88.0, 88.0]]]
        )
        completion_mask = torch.tensor([[False, False, True, True]])

        score = length_normalized_ches(
            preferred,
            dispreferred,
            completion_mask,
            completion_mask,
        )

        preferred_mean = torch.tensor([3.0, 0.0])
        dispreferred_mean = torch.tensor([4.0, 1.0])
        expected = torch.dot(preferred_mean, dispreferred_mean) - torch.dot(
            preferred_mean,
            preferred_mean,
        )
        self.assertAlmostEqual(float(score), float(expected))

    def test_training_delta_map_preserves_per_pair_likelihood_changes(self):
        report = {
            "initial_eval_preference": {
                "rows": [
                    {
                        "id": "a",
                        "chosen_average_log_prob": -2.0,
                        "rejected_average_log_prob": -3.0,
                        "raw_preference_margin": 1.0,
                    }
                ]
            },
            "final_eval_preference": {
                "rows": [
                    {
                        "id": "a",
                        "chosen_average_log_prob": -2.2,
                        "rejected_average_log_prob": -3.4,
                        "raw_preference_margin": 1.2,
                    }
                ]
            },
        }

        delta = training_delta_map(report)["a"]

        self.assertAlmostEqual(delta["chosen_average_log_prob_delta"], -0.2)
        self.assertAlmostEqual(delta["rejected_average_log_prob_delta"], -0.4)
        self.assertAlmostEqual(delta["raw_preference_margin_delta"], 0.2)

    def test_pearson_reports_direction(self):
        self.assertAlmostEqual(_pearson([1.0, 2.0, 3.0], [3.0, 2.0, 1.0]), -1.0)


if __name__ == "__main__":
    unittest.main()
