#!/usr/bin/env python3

import unittest

from analyze_target_event_map_v51 import (
    compare,
    evaluate_absolute,
    evaluate_comparison,
)


class AnalyzeTargetEventMapV51Tests(unittest.TestCase):
    def test_absolute_gate_requires_zero_false_actions(self):
        summary = {
            "parse_success_rate": 1.0,
            "commitment_accuracy": 0.9,
            "requested_commitment_precision": 1.0,
            "requested_commitment_recall": 0.95,
            "compiled_call_exact_count": 46,
            "compiled_call_exact_accuracy": 0.9583,
            "no_action_specificity": 1.0,
            "false_action_count": 1,
            "false_action_rate": 0.0208,
            "negation_violation_count": 0,
            "accepted_call_anchor_coverage": 1.0,
            "ungrounded_execution_count": 0,
            "median_case_latency_seconds": 2.0,
            "p95_case_latency_seconds": 4.0,
        }
        gates = {
            "parse_success_rate": 1.0,
            "commitment_accuracy_at_least": 0.8689,
            "requested_commitment_precision": 1.0,
            "requested_commitment_recall_at_least": 0.9143,
            "compiled_call_exact_count_at_least": 45,
            "compiled_call_exact_accuracy_at_least": 0.9375,
            "no_action_specificity": 1.0,
            "false_action_count": 0,
            "false_action_rate": 0.0,
            "negation_violation_count": 0,
            "accepted_call_anchor_coverage": 1.0,
            "ungrounded_execution_count": 0,
            "median_case_latency_seconds_at_most": 8.0,
            "p95_case_latency_seconds_at_most": 15.0,
        }
        result = evaluate_absolute(summary, gates)
        self.assertFalse(result["passed"])
        self.assertIn("false_action_count", result["failed_checks"])

    def test_comparison_records_fixes_and_regressions(self):
        base_row = {
            "case_id": "a",
            "target_id": "motion.wave",
            "user_input": "x",
            "commitment": "requested",
            "predicted_commitment": "mentioned",
            "correct": False,
        }
        fixed_row = {**base_row, "predicted_commitment": "requested", "correct": True}
        control = {
            "target_predictions": [base_row],
            "compiled_call_failures": [{"case_id": "a"}],
            "commitment_correct_count": 0,
            "compiled_call_exact_count": 0,
            "false_action_count": 1,
        }
        candidate = {
            "target_predictions": [fixed_row],
            "compiled_call_failures": [],
            "commitment_correct_count": 1,
            "compiled_call_exact_count": 1,
            "false_action_count": 0,
        }
        result = compare(control, candidate)
        self.assertEqual(result["fixed_semantic_count"], 1)
        self.assertEqual(result["semantic_regression_count"], 0)
        self.assertEqual(result["fixed_call_count"], 1)
        self.assertEqual(result["call_regression_count"], 0)

    def test_comparison_gate_rejects_any_regression(self):
        comparison = {
            "commitment_correct_count_delta": 2,
            "compiled_call_exact_count_delta": 2,
            "false_action_count_delta": -1,
            "semantic_regression_count": 1,
            "call_regression_count": 0,
        }
        gates = {
            "commitment_correct_count_delta_at_least": 2,
            "compiled_call_exact_count_delta_at_least": 2,
            "false_action_count_delta_at_most": -1,
            "semantic_regression_count": 0,
            "call_regression_count": 0,
        }
        result = evaluate_comparison(comparison, gates)
        self.assertFalse(result["passed"])
        self.assertIn("semantic_regression_count", result["failed_checks"])


if __name__ == "__main__":
    unittest.main()
