import unittest

import torch

from train_uruha_rightbrain_simpo_v19 import (
    add_chosen_nll,
    assign_prompt_balance_weights,
    research_boundary,
    simpo_loss,
)


class RightBrainSimPOV19Test(unittest.TestCase):
    def test_research_boundary_records_both_local_ablation_limits(self):
        boundary = research_boundary(True, 1.0)

        self.assertIn("inverse-multiplicity", boundary)
        self.assertIn("optional SFT regularization", boundary)
        self.assertIn("not a full GroupDPO reproduction", boundary)
        self.assertIn("actual-model holdouts", boundary)

    def test_chosen_nll_regularizer_preserves_zero_weight_baseline(self):
        preference_loss = torch.tensor(0.7)
        chosen_average = torch.tensor([-2.0])

        baseline, chosen_nll = add_chosen_nll(preference_loss, chosen_average, 0.0)
        regularized, _ = add_chosen_nll(preference_loss, chosen_average, 1.0)

        self.assertAlmostEqual(float(chosen_nll), 2.0)
        self.assertAlmostEqual(float(baseline), 0.7, places=6)
        self.assertAlmostEqual(float(regularized), 2.7, places=6)

    def test_prompt_balance_equalizes_total_weight_without_changing_mean(self):
        rows = [
            {"id": "a1", "source_case_id": "family-a", "source_prompt_id": "prompt-a"},
            {"id": "a2", "source_case_id": "family-a", "source_prompt_id": "prompt-a"},
            {"id": "a3", "source_case_id": "family-a", "source_prompt_id": "prompt-a"},
            {"id": "b1", "source_case_id": "family-b", "source_prompt_id": "prompt-b"},
        ]

        summary = assign_prompt_balance_weights(rows, enabled=True)

        self.assertAlmostEqual(summary["sample_weight_mean"], 1.0)
        self.assertAlmostEqual(rows[0]["sample_weight"], 2 / 3)
        self.assertAlmostEqual(rows[3]["sample_weight"], 2.0)
        self.assertAlmostEqual(summary["prompt_weight_totals"]["prompt-a"], 2.0)
        self.assertAlmostEqual(summary["prompt_weight_totals"]["prompt-b"], 2.0)
        self.assertAlmostEqual(summary["post_balance_prompt_weight_spread"], 0.0)

    def test_disabled_prompt_balance_preserves_pairwise_weights(self):
        rows = [
            {"id": "a1", "source_case_id": "family-a", "source_prompt_id": "prompt-a"},
            {"id": "a2", "source_case_id": "family-a", "source_prompt_id": "prompt-a"},
            {"id": "b1", "source_case_id": "family-b", "source_prompt_id": "prompt-b"},
        ]

        summary = assign_prompt_balance_weights(rows, enabled=False)

        self.assertFalse(summary["enabled"])
        self.assertTrue(all(row["sample_weight"] == 1.0 for row in rows))
        self.assertEqual(summary["post_balance_prompt_weight_spread"], 1.0)

    def test_simpo_loss_rewards_average_log_probability_margin(self):
        weak_loss, weak_raw, weak_target = simpo_loss(
            torch.tensor([-2.0]),
            torch.tensor([-2.0]),
            beta=2.5,
            gamma=0.25,
        )
        strong_loss, strong_raw, strong_target = simpo_loss(
            torch.tensor([-1.7]),
            torch.tensor([-2.0]),
            beta=2.5,
            gamma=0.25,
        )

        self.assertAlmostEqual(float(weak_raw), 0.0)
        self.assertLess(float(weak_target), 0.0)
        self.assertGreater(float(strong_target), 0.0)
        self.assertLess(float(strong_loss), float(weak_loss))


if __name__ == "__main__":
    unittest.main()
