import json
import tempfile
import unittest
from pathlib import Path

import torch

from train_uruha_rightbrain_dpo_v18 import (
    dpo_loss,
    load_preference_rows,
    split_by_source,
    tokenize_pair,
)


class _Tokens:
    def __init__(self, ids):
        self.input_ids = ids


class FakeTokenizer:
    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True):
        return "PROMPT"

    def __call__(self, text, add_special_tokens=False):
        return _Tokens(list(range(1, len(text) + 1)))


def _row(index, source="source-a"):
    return {
        "id": f"row-{index}",
        "source_case_id": source,
        "source_prompt_id": f"prompt-{index}",
        "prompt_messages": [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "user"},
        ],
        "chosen": "complete",
        "rejected": "short",
        "pair_diagnostics": {"required_group_count": 3, "rejected_hit_count": 2},
    }


class RightBrainDPOV18Test(unittest.TestCase):
    def test_dpo_loss_rewards_increased_policy_margin(self):
        neutral_loss, neutral_margin = dpo_loss(
            torch.tensor([2.0]),
            torch.tensor([1.0]),
            torch.tensor([2.0]),
            torch.tensor([1.0]),
            beta=0.1,
        )
        better_loss, better_margin = dpo_loss(
            torch.tensor([3.0]),
            torch.tensor([1.0]),
            torch.tensor([2.0]),
            torch.tensor([1.0]),
            beta=0.1,
        )

        self.assertAlmostEqual(float(neutral_margin), 0.0)
        self.assertGreater(float(better_margin), 0.0)
        self.assertLess(float(better_loss), float(neutral_loss))

    def test_split_is_source_separated(self):
        rows = [_row(index, f"source-{index // 2}") for index in range(8)]

        train, evaluation, train_sources, eval_sources = split_by_source(
            rows,
            seed=7,
            eval_source_count=1,
        )

        self.assertTrue(train)
        self.assertTrue(evaluation)
        self.assertFalse(set(train_sources) & set(eval_sources))
        self.assertFalse(
            {row["source_case_id"] for row in train}
            & {row["source_case_id"] for row in evaluation}
        )

    def test_tokenization_masks_prompt_and_keeps_completion(self):
        tokenized = tokenize_pair(_row(1), FakeTokenizer(), max_length=64)

        chosen = tokenized["chosen"]
        self.assertEqual(tokenized["source_prompt_id"], "prompt-1")
        self.assertEqual(chosen["completion_mask"].shape, chosen["input_ids"].shape)
        self.assertGreater(chosen["completion_token_count"], 0)
        self.assertFalse(bool(chosen["completion_mask"][0, 0]))

    def test_loader_rejects_non_preferred_pair(self):
        row = _row(1)
        row["pair_diagnostics"]["rejected_hit_count"] = 3
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "pairs.json"
            path.write_text(json.dumps([row]), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "neither semantically weaker"):
                load_preference_rows(path)

    def test_loader_accepts_validated_on_policy_surface_failure(self):
        row = _row(1)
        row["pair_diagnostics"].update(
            {
                "rejected_hit_count": 3,
                "chosen_strict_quality_pass": True,
                "rejected_strict_quality_pass": False,
                "rejected_surface_failure_reasons": ["unexpected_ascii_leak"],
            }
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "pairs.json"
            path.write_text(json.dumps([row]), encoding="utf-8")

            loaded = load_preference_rows(path)

        self.assertEqual(loaded[0]["id"], "row-1")


if __name__ == "__main__":
    unittest.main()
