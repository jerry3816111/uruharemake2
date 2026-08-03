#!/usr/bin/env python3
"""Tests for the source-separated active-head Qwen3 multi-batch probe."""

from __future__ import annotations

import ast
import unittest
from collections import Counter
from pathlib import Path

from transformers import AutoTokenizer

import build_rightbrain_qwen3_active_head_multibatch_v1 as construction
import run_rightbrain_qwen3_active_head_multibatch_v1 as runner


class ActiveHeadMultibatchContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = construction.load_json(construction.DATASET_PATH)

    def test_frozen_split_and_schedule(self):
        self.assertEqual(construction.REPEATS, (1, 2, 3))
        self.assertEqual(len(construction.TRAIN_ROW_INDICES), 16)
        self.assertEqual(len(construction.HOLDOUT_ROW_INDICES), 16)
        self.assertEqual(
            construction.TRAIN_SCHEDULE,
            construction.TRAIN_ROW_INDICES + construction.TRAIN_ROW_INDICES,
        )
        self.assertEqual(len(construction.TRAIN_SCHEDULE), 32)
        self.assertEqual(construction.ALLOCATED_TOKENS, 512)

    def test_train_and_holdout_are_source_and_target_separated(self):
        train = [self.rows[index] for index in construction.TRAIN_ROW_INDICES]
        holdout = [self.rows[index] for index in construction.HOLDOUT_ROW_INDICES]
        train_sources = {row["source_id"] for row in train}
        holdout_sources = {row["source_id"] for row in holdout}
        train_targets = {row["messages"][-1]["content"].strip() for row in train}
        holdout_targets = {
            row["messages"][-1]["content"].strip() for row in holdout
        }
        self.assertFalse(train_sources & holdout_sources)
        self.assertFalse(train_targets & holdout_targets)
        for selected in (train, holdout):
            self.assertEqual(
                Counter(row["provider_id"] for row in selected),
                {
                    "structured_neutral_dialogue": 8,
                    "structured_target_public_persona": 8,
                },
            )
            self.assertEqual(
                Counter(row["memory_mode"] for row in selected),
                {
                    "background_only": 4,
                    "do_not_mention": 4,
                    "explicit_allowed": 4,
                    "no_memory": 4,
                },
            )
            self.assertTrue(
                all(
                    row["provenance"]["synthetic"] is True
                    and row["provenance"]["source_independent"] is True
                    and row["provenance"]["contains_target_utterance"] is False
                    and row["provenance"]["contains_benchmark_item"] is False
                    for row in selected
                )
            )

    def test_canonical_batches_retain_every_answer_token(self):
        parent = construction.load_json(construction.PARENT_PREREGISTRATION)
        tokenizer = AutoTokenizer.from_pretrained(
            parent["local_model_contract"]["snapshot_root"],
            local_files_only=True,
            trust_remote_code=True,
        )
        batches, details, token_hash = construction.canonical_batches(
            tokenizer, self.rows
        )
        expected = set(
            construction.TRAIN_ROW_INDICES + construction.HOLDOUT_ROW_INDICES
        )
        self.assertEqual(set(batches), expected)
        self.assertEqual(len(details), 32)
        self.assertEqual(len(token_hash), 64)
        for detail in details:
            self.assertEqual(
                detail["active_position_contract"]["count"],
                detail["answer_tokens"],
            )
            self.assertEqual(detail["allocated_tokens"], 512)
            self.assertGreater(detail["retained_prompt_tokens"], 0)

    def test_runner_has_one_frozen_update_site_and_no_persistence(self):
        source = Path(runner.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        update_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "update"
        ]
        self.assertEqual(len(update_calls), 1)
        self.assertIn(
            "enumerate(construction.TRAIN_SCHEDULE, start=1)",
            source,
        )
        self.assertIn("clip_grad_norm", source)
        self.assertIn("optim.AdamW", source)
        for forbidden in (
            "save_weights(",
            "save_pretrained(",
            ".generate(",
            "generate_step(",
        ):
            self.assertNotIn(forbidden, source)

    def test_paired_summary_uses_identical_rows_and_correct_direction(self):
        before = [
            {
                "row_index": 1,
                "row_id": "b",
                "source_id": "source-b",
                "provider_id": "target",
                "memory_mode": "no_memory",
                "variant_index": 0,
                "loss": 5.0,
            },
            {
                "row_index": 0,
                "row_id": "a",
                "source_id": "source-a",
                "provider_id": "neutral",
                "memory_mode": "explicit_allowed",
                "variant_index": 0,
                "loss": 4.0,
            },
        ]
        after = [
            {**before[1], "loss": 3.8},
            {**before[0], "loss": 5.1},
        ]
        summary = runner._paired_summary(before, after)
        self.assertAlmostEqual(summary["pre_mean_loss"], 4.5)
        self.assertAlmostEqual(summary["post_mean_loss"], 4.45)
        self.assertAlmostEqual(summary["mean_loss_decrease"], 0.05)
        self.assertEqual(summary["improved_row_count"], 1)
        self.assertAlmostEqual(summary["worst_row_loss_increase"], 0.1)
        self.assertEqual([row["row_id"] for row in summary["pairs"]], ["a", "b"])
        with self.assertRaises(RuntimeError):
            runner._paired_summary(before, after[:1])

    def test_classification_order(self):
        base = {
            "all_values_finite": True,
            "parameter_hash_changed_and_delta_nonzero": True,
            "trajectory_reproducible": True,
            "mutation_within_bounds": True,
            "train_loss_learned": True,
            "holdout_loss_generalized": True,
            "all_contracts_exact": True,
        }
        self.assertEqual(
            runner._classify(base),
            "active_head_multibatch_holdout_learning_confirmed",
        )
        failures = (
            ("all_values_finite", "multibatch_nonfinite"),
            (
                "parameter_hash_changed_and_delta_nonzero",
                "multibatch_did_not_mutate_parameters",
            ),
            ("trajectory_reproducible", "multibatch_not_reproducible"),
            ("mutation_within_bounds", "multibatch_exceeded_mutation_bounds"),
            ("train_loss_learned", "multibatch_train_learning_failed"),
            (
                "holdout_loss_generalized",
                "multibatch_holdout_generalization_failed",
            ),
        )
        for key, outcome in failures:
            with self.subTest(key=key):
                self.assertEqual(runner._classify({**base, key: False}), outcome)
        self.assertEqual(
            runner._classify(base, completed=False),
            "multibatch_execution_failed",
        )

    def test_invalid_repeat_is_rejected_before_execution(self):
        with self.assertRaises(ValueError):
            runner.run_repeat(4)


if __name__ == "__main__":
    unittest.main()
