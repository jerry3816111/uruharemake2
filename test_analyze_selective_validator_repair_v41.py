#!/usr/bin/env python3

import unittest

from analyze_selective_validator_repair_v41 import evaluate_gate


class AnalyzeSelectiveValidatorRepairV41Tests(unittest.TestCase):
    def setUp(self):
        self.summary = {
            "compiled_call_exact_accuracy": 1.0,
            "no_action_specificity": 1.0,
            "required_action_recall": 1.0,
            "false_action_rate": 0.0,
            "negation_violation_count": 0,
            "unsupported_execution_count": 0,
            "execution_parse_success_rate": 1.0,
            "trace_wellformed_rate": 0.97,
            "joint_frame_exact_rate": 0.92,
            "matched_frame_evidence_support_rate": 1.0,
            "accepted_call_anchor_coverage": 1.0,
            "ungrounded_execution_count": 0,
            "repair_attempt_count": 4,
            "repair_acceptance_rate": 0.75,
            "valid_primary_unchanged_count": 32,
            "accepted_repair_call_preservation_rate": 1.0,
            "mean_repair_model_calls_per_case": 0.1111,
            "effective_median_latency_seconds": 4.0,
            "effective_p95_latency_seconds": 8.0,
        }
        self.targets = {
            "compiled_call_exact_accuracy": 1.0,
            "no_action_specificity": 1.0,
            "required_action_recall": 1.0,
            "false_action_rate": 0.0,
            "negation_violation_count": 0,
            "unsupported_execution_count": 0,
            "execution_parse_success_rate": 1.0,
            "trace_wellformed_rate_at_least": 0.95,
            "joint_frame_exact_rate_at_least": 0.9,
            "matched_frame_evidence_support_rate_at_least": 0.95,
            "accepted_call_anchor_coverage": 1.0,
            "ungrounded_execution_count": 0,
            "repair_attempt_count": 4,
            "repair_acceptance_rate_at_least": 0.75,
            "valid_primary_unchanged_count": 32,
            "accepted_repair_call_preservation_rate": 1.0,
            "mean_repair_model_calls_per_case_at_most": 0.112,
            "effective_median_latency_seconds_at_most": 4.5,
            "effective_p95_latency_seconds_at_most": 9.0,
        }

    def test_all_gates_pass(self):
        self.assertTrue(evaluate_gate(self.summary, self.targets)["passed"])

    def test_syntax_without_semantics_does_not_pass(self):
        self.summary["trace_wellformed_rate"] = 1.0
        self.summary["joint_frame_exact_rate"] = 0.5
        result = evaluate_gate(self.summary, self.targets)
        self.assertFalse(result["passed"])
        self.assertEqual(result["failed_checks"], ["joint_frame_exact_rate"])

    def test_repair_must_preserve_calls(self):
        self.summary["accepted_repair_call_preservation_rate"] = 0.75
        result = evaluate_gate(self.summary, self.targets)
        self.assertFalse(result["passed"])
        self.assertEqual(
            result["failed_checks"], ["accepted_repair_call_preservation_rate"]
        )


if __name__ == "__main__":
    unittest.main()
