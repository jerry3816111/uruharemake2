#!/usr/bin/env python3

import unittest

from analyze_action_ontology_grounding_v38 import _evaluate_gate


class AnalyzeActionOntologyGroundingV38Tests(unittest.TestCase):
    def test_accepted_calls_must_all_be_grounded(self):
        summary = {
            "compiled_call_exact_accuracy": 1.0,
            "no_action_specificity": 1.0,
            "required_action_recall": 1.0,
            "false_action_rate": 0.0,
            "negation_violation_count": 0,
            "unsupported_execution_count": 0,
            "invalid_tool_or_argument_rate": 0.0,
            "parse_success_rate": 1.0,
            "commitment_frame_micro_f1": 0.8,
            "accepted_call_anchor_coverage": 0.95,
            "ungrounded_execution_count": 0,
            "model_passes_per_case": 1.0,
            "median_latency_seconds": 4.0,
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
            "commitment_frame_micro_f1_at_least": 0.65,
            "accepted_call_anchor_coverage": 1.0,
            "ungrounded_execution_count": 0,
            "model_passes_per_case": 1.0,
            "median_latency_seconds_at_most": 4.5,
        }
        result = _evaluate_gate(summary, targets)
        self.assertFalse(result["passed"])
        self.assertEqual(result["failed_checks"], ["accepted_call_anchor_coverage"])
        summary["accepted_call_anchor_coverage"] = 1.0
        self.assertTrue(_evaluate_gate(summary, targets)["passed"])


if __name__ == "__main__":
    unittest.main()
