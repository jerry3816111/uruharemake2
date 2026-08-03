#!/usr/bin/env python3
"""Contract tests for the provider-signal position experiment."""

from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path

import build_rightbrain_qwen3_provider_signal_position_v1 as construction
import run_rightbrain_qwen3_provider_signal_position_v1 as runner


class ProviderSignalPositionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = construction.load_json(construction.DATASET_PATH)

    def test_probe_uses_four_never_used_balanced_sources(self):
        selected = construction.PROBE_ROW_INDICES + construction.REFERENCE_ALT_ROW_INDICES
        prior = tuple(
            dict.fromkeys(
                construction.data_parent.TRAIN_ROW_INDICES
                + construction.data_parent.HOLDOUT_ROW_INDICES
                + construction.fresh_parent.FRESH_GENERATION_ROW_INDICES
                + construction.fresh_parent.FRESH_REFERENCE_ALT_ROW_INDICES
                + construction.cpo_parent.HOLDOUT_ROW_INDICES
            )
        )
        selected_sources = {self.rows[index]["source_id"] for index in selected}
        prior_sources = {self.rows[index]["source_id"] for index in prior}
        self.assertEqual(len(selected_sources), 4)
        self.assertFalse(selected_sources & prior_sources)
        self.assertEqual(
            {self.rows[index]["provider_id"] for index in construction.PROBE_ROW_INDICES},
            {"structured_target_public_persona", "structured_neutral_dialogue"},
        )
        self.assertEqual(
            {self.rows[index]["memory_mode"] for index in construction.PROBE_ROW_INDICES},
            {"background_only", "do_not_mention", "explicit_allowed", "no_memory"},
        )

    def test_only_json_path_changes_between_conditions(self):
        for index in construction.PROBE_ROW_INDICES:
            nested = json.loads(
                construction.condition_messages(self.rows[index], "nested_control")[1]["content"]
            )
            top = json.loads(
                construction.condition_messages(self.rows[index], "top_level_signal")[1]["content"]
            )
            nested_rest, nested_persona = construction._payload_without_persona(nested)
            top_rest, top_persona = construction._payload_without_persona(top)
            self.assertEqual(nested_rest, top_rest)
            self.assertEqual(nested_persona, top_persona)
            self.assertIn("persona_expression_brief", nested["context"])
            self.assertIn("persona_expression_brief", top)
            self.assertNotIn("persona_expression_brief", top["context"])

    def test_prompt_contract_contains_no_assistant_reference(self):
        prompt = construction.prompt_contract(self.rows)
        self.assertEqual(prompt["case_count"], 8)
        self.assertFalse(prompt["assistant_references_in_prompt"])
        for case in prompt["cases"]:
            for condition in construction.CONDITIONS:
                messages = case[f"{condition}_messages"]
                self.assertEqual([message["role"] for message in messages], ["system", "user"])

    def test_reference_pairs_are_provider_specific_and_prompt_matched(self):
        references = construction._references_by_row(self.rows)
        self.assertEqual(len(references), 8)
        for value in references.values():
            self.assertEqual(len(value["own"]), 2)
            self.assertEqual(len(value["opposite"]), 2)
            self.assertFalse(set(value["own"]) & set(value["opposite"]))

    def test_runner_has_generation_but_no_training_or_save_path(self):
        source = Path(runner.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        generate_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "generate"
        ]
        update_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "update"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "optimizer"
        ]
        self.assertEqual(len(generate_calls), 1)
        self.assertEqual(update_calls, [])
        for forbidden in ("value_and_grad", "save_weights(", "save_pretrained("):
            self.assertNotIn(forbidden, source)

    def test_alignment_margin_direction(self):
        own = runner.score_common._char_bigram_f1("ゲームしよ", "ゲームしよ")
        opposite = runner.score_common._char_bigram_f1("ゲームしよ", "休もう")
        self.assertGreater(own - opposite, 0.0)

    def test_classification_order(self):
        passed = {
            "each_condition_reproducible": True,
            "candidate_outputs_changed": True,
            "provider_pair_difference_improved": True,
            "provider_alignment_margin_improved": True,
            "correct_provider_alignment_not_regressed": True,
            "joint_contract_noninferior": True,
            "no_exact_reference_copy": True,
            "resource_within_limit": True,
            "all_contracts_exact": True,
        }
        self.assertEqual(
            runner._classify(passed), "provider_signal_position_effect_confirmed"
        )
        self.assertEqual(
            runner._classify({**passed, "provider_pair_difference_improved": False}),
            "provider_signal_position_differentiation_not_improved",
        )
        self.assertEqual(
            runner._classify({**passed, "joint_contract_noninferior": False}),
            "provider_signal_position_contract_regressed",
        )
        self.assertEqual(
            runner._classify({**passed, "each_condition_reproducible": False}),
            "provider_signal_position_not_reproducible",
        )
        self.assertEqual(
            runner._classify(passed, completed=False),
            "provider_signal_position_execution_failed",
        )

    def test_invalid_condition_and_repeat_are_rejected(self):
        with self.assertRaises(ValueError):
            construction.condition_messages(self.rows[8], "invalid")
        with self.assertRaises(ValueError):
            runner.run_repeat(4)


if __name__ == "__main__":
    unittest.main()
