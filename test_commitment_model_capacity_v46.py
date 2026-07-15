#!/usr/bin/env python3

import json
import unittest
from pathlib import Path

from analyze_commitment_model_capacity_v46 import (
    evaluate_model_eligibility,
    select_model,
)
from run_commitment_model_capacity_v46 import (
    _validate_inputs,
    build_prompt,
    build_user_payload,
)
from run_discourse_state_perception_v45_holdout import build_candidate_rows


ROOT = Path(__file__).resolve().parent


class CommitmentModelCapacityV46Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load = lambda path: json.loads((ROOT / path).read_text(encoding="utf-8"))
        cls.config = load("configs/commitment_model_capacity_v46_preregistration.json")
        cls.v45_config = load("configs/discourse_state_perception_v45_preregistration.json")
        cls.v44_lock = load("configs/commitment_target_isolation_v44_semantic_lock.json")
        cls.dataset = load("datasets/discourse_state_perception_v45_holdout.json")
        cls.audit = load("reports/discourse_state_perception_v45_holdout_audit.json")

    def _summary(self, correct=55, latency=2.0, false_action=0.0):
        return {
            "classifier_parse_success_rate": 1.0,
            "commitment_accuracy": round(correct / 61, 4),
            "commitment_correct_count": correct,
            "requested_commitment_precision": 1.0,
            "requested_commitment_recall": 1.0,
            "compiled_call_exact_accuracy": 1.0,
            "compiled_call_exact_count": 48,
            "no_action_specificity": 1.0,
            "false_action_rate": false_action,
            "negation_violation_count": 0,
            "unsupported_execution_count": 0,
            "accepted_call_anchor_coverage": 1.0,
            "ungrounded_execution_count": 0,
            "extra_candidate_requested_count": 0,
            "median_case_latency_seconds": latency,
            "p95_case_latency_seconds": latency * 2,
        }

    def test_frozen_inputs_prompt_and_payload_validate_without_inference(self):
        _validate_inputs(self.config, self.dataset, self.audit)
        prompt = build_prompt(self.config, self.v45_config, self.v44_lock)
        self.assertIn("focus_discourse_state_signals", prompt)
        candidate_row = build_candidate_rows(self.dataset)[0]
        payload = build_user_payload(
            self.config,
            self.v45_config,
            candidate_row,
            candidate_row["candidates"][0],
        )
        self.assertIn("focus_discourse_state_signals", payload)

    def test_safety_failure_blocks_model_before_accuracy_ranking(self):
        summary = self._summary(correct=60, latency=0.5, false_action=0.1)
        gate = evaluate_model_eligibility(summary, self.config["eligibility_gates"])
        self.assertFalse(gate["passed"])
        self.assertIn("false_action_rate", gate["failed_checks"])

    def test_fast_model_within_one_correct_target_is_selected(self):
        summaries = {
            row["condition"]: self._summary(correct=55, latency=3.0)
            for row in self.config["model_conditions"]
        }
        summaries["qwen35_9b"] = self._summary(correct=56, latency=5.0)
        summaries["qwen35_2b"] = self._summary(correct=55, latency=1.2)
        selection = select_model(summaries, self.config)
        self.assertEqual(selection["selected_condition"], "qwen35_2b")
        self.assertTrue(selection["fresh_v46_holdout_authorized"])

    def test_no_safe_model_authorizes_decomposition_not_runtime(self):
        summaries = {
            row["condition"]: self._summary(correct=60, latency=1.0, false_action=0.1)
            for row in self.config["model_conditions"]
        }
        selection = select_model(summaries, self.config)
        self.assertIsNone(selection["selected_condition"])
        self.assertTrue(selection["architecture_decomposition_development_authorized"])
        self.assertFalse(selection["fresh_v46_holdout_authorized"])


if __name__ == "__main__":
    unittest.main()
