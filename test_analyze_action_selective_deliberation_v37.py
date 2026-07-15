#!/usr/bin/env python3

import unittest

from analyze_action_selective_deliberation_v37 import _evaluate_gate, _quantile


class AnalyzeActionSelectiveDeliberationV37Tests(unittest.TestCase):
    def test_quantile_uses_observed_upper_rank(self):
        self.assertEqual(_quantile([1.0, 2.0, 3.0, 4.0], 0.95), 4.0)
        self.assertEqual(_quantile([], 0.95), 0.0)

    def test_every_gate_must_pass(self):
        summary = {
            "compiled_call_exact_accuracy": 1.0,
            "no_action_specificity": 1.0,
            "required_action_recall": 1.0,
            "false_action_rate": 0.0,
            "negation_violation_count": 0,
            "unsupported_execution_count": 0,
            "invalid_tool_or_argument_rate": 0.0,
            "parse_success_rate": 1.0,
            "commitment_frame_micro_f1": 0.9,
            "compiled_evidence_validity_rate": 1.0,
            "escalation_rate": 0.5,
            "mean_model_passes_per_case": 2.0,
            "primary_pass_median_latency_seconds": 4.0,
            "escalated_total_p95_latency_seconds": 12.0,
        }
        targets = {
            "compiled_call_exact_accuracy_at_least": 0.97,
            "no_action_specificity": 1.0,
            "required_action_recall_at_least": 0.95,
            "false_action_rate": 0.0,
            "negation_violation_count": 0,
            "unsupported_execution_count": 0,
            "invalid_tool_or_argument_rate": 0.0,
            "parse_success_rate_at_least": 0.95,
            "commitment_frame_micro_f1_at_least": 0.75,
            "compiled_evidence_validity_rate": 1.0,
            "escalation_rate_at_most": 0.65,
            "mean_model_passes_per_case_at_most": 2.3,
            "primary_pass_median_latency_seconds_at_most": 4.5,
            "escalated_total_p95_latency_seconds_at_most": 15.0,
        }
        self.assertTrue(_evaluate_gate(summary, targets)["passed"])
        summary["false_action_rate"] = 0.01
        result = _evaluate_gate(summary, targets)
        self.assertFalse(result["passed"])
        self.assertEqual(result["failed_checks"], ["false_action_rate"])

    def test_latency_failure_cannot_be_hidden_by_accuracy(self):
        summary = {
            "compiled_call_exact_accuracy": 1.0,
            "no_action_specificity": 1.0,
            "required_action_recall": 1.0,
            "false_action_rate": 0.0,
            "negation_violation_count": 0,
            "unsupported_execution_count": 0,
            "invalid_tool_or_argument_rate": 0.0,
            "parse_success_rate": 1.0,
            "commitment_frame_micro_f1": 1.0,
            "compiled_evidence_validity_rate": 1.0,
            "escalation_rate": 0.5,
            "mean_model_passes_per_case": 2.0,
            "primary_pass_median_latency_seconds": 5.0,
            "escalated_total_p95_latency_seconds": 16.0,
        }
        targets = {
            "compiled_call_exact_accuracy_at_least": 0.97,
            "no_action_specificity": 1.0,
            "required_action_recall_at_least": 0.95,
            "false_action_rate": 0.0,
            "negation_violation_count": 0,
            "unsupported_execution_count": 0,
            "invalid_tool_or_argument_rate": 0.0,
            "parse_success_rate_at_least": 0.95,
            "commitment_frame_micro_f1_at_least": 0.75,
            "compiled_evidence_validity_rate": 1.0,
            "escalation_rate_at_most": 0.65,
            "mean_model_passes_per_case_at_most": 2.3,
            "primary_pass_median_latency_seconds_at_most": 4.5,
            "escalated_total_p95_latency_seconds_at_most": 15.0,
        }
        result = _evaluate_gate(summary, targets)
        self.assertFalse(result["passed"])
        self.assertEqual(
            result["failed_checks"],
            [
                "primary_pass_median_latency_seconds",
                "escalated_total_p95_latency_seconds",
            ],
        )


if __name__ == "__main__":
    unittest.main()
