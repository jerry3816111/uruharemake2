#!/usr/bin/env python3

import unittest

from analyze_domain_separated_action_contract_v40 import evaluate_gate


class AnalyzeDomainSeparatedActionContractV40Tests(unittest.TestCase):
    def setUp(self):
        self.summary = {
            "compiled_call_exact_accuracy": 1.0,
            "no_action_specificity": 1.0,
            "required_action_recall": 1.0,
            "false_action_rate": 0.0,
            "negation_violation_count": 0,
            "unsupported_execution_count": 0,
            "execution_parse_success_rate": 1.0,
            "trace_wellformed_rate": 1.0,
            "accepted_call_anchor_coverage": 1.0,
            "ungrounded_execution_count": 0,
            "model_passes_per_case": 1.0,
            "median_latency_seconds": 4.0,
            "p95_latency_seconds": 5.0,
        }
        self.targets = {
            "compiled_call_exact_accuracy_at_least": 0.97,
            "no_action_specificity": 1.0,
            "required_action_recall_at_least": 0.95,
            "false_action_rate": 0.0,
            "negation_violation_count": 0,
            "unsupported_execution_count": 0,
            "execution_parse_success_rate": 1.0,
            "trace_wellformed_rate_at_least": 0.95,
            "accepted_call_anchor_coverage": 1.0,
            "ungrounded_execution_count": 0,
            "model_passes_per_case": 1.0,
            "median_latency_seconds_at_most": 4.5,
            "p95_latency_seconds_at_most": 6.0,
        }

    def test_all_gates_pass(self):
        self.assertTrue(evaluate_gate(self.summary, self.targets)["passed"])

    def test_trace_quality_cannot_hide_behind_execution_success(self):
        self.summary["trace_wellformed_rate"] = 0.94
        result = evaluate_gate(self.summary, self.targets)
        self.assertFalse(result["passed"])
        self.assertEqual(result["failed_checks"], ["trace_wellformed_rate"])

    def test_latency_tail_is_independent_gate(self):
        self.summary["p95_latency_seconds"] = 6.1
        result = evaluate_gate(self.summary, self.targets)
        self.assertFalse(result["passed"])
        self.assertEqual(result["failed_checks"], ["p95_latency_seconds"])


if __name__ == "__main__":
    unittest.main()
