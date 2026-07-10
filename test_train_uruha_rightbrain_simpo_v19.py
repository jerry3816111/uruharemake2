import unittest

import torch

from train_uruha_rightbrain_simpo_v19 import simpo_loss


class RightBrainSimPOV19Test(unittest.TestCase):
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
