#!/usr/bin/env python3
"""Tests for the active-head Qwen3 short training trajectory."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

import build_rightbrain_qwen3_active_head_short_trajectory_v1 as construction
import run_rightbrain_qwen3_active_head_short_trajectory_v1 as runner


class ActiveHeadShortTrajectoryContractTests(unittest.TestCase):
    def test_repeat_and_update_contract(self):
        self.assertEqual(construction.REPEATS, (1, 2, 3))
        self.assertEqual(construction.OPTIMIZER_UPDATES, 32)
        self.assertEqual(construction.LOSS_QUANTUM, 0.0078125)

    def test_runner_has_one_update_site_inside_frozen_loop_and_no_save(self):
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
            "range(1, construction.OPTIMIZER_UPDATES + 1)",
            source,
        )
        self.assertIn("clip_grad_norm", source)
        self.assertIn("optim.AdamW", source)
        for forbidden in ("save_weights", "save_pretrained", "generate"):
            self.assertNotIn(forbidden, source)

    def test_classification_order(self):
        base = {
            "all_values_finite": True,
            "parameter_hash_changed_and_delta_nonzero": True,
            "trajectory_reproducible": True,
            "mutation_within_bounds": True,
            "loss_converged": True,
            "all_contracts_exact": True,
        }
        self.assertEqual(
            runner._classify(base), "active_head_short_trajectory_converged"
        )
        failures = (
            ("all_values_finite", "short_trajectory_nonfinite"),
            (
                "parameter_hash_changed_and_delta_nonzero",
                "short_trajectory_did_not_mutate_parameters",
            ),
            ("trajectory_reproducible", "short_trajectory_not_reproducible"),
            (
                "mutation_within_bounds",
                "short_trajectory_exceeded_mutation_bounds",
            ),
            ("loss_converged", "short_trajectory_did_not_converge"),
        )
        for key, outcome in failures:
            with self.subTest(key=key):
                self.assertEqual(runner._classify({**base, key: False}), outcome)
        self.assertEqual(
            runner._classify(base, completed=False),
            "short_trajectory_execution_failed",
        )

    def test_trajectory_hash_covers_loss_and_gradient_sequences(self):
        steps = [
            {
                "update": 1,
                "loss_before_update": 5.0,
                "raw_gradient": {"sha256": "raw"},
                "clipped_gradient": {"sha256": "clipped"},
                "optimizer_step_after_update": 1,
            }
        ]
        original = runner._trajectory_sha256(steps, 4.9)
        self.assertNotEqual(original, runner._trajectory_sha256(steps, 4.8))
        changed = [{**steps[0], "loss_before_update": 4.99}]
        self.assertNotEqual(original, runner._trajectory_sha256(changed, 4.9))

    def test_invalid_repeat_is_rejected_before_execution(self):
        with self.assertRaises(ValueError):
            runner.run_repeat(4)


if __name__ == "__main__":
    unittest.main()
