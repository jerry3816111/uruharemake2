#!/usr/bin/env python3
"""Validate the frozen negative V2 construction result."""

from __future__ import annotations

import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CLOSURE_PATH = (
    ROOT
    / "configs"
    / "consolidation_support_equivalence_v2_construction_closure.json"
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ConsolidationSupportEquivalenceV2ResultTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.closure = _load(CLOSURE_PATH)
        cls.audit = _load(
            ROOT / cls.closure["artifacts"]["audit_json"]["path"]
        )
        cls.final_dataset = _load(
            ROOT / cls.closure["artifacts"]["final_dataset"]["path"]
        )

    def test_construction_failure_and_stop_are_frozen(self):
        self.assertEqual(
            self.closure["decision"],
            "construction_fail_stop_support_attribution_hypothesis",
        )
        self.assertFalse(self.audit["all_construction_gates_pass"])
        self.assertEqual(self.final_dataset["cases"], [])
        self.assertFalse(
            self.closure["advancement"]["candidate_pilot_authorized"]
        )
        self.assertFalse(
            self.closure["advancement"]["runtime_restoration_authorized"]
        )
        self.assertIn(
            "Do not change the carrier",
            self.closure["stop_rule"],
        )

    def test_all_108_calls_are_preserved_without_retry(self):
        calls = self.audit["calls"]
        self.assertEqual(len(calls), 108)
        self.assertEqual(self.audit["transport_attempts"], 108)
        self.assertEqual(
            len({row["call_key"] for row in calls}),
            108,
        )
        self.assertTrue(
            all(row["transport_attempts"] == 1 for row in calls)
        )
        self.assertEqual(
            sum(bool(row["transport_error"]) for row in calls),
            0,
        )
        self.assertEqual(
            sum(row["parse_success"] for row in calls),
            50,
        )

    def test_carrier_failures_are_attributed_by_reviewer(self):
        by_reviewer = {
            reviewer: [
                row
                for row in self.audit["calls"]
                if row["reviewer"] == reviewer
            ]
            for reviewer in ("reviewer_a", "reviewer_b")
        }
        self.assertEqual(
            sum(row["parse_success"] for row in by_reviewer["reviewer_a"]),
            45,
        )
        self.assertEqual(
            sum(row["parse_success"] for row in by_reviewer["reviewer_b"]),
            5,
        )
        errors_a = Counter(
            row["parse_error"]
            for row in by_reviewer["reviewer_a"]
            if row["parse_error"]
        )
        errors_b = Counter(
            row["parse_error"]
            for row in by_reviewer["reviewer_b"]
            if row["parse_error"]
        )
        self.assertEqual(
            errors_a,
            {
                "ValueError: support_set_type": 7,
                "ValueError: empty_minimal_support_set": 2,
            },
        )
        self.assertEqual(
            errors_b,
            {
                "ValueError: argument_keys": 40,
                "ValueError: tool_call_count": 9,
            },
        )

    def test_candidate_and_production_remained_untouched(self):
        self.assertEqual(self.audit["candidate_model_calls"], 0)
        self.assertEqual(self.audit["production_database_writes"], 0)
        limits = self.audit["evidence_limits"]
        self.assertFalse(limits["candidate_inference_authorized"])
        self.assertFalse(limits["runtime_restoration_authorized"])
        self.assertFalse(limits["production_activation_authorized"])
        self.assertFalse(limits["retrieval_improvement_validated"])
        self.assertFalse(limits["dialogue_improvement_validated"])
        self.assertFalse(limits["human_likeness_validated"])

    def test_failure_is_measurement_carrier_not_semantic_candidate_evidence(self):
        attribution = self.closure["failure_attribution"]
        self.assertEqual(
            attribution["primary_failure_layer"],
            "independent_reviewer_output_carrier",
        )
        self.assertFalse(
            attribution["qwen35_4b_candidate_quality_evaluated"]
        )
        self.assertFalse(
            attribution["memory_runtime_quality_evaluated"]
        )
        self.assertFalse(
            attribution["human_like_memory_improvement_evaluated"]
        )

    def test_all_result_artifacts_are_hash_bound(self):
        for name, artifact in self.closure["artifacts"].items():
            self.assertEqual(
                _sha256(ROOT / artifact["path"]),
                artifact["sha256"],
                name,
            )


if __name__ == "__main__":
    unittest.main()
