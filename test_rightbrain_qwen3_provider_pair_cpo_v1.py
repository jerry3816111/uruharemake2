#!/usr/bin/env python3
"""Tests for the matched provider-pair CPO objective probe."""

from __future__ import annotations

import ast
import json
import unittest
from collections import Counter
from pathlib import Path

import build_rightbrain_qwen3_provider_pair_cpo_v1 as construction
import run_rightbrain_qwen3_provider_pair_cpo_v1 as runner


class ProviderPairCPOContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = construction.load_json(construction.DATASET_PATH)

    def test_train_and_holdout_pairs_are_matched_and_source_disjoint(self):
        train_pairs = construction.provider_pair_map(
            self.rows, construction.TRAIN_ROW_INDICES
        )
        holdout_pairs = construction.provider_pair_map(
            self.rows, construction.HOLDOUT_ROW_INDICES
        )
        self.assertEqual(set(train_pairs), set(construction.TRAIN_ROW_INDICES))
        self.assertEqual(set(holdout_pairs), set(construction.HOLDOUT_ROW_INDICES))
        train_sources = {
            self.rows[index]["source_id"] for index in construction.TRAIN_ROW_INDICES
        }
        holdout_sources = {
            self.rows[index]["source_id"]
            for index in construction.HOLDOUT_ROW_INDICES
        }
        self.assertFalse(train_sources & holdout_sources)
        train_answers = {
            self.rows[index]["messages"][-1]["content"].strip()
            for index in construction.TRAIN_ROW_INDICES
        }
        holdout_answers = {
            self.rows[index]["messages"][-1]["content"].strip()
            for index in construction.HOLDOUT_ROW_INDICES
        }
        self.assertFalse(train_answers & holdout_answers)
        for index, rejected_index in {**train_pairs, **holdout_pairs}.items():
            preferred = self.rows[index]
            rejected = self.rows[rejected_index]
            self.assertEqual(preferred["source_id"], rejected["source_id"])
            self.assertEqual(preferred["variant_index"], rejected["variant_index"])
            self.assertNotEqual(preferred["provider_id"], rejected["provider_id"])
            self.assertNotEqual(
                preferred["messages"][-1]["content"],
                rejected["messages"][-1]["content"],
            )

    def test_holdout_was_unused_and_balances_provider_memory_and_scene(self):
        previously_used = set(
            construction.data_parent.TRAIN_ROW_INDICES
            + construction.data_parent.HOLDOUT_ROW_INDICES
            + construction.evidence_parent.FRESH_GENERATION_ROW_INDICES
            + construction.evidence_parent.FRESH_REFERENCE_ALT_ROW_INDICES
        )
        previous_sources = {
            self.rows[index]["source_id"] for index in previously_used
        }
        holdout_rows = [
            self.rows[index] for index in construction.HOLDOUT_ROW_INDICES
        ]
        self.assertFalse(
            {row["source_id"] for row in holdout_rows} & previous_sources
        )
        self.assertEqual(
            Counter(row["provider_id"] for row in holdout_rows),
            {
                "structured_target_public_persona": 4,
                "structured_neutral_dialogue": 4,
            },
        )
        self.assertEqual(
            Counter(row["memory_mode"] for row in holdout_rows),
            {
                "background_only": 2,
                "do_not_mention": 2,
                "explicit_allowed": 2,
                "no_memory": 2,
            },
        )
        self.assertEqual(len({row["source_id"] for row in holdout_rows}), 4)

    def test_only_pairwise_weight_changes_between_conditions(self):
        control = {
            "preferred_sft_weight": 1.0,
            "pairwise_weight": 0.0,
            "pairwise_beta": construction.PAIRWISE_BETA,
        }
        candidate = {
            "preferred_sft_weight": 1.0,
            "pairwise_weight": 1.0,
            "pairwise_beta": construction.PAIRWISE_BETA,
        }
        differing = [key for key in control if control[key] != candidate[key]]
        self.assertEqual(differing, ["pairwise_weight"])
        self.assertEqual(
            runner._pair_gradient_coefficient(0.0, 1.0, -1.0), 0.0
        )
        self.assertGreater(
            runner._pair_gradient_coefficient(1.0, 1.0, -1.0), 0.5
        )
        self.assertLess(
            runner._pair_gradient_coefficient(1.0, 1.0, 1.0), 0.5
        )

    def test_runner_has_two_backward_sites_one_update_and_no_generation_or_save(self):
        path = Path(runner.__file__)
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        update_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "update"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "optimizer"
        ]
        value_grad_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "value_and_grad"
        ]
        self.assertEqual(len(update_calls), 1)
        self.assertEqual(len(value_grad_calls), 2)
        for forbidden in ("generate(", "save_weights(", "save_pretrained("):
            self.assertNotIn(forbidden, source)

    def test_pair_summary_and_change_use_correct_margin_direction(self):
        before = [
            {
                "row_index": 1,
                "row_id": "a",
                "source_id": "s",
                "provider_id": "target",
                "memory_mode": "no_memory",
                "variant_index": 1,
                "rejected_row_index": 2,
                "rejected_row_id": "b",
                "rejected_provider_id": "neutral",
                "preferred_nll": 2.0,
                "rejected_nll": 1.8,
                "provider_margin": -0.2,
                "correct_preference": False,
            }
        ]
        after = [{**before[0], "preferred_nll": 1.9, "rejected_nll": 2.0}]
        after[0]["provider_margin"] = 0.1
        after[0]["correct_preference"] = True
        summary = runner._pair_summary(after)
        change = runner._paired_change(before, after)
        self.assertAlmostEqual(summary["provider_margin_mean"], 0.1)
        self.assertEqual(summary["correct_preference_rate"], 1.0)
        self.assertAlmostEqual(change["provider_margin_delta_mean"], 0.3)
        self.assertAlmostEqual(change["preferred_nll_decrease_mean"], 0.1)

    def test_classification_order(self):
        base = {
            "all_values_finite_and_update_count_exact": True,
            "initial_parameter_hash_equal_between_conditions": True,
            "pre_holdout_metrics_equal_between_conditions": True,
            "control_and_candidate_each_reproducible": True,
            "candidate_holdout_margin_delta_positive": True,
            "candidate_holdout_margin_delta_exceeds_control": True,
            "candidate_post_holdout_margin_exceeds_control": True,
            "candidate_post_correct_preference_rate_not_below_control": True,
            "candidate_post_preferred_nll_within_control_bound": True,
            "candidate_train_final_margin_exceeds_control": True,
            "mutation_within_bounds": True,
            "all_contracts_exact": True,
        }
        self.assertEqual(
            runner._classify(base),
            "provider_pair_cpo_holdout_margin_confirmed",
        )
        self.assertEqual(
            runner._classify(
                {**base, "candidate_holdout_margin_delta_positive": False}
            ),
            "provider_pair_cpo_holdout_margin_not_improved",
        )
        self.assertEqual(
            runner._classify(
                {**base, "candidate_post_preferred_nll_within_control_bound": False}
            ),
            "provider_pair_cpo_preferred_likelihood_regressed",
        )
        self.assertEqual(
            runner._classify({**base, "mutation_within_bounds": False}),
            "provider_pair_cpo_mutation_out_of_bounds",
        )
        self.assertEqual(
            runner._classify(base, completed=False),
            "provider_pair_cpo_execution_failed",
        )

    def test_invalid_condition_and_repeat_are_rejected_before_execution(self):
        with self.assertRaises(ValueError):
            runner.run_condition("invalid", 1)
        with self.assertRaises(ValueError):
            runner.run_condition("sft_control", 4)


if __name__ == "__main__":
    unittest.main()
