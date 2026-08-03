#!/usr/bin/env python3
"""Tests for the Qwen3 fresh-generation pre/post probe."""

from __future__ import annotations

import ast
import unittest
from collections import Counter
from pathlib import Path

import build_rightbrain_qwen3_fresh_generation_v1 as construction
import run_rightbrain_qwen3_fresh_generation_v1 as runner


class FreshGenerationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = construction.load_json(construction.DATASET_PATH)

    def test_fresh_prompts_are_disjoint_balanced_and_prompt_only(self):
        contract = construction.fresh_generation_contract(self.rows)
        self.assertEqual(contract["unique_prompt_count"], 8)
        self.assertEqual(contract["source_id_overlap_with_train_and_loss_holdout"], 0)
        self.assertEqual(
            contract["exact_reference_overlap_with_train_and_loss_holdout"], 0
        )
        self.assertEqual(
            contract["provider_counts"],
            {
                "structured_neutral_dialogue": 4,
                "structured_target_public_persona": 4,
            },
        )
        self.assertEqual(set(contract["memory_mode_counts"].values()), {2})
        self.assertFalse(contract["assistant_reference_in_generation_prompt"])
        for index in construction.FRESH_GENERATION_ROW_INDICES:
            self.assertEqual(
                [message["role"] for message in self.rows[index]["messages"][:2]],
                ["system", "user"],
            )

    def test_reference_variants_share_prompt_but_not_answer(self):
        for primary, alternate in zip(
            construction.FRESH_GENERATION_ROW_INDICES,
            construction.FRESH_REFERENCE_ALT_ROW_INDICES,
            strict=True,
        ):
            self.assertEqual(
                self.rows[primary]["messages"][:2],
                self.rows[alternate]["messages"][:2],
            )
            self.assertNotEqual(
                self.rows[primary]["messages"][-1]["content"],
                self.rows[alternate]["messages"][-1]["content"],
            )

    def test_runner_has_generation_and_one_update_site_but_no_save(self):
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
        self.assertIn("generate(", source)
        self.assertIn("enumerate(construction.TRAIN_SCHEDULE, start=1)", source)
        for forbidden in ("save_weights(", "save_pretrained("):
            self.assertNotIn(forbidden, source)

    def test_score_output_obeys_semantic_memory_and_surface_contract(self):
        case, _ = runner._prompt_cases()
        selected = case[0]
        references = ["前に話したボードゲーム好き。一緒に遊ぼ。"]
        good = {
            "row_index": selected["row_index"],
            "row_id": selected["row_id"],
            "source_id": selected["source_id"],
            "provider_id": selected["provider_id"],
            "memory_mode": selected["memory_mode"],
            "output": "前に話したボードゲーム好き。一緒に遊ぼ。",
            "character_count": 23,
            "generation_seconds": 0.1,
        }
        scored = runner._score_output(selected, good, references)
        self.assertTrue(scored["semantic_complete"])
        self.assertTrue(scored["memory_policy_pass"])
        self.assertTrue(scored["joint_contract_pass"])
        bad = runner._score_output(
            selected,
            {**good, "output": "AIです"},
            references,
        )
        self.assertFalse(bad["semantic_complete"])
        self.assertFalse(bad["forbidden_pass"])
        self.assertFalse(bad["casual_japanese_pass"])
        self.assertFalse(bad["joint_contract_pass"])

    def test_aggregate_scores_are_balanced_by_provider_pair(self):
        cases, _ = runner._prompt_cases()
        self.assertEqual(Counter(case["provider_id"] for case in cases), {
            "structured_target_public_persona": 4,
            "structured_neutral_dialogue": 4,
        })
        self.assertEqual(Counter(case["memory_mode"] for case in cases), {
            "explicit_allowed": 2,
            "background_only": 2,
            "do_not_mention": 2,
            "no_memory": 2,
        })

    def test_classification_order(self):
        base = {
            "training_exact_and_values_finite": True,
            "generation_reproducible": True,
            "outputs_changed": True,
            "contract_behavior_improved": True,
            "mutation_within_bounds": True,
            "all_contracts_exact": True,
        }
        self.assertEqual(runner._classify(base), "fresh_generation_behavior_improved")
        failures = (
            ("training_exact_and_values_finite", "fresh_generation_training_drifted"),
            ("generation_reproducible", "fresh_generation_not_reproducible"),
            ("outputs_changed", "fresh_generation_outputs_unchanged"),
            ("contract_behavior_improved", "fresh_generation_contract_not_improved"),
            ("mutation_within_bounds", "fresh_generation_mutation_out_of_bounds"),
        )
        for key, outcome in failures:
            with self.subTest(key=key):
                self.assertEqual(runner._classify({**base, key: False}), outcome)
        self.assertEqual(
            runner._classify(base, completed=False),
            "fresh_generation_execution_failed",
        )

    def test_invalid_repeat_is_rejected_before_execution(self):
        with self.assertRaises(ValueError):
            runner.run_repeat(4)


if __name__ == "__main__":
    unittest.main()
