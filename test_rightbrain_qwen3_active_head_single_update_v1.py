#!/usr/bin/env python3
"""Tests for the active-head Qwen3 single-update canary."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

import build_rightbrain_qwen3_active_head_single_update_v1 as construction
import run_rightbrain_qwen3_active_head_single_update_v1 as runner


class ActiveHeadSingleUpdateContractTests(unittest.TestCase):
    def test_repeat_and_optimizer_contract(self):
        self.assertEqual(construction.REPEATS, tuple(range(1, 10)))

    def test_runner_has_exactly_one_update_site_and_no_save(self):
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
        self.assertIn("clip_grad_norm", source)
        self.assertIn("optim.AdamW", source)
        for forbidden in ("save_weights", "save_pretrained", "generate"):
            self.assertNotIn(forbidden, source)

    def test_classification_order(self):
        base = {
            "all_values_finite": True,
            "parameter_hash_changed_and_delta_nonzero": True,
            "update_reproducible": True,
            "mutation_within_bounds": True,
            "loss_within_bound": True,
            "all_contracts_exact": True,
        }
        self.assertEqual(
            runner._classify(base), "active_head_single_update_canary_passed"
        )
        failures = (
            ("all_values_finite", "single_update_nonfinite"),
            (
                "parameter_hash_changed_and_delta_nonzero",
                "single_update_did_not_mutate_parameters",
            ),
            ("update_reproducible", "single_update_not_reproducible"),
            ("mutation_within_bounds", "single_update_exceeded_mutation_bounds"),
            ("loss_within_bound", "single_update_loss_regressed"),
        )
        for key, outcome in failures:
            with self.subTest(key=key):
                self.assertEqual(runner._classify({**base, key: False}), outcome)
        self.assertEqual(
            runner._classify(base, completed=False),
            "single_update_execution_failed",
        )

    def test_invalid_repeat_is_rejected_before_execution(self):
        with self.assertRaises(ValueError):
            runner.run_repeat(10)


if __name__ == "__main__":
    unittest.main()
