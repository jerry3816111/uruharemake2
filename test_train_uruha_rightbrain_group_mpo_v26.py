import json
import tempfile
import unittest
from pathlib import Path

import torch

from train_uruha_rightbrain_contract_v1 import _sha256
from train_uruha_rightbrain_group_mpo_v26 import (
    attach_reference_scores,
    mpo_coefficients,
    mpo_loss,
    validate_probe,
    validate_probe_split,
)


class RightBrainGroupMPOV26Test(unittest.TestCase):
    def test_surrogate_coefficients_match_direct_mpo_gradient(self):
        scores = torch.tensor(
            [0.2, -0.1, 0.3, -0.4],
            dtype=torch.float64,
            requires_grad=True,
        )
        positive_mask = torch.tensor([True, True, False, False])

        loss = mpo_loss(scores, positive_mask)
        loss.backward()
        coefficients = mpo_coefficients(scores.detach(), positive_mask)

        self.assertTrue(torch.allclose(scores.grad, coefficients, atol=1e-7))
        self.assertAlmostEqual(float(coefficients.sum()), 0.0, places=7)

    def test_mpo_rewards_probability_mass_on_any_valid_response(self):
        positive_mask = torch.tensor([True, True, False, False])
        baseline = mpo_loss(torch.zeros(4), positive_mask)
        improved = mpo_loss(
            torch.tensor([0.8, 0.4, -0.2, -0.4]),
            positive_mask,
        )

        self.assertLess(float(improved), float(baseline))

    def test_probe_guard_binds_dataset_and_adapter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dataset = Path(tmpdir) / "dataset.json"
            probe = Path(tmpdir) / "probe.json"
            adapter = Path(tmpdir) / "v10"
            dataset.write_text("[]\n", encoding="utf-8")
            adapter.mkdir()
            adapter_model = adapter / "adapter_model.safetensors"
            adapter_model.write_bytes(b"v10 weights")
            probe.write_text(
                json.dumps(
                    {
                        "dataset_sha256": _sha256(dataset),
                        "init_adapter_ref": "v10",
                        "init_adapter_model_sha256": _sha256(adapter_model),
                        "decision": {"authorize_group_training": True},
                    }
                ),
                encoding="utf-8",
            )

            validate_probe(dataset, probe, adapter)
            adapter_model.write_bytes(b"different weights")
            with self.assertRaisesRegex(ValueError, "weights changed"):
                validate_probe(dataset, probe, adapter)
            adapter_model.write_bytes(b"v10 weights")
            dataset.write_text("[{}]\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "changed after"):
                validate_probe(dataset, probe, adapter)

    def test_reference_attachment_requires_every_candidate(self):
        groups = [
            {
                "id": "g1",
                "responses": [
                    {"id": "p1", "label": "positive"},
                    {"id": "n1", "label": "negative"},
                ],
            }
        ]
        probe = {
            "initial_train_absolute_group_metrics": {
                "groups": [
                    {
                        "id": "g1",
                        "responses": [
                            {"id": "p1", "average_log_prob": -1.0},
                            {"id": "n1", "average_log_prob": -2.0},
                        ],
                    }
                ]
            },
            "initial_eval_absolute_group_metrics": {"groups": []},
        }

        self.assertEqual(attach_reference_scores(groups, probe), 2)
        self.assertEqual(groups[0]["responses"][0]["reference_average_log_prob"], -1.0)

    def test_training_split_must_match_frozen_probe(self):
        probe = {
            "base_model": "base",
            "max_length": 720,
            "seed": 7,
            "train_source_ids": ["train"],
            "eval_source_ids": ["eval"],
        }

        validate_probe_split(
            probe,
            base_model="base",
            max_length=720,
            seed=7,
            train_sources=["train"],
            eval_sources=["eval"],
        )
        with self.assertRaisesRegex(ValueError, "differs"):
            validate_probe_split(
                probe,
                base_model="base",
                max_length=720,
                seed=8,
                train_sources=["train"],
                eval_sources=["eval"],
            )


if __name__ == "__main__":
    unittest.main()
