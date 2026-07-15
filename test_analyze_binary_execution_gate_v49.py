#!/usr/bin/env python3

import json
import unittest
from copy import deepcopy
from pathlib import Path

from analyze_binary_execution_gate_v49 import evaluate_eligibility, select_model


ROOT = Path(__file__).resolve().parent
CONFIG = json.loads(
    (ROOT / "configs" / "binary_execution_gate_v49_preregistration.json").read_text(
        encoding="utf-8"
    )
)


def _passing_summary():
    return {
        "parse_success_rate": 1.0,
        "binary_accuracy": 0.95,
        "execute_precision": 1.0,
        "execute_recall": 0.95,
        "compiled_call_exact_accuracy": 0.96,
        "no_action_specificity": 1.0,
        "false_action_rate": 0.0,
        "negation_violation_count": 0,
        "accepted_call_anchor_coverage": 1.0,
        "ungrounded_execution_count": 0,
        "median_case_latency_seconds": 1.0,
        "p95_case_latency_seconds": 2.0,
    }


class AnalyzeBinaryExecutionGateV49Tests(unittest.TestCase):
    def test_zero_false_actions_cannot_hide_all_rejection(self):
        summary = _passing_summary()
        summary["execute_recall"] = 0.0
        gate = evaluate_eligibility(summary, CONFIG["eligibility_gates"])
        self.assertFalse(gate["passed"])
        self.assertIn("execute_recall", gate["failed_checks"])

    def test_any_false_action_fails_before_size_selection(self):
        summary = _passing_summary()
        summary["false_action_rate"] = 0.01
        gate = evaluate_eligibility(summary, CONFIG["eligibility_gates"])
        self.assertFalse(gate["passed"])
        self.assertIn("false_action_rate", gate["failed_checks"])

    def test_smallest_eligible_model_is_selected(self):
        summaries = {
            row["condition"]: deepcopy(_passing_summary())
            for row in CONFIG["model_conditions"]
        }
        selection = select_model(summaries, CONFIG)
        self.assertEqual(selection["selected_condition"], "qwen35_0_8b_binary")
        self.assertTrue(selection["fresh_holdout_authorized"])

    def test_no_eligible_model_authorizes_decomposition_not_runtime(self):
        summaries = {
            row["condition"]: deepcopy(_passing_summary())
            for row in CONFIG["model_conditions"]
        }
        for summary in summaries.values():
            summary["execute_precision"] = 0.9
        selection = select_model(summaries, CONFIG)
        self.assertIsNone(selection["selected_condition"])
        self.assertFalse(selection["fresh_holdout_authorized"])
        self.assertTrue(selection["architecture_decomposition_v50_authorized"])


if __name__ == "__main__":
    unittest.main()
