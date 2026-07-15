#!/usr/bin/env python3

import json
import unittest
from pathlib import Path

from run_relation_safety_state_v58_holdout import CONDITIONS
from run_target_event_map_v51 import build_candidate_rows


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "relation_safety_state_v58_holdout_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "relation_safety_state_v58_holdout.json"


class RelationSafetyStateV58HoldoutHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load = lambda path: json.loads(path.read_text(encoding="utf-8"))
        cls.config = load(CONFIG_PATH)
        cls.dataset = load(DATASET_PATH)
        cls.runner_source = (
            ROOT / cls.config["frozen_inputs"]["runner"]
        ).read_text(encoding="utf-8")
        cls.analyzer_source = (
            ROOT / cls.config["frozen_inputs"]["analyzer"]
        ).read_text(encoding="utf-8")

    def test_runner_uses_one_model_result_for_both_states(self):
        self.assertEqual(self.runner_source.count("_run_judgment("), 1)
        self.assertIn("state56 = resolve_v56", self.runner_source)
        self.assertIn("state58 = resolve_v58", self.runner_source)
        self.assertIn("select_commitment(state56, fallback)", self.runner_source)
        self.assertIn("select_commitment(state58, fallback)", self.runner_source)
        self.assertIn('"shared_fallback_commitment": fallback', self.runner_source)

    def test_same_frozen_compiler_is_used_for_both_conditions(self):
        self.assertEqual(
            self.runner_source.count("compile_relation_authorized_v57("), 2
        )
        self.assertEqual(tuple(self.config["conditions"]), CONDITIONS)
        self.assertNotIn("compile_target_relative_v48", self.runner_source)

    def test_model_inputs_contain_no_gold_fields(self):
        rows = build_candidate_rows(self.dataset)
        self.assertEqual(len(rows), 64)
        for row in rows:
            self.assertNotIn("expected_frames", row)
            self.assertNotIn("expected_calls", row)
            self.assertNotIn("gold", row)

    def test_analyzer_separates_state_compiler_source_and_family(self):
        for required in (
            "summarize_state",
            "summarize_compiler",
            "summarize_relation_diagnostics",
            '"source_groups"',
            '"family_groups"',
            '"state_regression_count"',
            '"case_regression_count"',
            '"required_call_recall"',
            '"false_action_case_count"',
        ):
            self.assertIn(required, self.analyzer_source)

    def test_harness_cannot_authorize_runtime_or_physical_action(self):
        for key in (
            "runtime_change_authorized",
            "shadow_integration_authorized",
            "physical_vrm_execution_enabled",
            "complete_rightbrain_claim_authorized",
            "broad_human_likeness_claim_authorized",
        ):
            self.assertFalse(self.config[key], key)
            self.assertIn(f'"{key}": False', self.analyzer_source)


if __name__ == "__main__":
    unittest.main()
