#!/usr/bin/env python3

import json
import unittest
from pathlib import Path

from analyze_action_intent_frame_v36 import _gate


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "action_intent_frame_v36_preregistration.json"


class AnalyzeActionIntentFrameV36Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        cls.target = config["development_gates_per_model"]

    def perfect_summary(self):
        return {
            "compiled_call_exact_accuracy": 1.0,
            "no_action_specificity": 1.0,
            "required_action_recall": 1.0,
            "false_action_rate": 0.0,
            "negation_violation_count": 0,
            "unsupported_execution_count": 0,
            "invalid_tool_or_argument_rate": 0.0,
            "utterance_state_accuracy": 1.0,
            "joint_frame_exact_accuracy": 1.0,
            "requested_frame_precision": 1.0,
            "requested_frame_recall": 1.0,
            "commitment_frame_micro_f1": 1.0,
            "parse_success_rate": 1.0,
            "compiled_evidence_validity_rate": 1.0,
            "median_latency_seconds": 1.0,
            "p95_latency_seconds": 2.0,
        }

    def test_perfect_summary_passes_every_frozen_gate(self):
        result = _gate(self.perfect_summary(), self.target)
        self.assertTrue(result["passed"])
        self.assertEqual(result["failed_checks"], [])

    def test_single_below_threshold_metric_fails_without_averaging(self):
        summary = self.perfect_summary()
        summary["compiled_call_exact_accuracy"] = 0.89
        result = _gate(summary, self.target)
        self.assertFalse(result["passed"])
        self.assertEqual(result["failed_checks"], ["compiled_call_exact_accuracy"])

    def test_any_false_action_fails_strict_safety_gate(self):
        summary = self.perfect_summary()
        summary["false_action_rate"] = 1 / 36
        result = _gate(summary, self.target)
        self.assertFalse(result["passed"])
        self.assertIn("false_action_rate", result["failed_checks"])


if __name__ == "__main__":
    unittest.main()
