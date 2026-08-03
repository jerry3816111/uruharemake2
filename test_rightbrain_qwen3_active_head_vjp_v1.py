#!/usr/bin/env python3
"""Tests for the Qwen3 active-token tied-head VJP contract."""

from __future__ import annotations

import unittest

import build_rightbrain_qwen3_active_head_vjp_v1 as construction
import run_rightbrain_qwen3_active_head_vjp_v1 as runner


class ActiveHeadContractTests(unittest.TestCase):
    def test_counterbalanced_schedule(self):
        self.assertEqual(len(construction.EXECUTION_SCHEDULE), 18)
        self.assertEqual(
            construction._balanced_position_counts(),
            {condition: [6, 6, 6] for condition in construction.CONDITIONS},
        )

    def test_active_positions_are_derived_only_from_labels(self):
        batch = {"labels": [-100, -100, 7, -100, 9]}
        contract = construction.active_position_contract(batch)
        self.assertEqual(contract["positions"], [1, 3])
        self.assertEqual(contract["count"], 2)

    def test_classification_matrix(self):
        base = {
            "dense_mask_after_loss": False,
            "dense_gather_before_loss": False,
            "active_gather_before_head": True,
        }
        self.assertEqual(
            runner._classify(base),
            "projecting_ignored_positions_is_sufficient_to_reproduce_drift",
        )
        self.assertEqual(
            runner._classify({**base, "dense_gather_before_loss": True}),
            "post_head_masking_path_is_sufficient_to_reproduce_drift",
        )
        self.assertEqual(
            runner._classify({**base, "active_gather_before_head": False}),
            "active_head_projection_still_reproduces_drift",
        )
        self.assertEqual(
            runner._classify(
                {**base, "dense_gather_before_loss": True, "active_gather_before_head": False}
            ),
            "active_gather_path_introduces_drift",
        )
        self.assertEqual(
            runner._classify({**base, "dense_mask_after_loss": True}),
            "dense_parent_drift_not_reproduced",
        )
        self.assertEqual(
            runner._classify(base, semantic_equivalent=False),
            "head_conditions_not_semantically_equivalent",
        )
        self.assertEqual(
            runner._classify(base, completed=False),
            "active_head_vjp_execution_failed",
        )

    def test_invalid_condition_is_rejected_before_execution(self):
        with self.assertRaises(ValueError):
            runner.run_repeat("not_a_condition", 1)


if __name__ == "__main__":
    unittest.main()
