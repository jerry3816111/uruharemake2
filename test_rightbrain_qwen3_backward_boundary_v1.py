#!/usr/bin/env python3
"""Tests for the Qwen3 backward-boundary localization contract."""

from __future__ import annotations

import unittest

import numpy as np

import build_rightbrain_qwen3_backward_boundary_v1 as construction
import run_rightbrain_qwen3_backward_boundary_v1 as runner


class BackwardBoundaryContractTests(unittest.TestCase):
    def test_counterbalanced_schedule(self):
        self.assertEqual(len(construction.EXECUTION_SCHEDULE), 18)
        for condition, counts in construction._balanced_position_counts().items():
            self.assertIn(condition, construction.CONDITIONS)
            self.assertEqual(counts, [6, 6, 6])

    def test_cotangent_is_deterministic_and_normalized(self):
        left, left_hash = construction.canonical_cotangent([1, 7, 11], 17)
        right, right_hash = construction.canonical_cotangent([1, 7, 11], 17)
        self.assertTrue(np.array_equal(left, right))
        self.assertEqual(left_hash, right_hash)
        self.assertEqual(left.dtype, np.float32)
        self.assertLess(abs(float(np.linalg.norm(left)) - 1.0), 0.2)

    def test_classification_matrix(self):
        base = {
            "full_chain_control": False,
            "head_boundary_vjp": False,
            "transformer_boundary_vjp": True,
        }
        self.assertEqual(
            runner._classify(base),
            "tied_lm_head_backward_is_sufficient_to_reproduce_drift",
        )
        self.assertEqual(
            runner._classify({**base, "head_boundary_vjp": True, "transformer_boundary_vjp": False}),
            "shared_transformer_backward_is_sufficient_to_reproduce_drift",
        )
        self.assertEqual(
            runner._classify({**base, "transformer_boundary_vjp": False}),
            "both_backward_regions_independently_reproduce_drift",
        )
        self.assertEqual(
            runner._classify({**base, "head_boundary_vjp": True}),
            "composed_head_transformer_backward_is_required_to_reproduce_drift",
        )
        self.assertEqual(
            runner._classify({**base, "full_chain_control": True}),
            "full_chain_parent_drift_not_reproduced",
        )
        self.assertEqual(
            runner._classify(base, completed=False),
            "backward_boundary_execution_failed",
        )

    def test_invalid_condition_is_rejected_before_execution(self):
        with self.assertRaises(ValueError):
            runner.run_repeat("not_a_condition", 1)


if __name__ == "__main__":
    unittest.main()
