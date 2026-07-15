#!/usr/bin/env python3

import unittest

from analyze_grounded_frame_isolation_v39 import _evaluate_gate


class AnalyzeGroundedFrameIsolationV39Tests(unittest.TestCase):
    def test_trace_gate_remains_independent_from_execution(self):
        summary = {
            "compiled_call_exact_accuracy": 1.0,
            "no_action_specificity": 1.0,
            "required_action_recall": 1.0,
            "false_action_rate": 0.0,
            "negation_violation_count": 0,
            "unsupported_execution_count": 0,
            "execution_parse_success_rate": 1.0,
            "trace_wellformed_rate": 0.89,
            "accepted_call_anchor_coverage": 1.0,
            "ungrounded_execution_count": 0,
            "model_passes_per_case": 1.0,
            "median_latency_seconds": 4.0,
        }
        targets = {
            "compiled_call_exact_accuracy": 1.0,
            "no_action_specificity": 1.0,
            "required_action_recall": 1.0,
            "false_action_rate": 0.0,
            "negation_violation_count": 0,
            "unsupported_execution_count": 0,
            "execution_parse_success_rate": 1.0,
            "trace_wellformed_rate_at_least": 0.9,
            "accepted_call_anchor_coverage": 1.0,
            "ungrounded_execution_count": 0,
            "model_passes_per_case": 1.0,
            "median_latency_seconds_at_most": 4.5,
        }
        result = _evaluate_gate(summary, targets)
        self.assertFalse(result["passed"])
        self.assertEqual(result["failed_checks"], ["trace_wellformed_rate"])


if __name__ == "__main__":
    unittest.main()
