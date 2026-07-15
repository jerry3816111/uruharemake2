#!/usr/bin/env python3

import unittest

from analyze_grounded_commitment_classifier_v42 import (
    evaluate_gate,
    summarize_condition,
)
from grounded_commitment_classifier_v42 import ground_supported_targets
from grounded_frame_isolation_v39 import load_v39_anchor_ontology


class AnalyzeGroundedCommitmentClassifierV42Tests(unittest.TestCase):
    def setUp(self):
        self.summary = {
            "candidate_target_recall": 1.0,
            "candidate_precision": 1.0,
            "classifier_parse_success_rate": 1.0,
            "commitment_accuracy": 0.97,
            "requested_commitment_precision": 1.0,
            "requested_commitment_recall": 0.96,
            "supported_frame_case_exact_rate": 0.95,
            "selected_evidence_support_rate": 0.96,
            "compiled_call_exact_accuracy": 0.98,
            "no_action_specificity": 1.0,
            "required_action_recall": 0.96,
            "false_action_rate": 0.0,
            "negation_violation_count": 0,
            "unsupported_execution_count": 0,
            "accepted_call_anchor_coverage": 1.0,
            "ungrounded_execution_count": 0,
            "mean_classifier_calls_per_case": 1.0556,
            "median_case_latency_seconds": 3.0,
            "p95_case_latency_seconds": 8.0,
        }
        self.targets = {
            "candidate_target_recall": 1.0,
            "candidate_precision": 1.0,
            "classifier_parse_success_rate_at_least": 0.97,
            "commitment_accuracy_at_least": 0.95,
            "requested_commitment_precision": 1.0,
            "requested_commitment_recall_at_least": 0.95,
            "supported_frame_case_exact_rate_at_least": 0.94,
            "selected_evidence_support_rate_at_least": 0.95,
            "compiled_call_exact_accuracy_at_least": 0.97,
            "no_action_specificity": 1.0,
            "required_action_recall_at_least": 0.95,
            "false_action_rate": 0.0,
            "negation_violation_count": 0,
            "unsupported_execution_count": 0,
            "accepted_call_anchor_coverage": 1.0,
            "ungrounded_execution_count": 0,
            "mean_classifier_calls_per_case_at_most": 1.056,
            "median_case_latency_seconds_at_most": 4.5,
            "p95_case_latency_seconds_at_most": 10.0,
        }

    def test_all_gates_pass(self):
        self.assertTrue(evaluate_gate(self.summary, self.targets)["passed"])

    def test_false_requested_commitment_is_independent_failure(self):
        self.summary["requested_commitment_precision"] = 0.95
        result = evaluate_gate(self.summary, self.targets)
        self.assertFalse(result["passed"])
        self.assertEqual(result["failed_checks"], ["requested_commitment_precision"])

    def test_single_case_summary_compiles_grounded_request(self):
        user_input = "一度手を振って。"
        candidates = ground_supported_targets(user_input, load_v39_anchor_ontology())
        wave = next(row for row in candidates if row["target_id"] == "motion.wave")
        case = {
            "id": "case",
            "family": "test",
            "user_input": user_input,
            "expected_frames": [
                {
                    "domain": "motion",
                    "value": "wave",
                    "commitment": "requested",
                    "evidence_options": ["手を振って"],
                }
            ],
            "expected_calls": [
                {"name": "play_motion", "arguments": {"motion": "wave"}}
            ],
            "forbidden_calls": [],
            "expected_no_action": False,
            "expected_derived_state": "explicit_current_request",
        }
        report = {
            "candidate_rows": [
                {
                    "case_id": "case",
                    "user_input": user_input,
                    "candidates": [wave],
                }
            ],
            "judgment_rows": [
                {
                    "condition": "model",
                    "case_id": "case",
                    "target_id": "motion.wave",
                    "result": {
                        "parsed": {
                            "parse_success": True,
                            "errors": [],
                            "commitment": "requested",
                            "evidence_index": 0,
                        },
                        "response_metrics": {"wall_seconds": 1.0},
                    },
                }
            ],
        }
        summary = summarize_condition(
            report,
            {"cases": [case]},
            {"summary": {"supported_target_recall": 1.0, "candidate_precision": 1.0}},
            "model",
        )
        self.assertEqual(summary["commitment_accuracy"], 1.0)
        self.assertEqual(summary["compiled_call_exact_accuracy"], 1.0)
        self.assertEqual(summary["false_action_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()
