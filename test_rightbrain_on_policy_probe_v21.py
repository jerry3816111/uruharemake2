import json
import tempfile
import unittest
from pathlib import Path

from probe_rightbrain_on_policy_preference_v21 import build_probe_decision
from train_uruha_rightbrain_contract_v1 import _sha256
from train_uruha_rightbrain_simpo_v21 import requested_dataset, validate_probe


def _dataset_summary():
    return {"authorize_preference_probe": True}


def _split_summary():
    return {
        "source_overlap_count": 0,
        "eval_source_ids": ["family_a", "family_b"],
    }


def _metrics(margins):
    return {
        "pair_count": len(margins),
        "chosen_preference_rate": sum(value > 0 for value in margins) / len(margins),
        "target_margin_rate": sum(value > 0.1 for value in margins) / len(margins),
        "rows": [
            {
                "raw_preference_margin": value,
                "target_reward_margin": value - 0.1,
            }
            for value in margins
        ],
    }


class RightBrainOnPolicyProbeV21Test(unittest.TestCase):
    def test_training_guard_reads_actual_dataset_override(self):
        self.assertEqual(
            requested_dataset(["--epochs", "2", "--dataset", "custom.json"]),
            "custom.json",
        )

    def test_probe_allows_training_only_with_unseen_misranking(self):
        decision = build_probe_decision(
            _dataset_summary(),
            _split_summary(),
            _metrics([0.2, -0.1, 0.3, 0.4]),
            _metrics([0.2, -0.1, 0.3, 0.4]),
        )

        self.assertTrue(decision["authorize_training"])
        self.assertEqual(decision["eval_misranked_pair_count"], 1)

    def test_probe_blocks_saturated_unseen_pairs(self):
        decision = build_probe_decision(
            _dataset_summary(),
            _split_summary(),
            _metrics([0.2, 0.3, 0.4, 0.5]),
            _metrics([0.2, 0.3, 0.4, 0.5]),
        )

        self.assertFalse(decision["authorize_training"])
        self.assertFalse(decision["gates"]["unseen_preference_is_not_saturated"])

    def test_training_guard_binds_probe_to_exact_dataset(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dataset_path = Path(tmpdir) / "dataset.json"
            probe_path = Path(tmpdir) / "probe.json"
            dataset_path.write_text("[]\n", encoding="utf-8")
            probe_path.write_text(
                json.dumps(
                    {
                        "dataset_sha256": _sha256(dataset_path),
                        "decision": {"authorize_training": True},
                    }
                ),
                encoding="utf-8",
            )

            validate_probe(dataset_path, probe_path)
            dataset_path.write_text("[{}]\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "changed after"):
                validate_probe(dataset_path, probe_path)


if __name__ == "__main__":
    unittest.main()
