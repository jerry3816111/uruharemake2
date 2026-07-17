#!/usr/bin/env python3
"""Test the frozen support-attribution V1 harness."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from consolidation_support_attribution_v1_core import (
    analyze_support_attribution,
    build_coarse_control_rows,
    parse_support_tool_response,
)
from run_consolidation_support_attribution_v1_development import (
    _validate_report_progress,
    build_request_body,
)


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "consolidation_support_attribution_v1_development_preregistration.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _tool_response(indices, *, content=""):
    return {
        "message": {
            "content": content,
            "tool_calls": [
                {
                    "function": {
                        "name": "attribute_memory_support",
                        "arguments": {
                            "support_event_indices": indices,
                        },
                    }
                }
            ],
        }
    }


def _candidate_row(case, indices, *, wall_seconds=1.0):
    return {
        "id": case["id"],
        "condition": "qwen35_4b_support_attribution",
        "parse_success": True,
        "index_contract_success": True,
        "parse_error": None,
        "support_event_indices": list(indices),
        "wall_seconds": wall_seconds,
        "transport_attempts": 1,
        "transport_error": None,
    }


class ConsolidationSupportAttributionV1HarnessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = _load(CONFIG_PATH)
        cls.dataset = _load(ROOT / cls.config["dataset"]["path"])
        cls.cases = cls.dataset["cases"]

    def test_parser_accepts_only_one_closed_index_call(self):
        parsed = parse_support_tool_response(_tool_response([4, 2]))
        self.assertTrue(parsed["parse_success"])
        self.assertTrue(parsed["index_contract_success"])
        self.assertEqual(parsed["support_event_indices"], [2, 4])

        invalid_responses = (
            _tool_response([2], content="Here is the answer."),
            _tool_response([2, 2]),
            _tool_response([0]),
            _tool_response([True]),
            {
                "message": {
                    "content": "",
                    "tool_calls": [],
                }
            },
        )
        for response in invalid_responses:
            with self.subTest(response=response):
                invalid = parse_support_tool_response(response)
                self.assertFalse(invalid["parse_success"])
                self.assertEqual(invalid["support_event_indices"], [])

    def test_model_request_contains_no_gold_or_scorer_fields(self):
        case = self.cases[0]
        body = build_request_body(self.config, case)
        encoded = json.dumps(body, ensure_ascii=False)
        for forbidden in (
            "gold_support_event_indices",
            "support_mode",
            "scenario_family",
            "expected",
            "correct",
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertIn(case["derived_memory"], encoded)
        for event in case["source_events"]:
            self.assertIn(event["user"], encoded)

    def test_perfect_candidate_passes_every_frozen_gate(self):
        control_rows = build_coarse_control_rows(self.cases)
        candidate_rows = [
            _candidate_row(
                case,
                case["gold_support_event_indices"],
                wall_seconds=1.0 + (index * 0.01),
            )
            for index, case in enumerate(self.cases)
        ]
        analysis = analyze_support_attribution(
            self.cases,
            control_rows,
            candidate_rows,
            self.config["success_gates"],
        )
        self.assertTrue(analysis["all_success_gates_pass"])
        self.assertEqual(analysis["candidate"]["exact_set_match_count"], 18)
        self.assertEqual(analysis["candidate"]["false_source_count"], 0)
        self.assertEqual(analysis["candidate"]["missed_source_count"], 0)

    def test_coarse_candidate_fails_precision_and_exactness(self):
        control_rows = build_coarse_control_rows(self.cases)
        analysis = analyze_support_attribution(
            self.cases,
            control_rows,
            control_rows,
            self.config["success_gates"],
        )
        self.assertFalse(analysis["all_success_gates_pass"])
        self.assertEqual(analysis["candidate"]["exact_set_match_count"], 0)
        self.assertEqual(analysis["candidate"]["evidence_precision"], 0.1389)
        self.assertEqual(analysis["candidate"]["false_source_count"], 93)

    def test_transport_or_parse_failure_cannot_silently_pass(self):
        control_rows = build_coarse_control_rows(self.cases)
        candidate_rows = [
            _candidate_row(case, case["gold_support_event_indices"])
            for case in self.cases
        ]
        candidate_rows[0].update(
            {
                "parse_success": False,
                "index_contract_success": False,
                "support_event_indices": [],
                "transport_error": "TimeoutError",
            }
        )
        analysis = analyze_support_attribution(
            self.cases,
            control_rows,
            candidate_rows,
            self.config["success_gates"],
        )
        self.assertFalse(analysis["all_success_gates_pass"])
        self.assertFalse(
            analysis["gates"][
                "candidate_parse_success_count_exact"
            ]["passed"]
        )
        self.assertFalse(
            analysis["gates"][
                "candidate_transport_error_count_exact"
            ]["passed"]
        )

    def test_resume_progress_must_be_a_unique_dataset_prefix(self):
        control_rows = build_coarse_control_rows(self.cases)
        first_row = _candidate_row(
            self.cases[0],
            self.cases[0]["gold_support_event_indices"],
        )
        report = {
            "control_rows": control_rows,
            "candidate_rows": [first_row],
            "model_calls": 1,
            "transport_attempts_made": 1,
        }
        _validate_report_progress(report, self.dataset)

        invalid = dict(report)
        invalid["candidate_rows"] = [
            _candidate_row(
                self.cases[1],
                self.cases[1]["gold_support_event_indices"],
            )
        ]
        with self.assertRaisesRegex(ValueError, "unique dataset prefix"):
            _validate_report_progress(invalid, self.dataset)


if __name__ == "__main__":
    unittest.main()
