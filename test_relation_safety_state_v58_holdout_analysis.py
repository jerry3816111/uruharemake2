#!/usr/bin/env python3

import json
import unittest
from pathlib import Path

from analyze_relation_safety_state_v58_holdout import summarize_compiler


ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "datasets" / "relation_safety_state_v58_holdout.json"


class RelationSafetyStateV58HoldoutAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))

    def _raw_with(self, calls_by_case):
        return {
            "case_rows": [
                {
                    "case_id": case["id"],
                    "candidate_compilation": {
                        "accepted_calls": calls_by_case.get(case["id"], []),
                        "authorization_provenance_coverage": 1.0,
                        "ungrounded_execution_count": 0,
                        "commitment_mutation_count": 0,
                    },
                }
                for case in self.dataset["cases"]
            ]
        }

    def test_always_abstaining_cannot_hide_zero_action_recall(self):
        report = summarize_compiler(self._raw_with({}), self.dataset, "candidate")
        self.assertEqual(report["action_ordered_exact_accuracy"], 0.0)
        self.assertEqual(report["required_call_recall"], 0.0)
        self.assertEqual(report["no_action_specificity"], 1.0)
        self.assertLess(report["ordered_exact_accuracy"], 0.9375)

    def test_reversed_ordered_plan_is_not_exact(self):
        case = next(
            case
            for case in self.dataset["cases"]
            if case["id"] == "v58h_contrast_05"
        )
        report = summarize_compiler(
            self._raw_with({case["id"]: list(reversed(case["expected_calls"]))}),
            self.dataset,
            "candidate",
        )
        self.assertNotIn(case["id"], report["correct_case_ids"])


if __name__ == "__main__":
    unittest.main()
