#!/usr/bin/env python3
"""Contract tests for the compiled surface-signal experiment."""

from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path

import build_rightbrain_qwen3_compiled_surface_signal_v1 as construction
import run_rightbrain_qwen3_compiled_surface_signal_v1 as runner


class CompiledSurfaceSignalContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = construction.build_dataset()

    def test_dataset_is_balanced_source_disjoint_and_evaluation_only(self):
        prior = construction.load_json(construction.PRIOR_DATASET)
        self.assertEqual(len(self.rows), 16)
        self.assertEqual(len({row["source_id"] for row in self.rows}), 4)
        self.assertFalse(
            {row["source_id"] for row in self.rows}
            & {row["source_id"] for row in prior}
        )
        self.assertFalse(
            {row["messages"][-1]["content"] for row in self.rows}
            & {row["messages"][-1]["content"] for row in prior}
        )
        self.assertEqual(
            {row["provider_id"] for row in self.rows}, set(construction.PROVIDERS)
        )
        self.assertEqual(
            {row["memory_mode"] for row in self.rows},
            {"background_only", "do_not_mention", "no_memory", "explicit_allowed"},
        )
        for row in self.rows:
            self.assertFalse(row["provenance"]["contains_target_utterance"])
            self.assertFalse(row["provenance"]["contains_benchmark_item"])
            self.assertFalse(row["provenance"]["training_authorized"])

    def test_primary_and_alternate_rows_are_exactly_partitioned(self):
        selected = set(construction.PRIMARY_ROW_INDICES) | set(
            construction.REFERENCE_ALT_ROW_INDICES
        )
        self.assertEqual(selected, set(range(16)))
        self.assertFalse(
            set(construction.PRIMARY_ROW_INDICES)
            & set(construction.REFERENCE_ALT_ROW_INDICES)
        )
        for primary, alternate in zip(
            construction.PRIMARY_ROW_INDICES,
            construction.REFERENCE_ALT_ROW_INDICES,
            strict=True,
        ):
            left = self.rows[primary]
            right = self.rows[alternate]
            self.assertEqual(left["source_id"], right["source_id"])
            self.assertEqual(left["provider_id"], right["provider_id"])
            self.assertEqual((left["variant_index"], right["variant_index"]), (1, 2))

    def test_only_provider_signal_representation_changes(self):
        for index in construction.PRIMARY_ROW_INDICES:
            row = self.rows[index]
            control_messages = construction.condition_messages(
                row, "abstract_top_level_control"
            )
            candidate_messages = construction.condition_messages(
                row, "compiled_surface_signal"
            )
            control = json.loads(control_messages[1]["content"])
            candidate = json.loads(candidate_messages[1]["content"])
            self.assertEqual(next(iter(control)), "persona_expression_brief")
            self.assertEqual(next(iter(candidate)), "compiled_surface_signal")
            abstract = control.pop("persona_expression_brief")
            compiled = candidate.pop("compiled_surface_signal")
            self.assertEqual(control, candidate)
            self.assertEqual(compiled, construction.compile_surface_signal(abstract))

    def test_compiler_is_generic_deterministic_and_surface_bounded(self):
        compiled_by_provider = {}
        for provider in construction.PROVIDERS:
            persona = construction._persona_brief(provider)
            first = construction.compile_surface_signal(persona)
            second = construction.compile_surface_signal(persona)
            self.assertEqual(first, second)
            encoded = json.dumps(first, ensure_ascii=False)
            self.assertFalse(
                any(term in encoded for term in construction.SIGNAL_FORBIDDEN_CASE_TERMS)
            )
            for protected in (
                "required_marker_groups",
                "forbidden_markers",
                "audited_memory_brief",
                "leftbrain_plan",
                "tool_calls",
            ):
                self.assertTrue(
                    any(protected in item for item in first["never_change"])
                )
            compiled_by_provider[provider] = first
        self.assertNotEqual(
            compiled_by_provider[construction.TARGET_PROVIDER],
            compiled_by_provider[construction.NEUTRAL_PROVIDER],
        )

    def test_provider_pairs_share_all_non_signal_inputs(self):
        for scenario in construction.SCENARIOS:
            target = construction._payload(scenario, construction.TARGET_PROVIDER)
            neutral = construction._payload(scenario, construction.NEUTRAL_PROVIDER)
            target_rest, _ = construction._extract_persona(target)
            neutral_rest, _ = construction._extract_persona(neutral)
            self.assertEqual(target_rest, neutral_rest)

    def test_prompt_contract_contains_no_assistant_reference(self):
        prompt = construction.prompt_contract(self.rows)
        self.assertEqual(prompt["case_count"], 8)
        self.assertFalse(prompt["assistant_references_in_prompt"])
        for case in prompt["cases"]:
            for condition in construction.CONDITIONS:
                messages = case[f"{condition}_messages"]
                self.assertEqual(
                    [message["role"] for message in messages], ["system", "user"]
                )

    def test_reference_pairs_are_provider_specific(self):
        references = construction._references_by_row(self.rows)
        self.assertEqual(len(references), 8)
        for value in references.values():
            self.assertEqual(len(value["own"]), 2)
            self.assertEqual(len(value["opposite"]), 2)
            self.assertFalse(set(value["own"]) & set(value["opposite"]))

    def test_runner_generates_but_cannot_train_or_save(self):
        source = Path(runner.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        generate_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "generate"
        ]
        optimizer_updates = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "update"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "optimizer"
        ]
        self.assertEqual(len(generate_calls), 1)
        self.assertEqual(optimizer_updates, [])
        for forbidden in ("value_and_grad", "save_weights(", "save_pretrained("):
            self.assertNotIn(forbidden, source)

    def test_classification_prioritizes_contract_failures(self):
        passed = {
            "each_condition_reproducible": True,
            "candidate_outputs_changed": True,
            "provider_pair_difference_not_regressed": True,
            "provider_alignment_margin_improved": True,
            "correct_provider_alignment_improved": True,
            "joint_contract_not_regressed": True,
            "semantic_complete_not_regressed": True,
            "memory_policy_not_regressed": True,
            "forbidden_pass_not_regressed": True,
            "no_exact_reference_copy": True,
            "resource_within_limit": True,
            "all_contracts_exact": True,
        }
        self.assertEqual(
            runner._classify(passed), "compiled_surface_signal_effect_confirmed"
        )
        self.assertEqual(
            runner._classify({**passed, "provider_alignment_margin_improved": False}),
            "compiled_surface_signal_alignment_not_improved",
        )
        self.assertEqual(
            runner._classify({**passed, "joint_contract_not_regressed": False}),
            "compiled_surface_signal_contract_regressed",
        )
        self.assertEqual(
            runner._classify({**passed, "each_condition_reproducible": False}),
            "compiled_surface_signal_not_reproducible",
        )
        self.assertEqual(
            runner._classify(passed, completed=False),
            "compiled_surface_signal_execution_failed",
        )

    def test_invalid_provider_condition_and_repeat_are_rejected(self):
        with self.assertRaises(ValueError):
            construction._persona_brief("invalid")
        with self.assertRaises(ValueError):
            construction.condition_messages(self.rows[0], "invalid")
        with self.assertRaises(ValueError):
            runner.run_repeat(4)


if __name__ == "__main__":
    unittest.main()
