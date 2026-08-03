#!/usr/bin/env python3
"""Tests for the frozen Qwen3 active-head 64-step follow-up."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

import build_rightbrain_qwen3_active_head_64step_v1 as construction
import build_rightbrain_qwen3_active_head_multibatch_v1 as parent
import run_rightbrain_qwen3_active_head_64step_v1 as runner
import run_rightbrain_qwen3_active_head_multibatch_v1 as parent_engine


class ActiveHead64StepContractTests(unittest.TestCase):
    def test_only_schedule_length_changes_from_parent(self):
        self.assertEqual(construction.REPEATS, parent.REPEATS)
        self.assertEqual(construction.TRAIN_ROW_INDICES, parent.TRAIN_ROW_INDICES)
        self.assertEqual(
            construction.HOLDOUT_ROW_INDICES, parent.HOLDOUT_ROW_INDICES
        )
        self.assertEqual(construction.ALLOCATED_TOKENS, parent.ALLOCATED_TOKENS)
        self.assertEqual(construction.TRAIN_SCHEDULE[:32], parent.TRAIN_SCHEDULE)
        self.assertEqual(construction.TRAIN_SCHEDULE[32:], parent.TRAIN_SCHEDULE)
        self.assertEqual(len(construction.TRAIN_SCHEDULE), 64)

    def test_verified_parent_engine_has_one_update_site_and_wrapper_has_no_save(self):
        parent_source = Path(parent_engine.__file__).read_text(encoding="utf-8")
        tree = ast.parse(parent_source)
        update_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "update"
        ]
        self.assertEqual(len(update_calls), 1)
        wrapper_source = Path(runner.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "save_weights(",
            "save_pretrained(",
            ".generate(",
            "generate_step(",
        ):
            self.assertNotIn(forbidden, parent_source)
            self.assertNotIn(forbidden, wrapper_source)

    def test_classification_order_and_parent_comparison(self):
        base = {
            "all_values_finite": True,
            "parameter_hash_changed_and_delta_nonzero": True,
            "trajectory_reproducible": True,
            "mutation_within_bounds": True,
            "train_loss_learned": True,
            "holdout_loss_generalized": True,
            "all_contracts_exact": True,
            "parent_32step_gain_and_holdout_noninferiority": True,
        }
        self.assertEqual(
            runner._classify(base),
            "active_head_64step_holdout_learning_confirmed",
        )
        self.assertEqual(
            runner._classify(
                {**base, "parent_32step_gain_and_holdout_noninferiority": False}
            ),
            "extended_parent_gain_failed",
        )
        self.assertEqual(
            runner._classify({**base, "train_loss_learned": False}),
            "extended_train_learning_failed",
        )
        self.assertEqual(
            runner._classify(base, completed=False), "extended_execution_failed"
        )

    def test_invalid_repeat_is_rejected_before_execution(self):
        with self.assertRaises(ValueError):
            runner.run_repeat(4)


if __name__ == "__main__":
    unittest.main()
