#!/usr/bin/env python3

import json
import unittest
from pathlib import Path

from analyze_discourse_state_perception_v45_holdout import (
    CANDIDATE,
    CONTROL,
    compare_conditions,
    evaluate_absolute_gates,
    evaluate_comparison_gates,
    summarize_condition,
)
from run_discourse_state_perception_v45_holdout import (
    CONDITIONS,
    build_candidate_rows,
    build_matched_prompts,
    build_user_payload,
)


ROOT = Path(__file__).resolve().parent


class DiscourseStatePerceptionV45HoldoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load = lambda path: json.loads((ROOT / path).read_text(encoding="utf-8"))
        cls.lock = load("configs/discourse_state_perception_v45_holdout_lock.json")
        cls.v45_config = load("configs/discourse_state_perception_v45_preregistration.json")
        cls.v44_lock = load("configs/commitment_target_isolation_v44_semantic_lock.json")
        cls.dataset = load("datasets/discourse_state_perception_v45_holdout.json")
        cls.audit = load("reports/discourse_state_perception_v45_holdout_audit.json")
        cls.candidate_rows = build_candidate_rows(cls.dataset)
        cls.gold = {
            (case["id"], f"{frame['domain']}.{frame['value']}"): frame["commitment"]
            for case in cls.dataset["cases"]
            for frame in case["expected_frames"]
            if frame["value"] != "unsupported"
        }

    def _perfect_report(self):
        rows = []
        for condition in CONDITIONS:
            for candidate_row in self.candidate_rows:
                for candidate in candidate_row["candidates"]:
                    target_id = candidate["target_id"]
                    commitment = self.gold.get(
                        (candidate_row["case_id"], target_id), "mentioned"
                    )
                    rows.append(
                        {
                            "condition": condition,
                            "case_id": candidate_row["case_id"],
                            "target_id": target_id,
                            "result": {
                                "parsed": {
                                    "parse_success": True,
                                    "errors": [],
                                    "commitment": commitment,
                                },
                                "response_metrics": {"wall_seconds": 0.1},
                            },
                        }
                    )
        return {"candidate_rows": self.candidate_rows, "judgment_rows": rows}

    def _summary(self, report, condition):
        return summarize_condition(
            report,
            self.dataset,
            self.audit,
            condition,
            self.lock["taxonomy_boundary_tags"],
        )

    def test_matched_prompts_and_payloads_differ_only_at_v45_boundary_logic(self):
        prompts = build_matched_prompts(self.v45_config, self.v44_lock)
        self.assertEqual(set(prompts), set(CONDITIONS))
        self.assertNotEqual(prompts[CONTROL], prompts[CANDIDATE])
        case_row = next(
            row for row in self.candidate_rows if row["case_id"] == "v45h_boundary_01"
        )
        candidate = case_row["candidates"][0]
        control_payload = build_user_payload(
            CONTROL, case_row, candidate, self.v45_config
        )
        candidate_payload = build_user_payload(
            CANDIDATE, case_row, candidate, self.v45_config
        )
        self.assertNotIn("focus_discourse_state_signals", control_payload)
        self.assertIn("focus_discourse_state_signals", candidate_payload)

    def test_summary_handles_extra_grounding_candidates_without_hiding_them(self):
        summary = self._summary(self._perfect_report(), CANDIDATE)
        self.assertEqual(summary["candidate_target_count"], 63)
        self.assertEqual(summary["supported_target_count"], 61)
        self.assertEqual(summary["extra_candidate_count"], 2)
        self.assertEqual(summary["extra_candidate_requested_count"], 0)
        self.assertEqual(summary["commitment_accuracy"], 1.0)
        self.assertEqual(summary["requested_commitment_precision"], 1.0)
        self.assertEqual(summary["requested_commitment_recall"], 1.0)
        self.assertEqual(summary["compiled_call_exact_accuracy"], 0.9583)
        self.assertEqual(summary["compiled_call_failure_case_count"], 2)
        self.assertEqual(summary["supported_frame_exact_case_count"], 46)

    def test_requested_extra_candidate_is_counted_as_a_false_positive(self):
        report = self._perfect_report()
        expected_keys = set(self.gold)
        row = next(
            row
            for row in report["judgment_rows"]
            if row["condition"] == CANDIDATE
            and (row["case_id"], row["target_id"]) not in expected_keys
        )
        row["result"]["parsed"]["commitment"] = "requested"
        summary = self._summary(report, CANDIDATE)
        self.assertEqual(summary["extra_candidate_requested_count"], 1)
        self.assertLess(summary["requested_commitment_precision"], 1.0)

    def test_preregistered_two_point_gain_cannot_pass_with_only_one_fixed_target(self):
        report = self._perfect_report()
        control = self._summary(report, CONTROL)
        candidate = self._summary(report, CANDIDATE)
        taxonomy_keys = [
            (row["case_id"], row["target_id"])
            for row in candidate["target_predictions"]
            if row["is_expected_supported_target"]
            and set(
                next(
                    case["evaluation_tags"]
                    for case in self.dataset["cases"]
                    if case["id"] == row["case_id"]
                )
            )
            & set(self.lock["taxonomy_boundary_tags"])
        ]
        key = taxonomy_keys[0]
        for row in control["target_predictions"]:
            if (row["case_id"], row["target_id"]) == key:
                row["commitment"] = "mentioned"
        control["commitment_correct_count"] -= 1
        control["taxonomy_boundary_correct_count"] -= 1
        comparison = compare_conditions(
            control,
            candidate,
            self.dataset,
            self.lock["taxonomy_boundary_tags"],
        )
        gate = evaluate_comparison_gates(
            comparison, self.lock["matched_comparison_gates"]
        )
        self.assertEqual(comparison["fixed_count"], 1)
        self.assertEqual(comparison["commitment_accuracy_delta_vs_control"], 0.0164)
        self.assertFalse(gate["passed"])

    def test_perfect_semantics_passes_absolute_safety_and_latency_gate(self):
        summary = self._summary(self._perfect_report(), CANDIDATE)
        gate = evaluate_absolute_gates(
            summary, self.lock["candidate_absolute_gates"]
        )
        self.assertTrue(gate["passed"], gate["failed_checks"])


if __name__ == "__main__":
    unittest.main()
