import json
import tempfile
import unittest
from pathlib import Path

from probe_rightbrain_group_preference_v26 import (
    build_probe_decision,
    load_groups,
)


def _split_summary():
    return {
        "source_overlap_count": 0,
        "train_group_count": 8,
        "eval_source_ids": ["a", "b"],
    }


def _eval_metrics(preference_rate=0.6):
    return {
        "group_count": 4,
        "candidate_count": 24,
        "pair_count": 20,
        "pairwise_positive_preference_rate": preference_rate,
        "all_log_probs_finite": True,
    }


class RightBrainGroupPreferenceProbeV26Test(unittest.TestCase):
    def test_probe_authorizes_only_source_separated_unsaturated_groups(self):
        decision = build_probe_decision(
            {"authorize_group_probe": True},
            _split_summary(),
            _eval_metrics(),
        )

        self.assertTrue(decision["authorize_group_training"])
        self.assertEqual(decision["eval_misranked_pair_count"], 8)

    def test_probe_blocks_saturated_reference_ranking(self):
        decision = build_probe_decision(
            {"authorize_group_probe": True},
            _split_summary(),
            _eval_metrics(preference_rate=1.0),
        )

        self.assertFalse(decision["authorize_group_training"])
        self.assertFalse(
            decision["gates"]["unseen_pairwise_preference_is_not_saturated"]
        )

    def test_loader_rejects_candidate_id_reused_across_groups(self):
        group = {
            "id": "g1",
            "source_case_id": "source-a",
            "source_prompt_id": "prompt-a",
            "prompt_messages": [{"role": "system"}, {"role": "user"}],
            "positives": [{"id": "candidate", "text": "positive"}],
            "negatives": [{"id": "negative", "text": "negative"}],
        }
        second = json.loads(json.dumps(group))
        second["id"] = "g2"
        second["source_prompt_id"] = "prompt-b"
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "groups.json"
            path.write_text(json.dumps([group, second]), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Invalid candidate"):
                load_groups(path)


if __name__ == "__main__":
    unittest.main()
