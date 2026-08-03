#!/usr/bin/env python3
"""Tests for the active-token Qwen3 full-chain zero-update contract."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

import build_rightbrain_qwen3_active_head_full_chain_v1 as construction
import run_rightbrain_qwen3_active_head_full_chain_v1 as runner


ROOT = Path(__file__).resolve().parent


class ActiveHeadFullChainContractTests(unittest.TestCase):
    def test_schedule_is_balanced(self):
        self.assertEqual(len(construction.EXECUTION_SCHEDULE), 18)
        self.assertEqual(
            construction._balanced_position_counts(),
            {condition: [9, 9] for condition in construction.CONDITIONS},
        )

    def test_active_objective_gathers_before_tied_head(self):
        source = Path(runner.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        function = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "_active_full_chain_loss"
        )
        calls = [
            node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
            for node in ast.walk(function)
            if isinstance(node, ast.Call)
            and isinstance(node.func, (ast.Attribute, ast.Name))
        ]
        self.assertEqual(calls.count("take"), 2)
        self.assertIn("as_linear", calls)
        self.assertIn("cross_entropy", calls)

    def test_runner_has_no_optimizer_update_or_generation(self):
        source = Path(runner.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "mlx.optimizers",
            "Adam",
            "AdamW",
            "SGD",
            "optimizer.update",
            "save_weights",
            "generate",
        ):
            self.assertNotIn(forbidden, source)

    def test_classification_matrix(self):
        base = {
            "dense_full_chain_control": False,
            "active_head_full_chain": True,
        }
        self.assertEqual(
            runner._classify(base),
            "active_head_full_chain_stabilizes_zero_update_backward",
        )
        self.assertEqual(
            runner._classify({**base, "active_head_full_chain": False}),
            "active_head_is_insufficient_for_full_chain_stability",
        )
        self.assertEqual(
            runner._classify({**base, "dense_full_chain_control": True}),
            "dense_full_chain_parent_drift_not_reproduced",
        )
        self.assertEqual(
            runner._classify(
                {
                    "dense_full_chain_control": True,
                    "active_head_full_chain": False,
                }
            ),
            "active_head_full_chain_introduces_drift",
        )
        self.assertEqual(
            runner._classify(base, semantic_equivalent=False),
            "full_chain_conditions_not_semantically_equivalent",
        )
        self.assertEqual(
            runner._classify(base, completed=False),
            "active_head_full_chain_execution_failed",
        )

    def test_invalid_condition_is_rejected_before_execution(self):
        with self.assertRaises(ValueError):
            runner.run_repeat("not_a_condition", 1)


if __name__ == "__main__":
    unittest.main()
