#!/usr/bin/env python3

import re
import unittest

from audit_grounded_action_candidates_v42 import audit_case, audit_dataset


class GroundedActionCandidateAuditV42Tests(unittest.TestCase):
    def test_audit_separates_missing_extra_and_unsupported(self):
        ontology = {
            ("motion", "wave"): [re.compile("手を振")],
            ("gaze", "left"): [re.compile("左")],
        }
        case = {
            "id": "case",
            "family": "test",
            "user_input": "手を振って右を見て、そして飛んで。",
            "expected_frames": [
                {
                    "domain": "motion",
                    "value": "wave",
                    "commitment": "requested",
                    "evidence_options": ["手を振って"],
                },
                {
                    "domain": "gaze",
                    "value": "right",
                    "commitment": "requested",
                    "evidence_options": ["右を見て"],
                },
                {
                    "domain": "motion",
                    "value": "unsupported",
                    "commitment": "requested",
                    "evidence_options": ["飛んで"],
                },
            ],
        }
        row = audit_case(case, ontology)
        self.assertEqual(row["true_positive_targets"], [["motion", "wave"]])
        self.assertEqual(row["missing_targets"], [["gaze", "right"]])
        self.assertEqual(row["extra_targets"], [])
        self.assertEqual(row["expected_unsupported_frame_count"], 1)

    def test_dataset_summary_counts_exact_candidate_sets(self):
        ontology = {("motion", "wave"): [re.compile("手を振")]}
        dataset = {
            "cases": [
                {
                    "id": "hit",
                    "family": "test",
                    "user_input": "手を振って。",
                    "expected_frames": [
                        {
                            "domain": "motion",
                            "value": "wave",
                            "commitment": "requested",
                            "evidence_options": ["手を振って"],
                        }
                    ],
                },
                {
                    "id": "empty",
                    "family": "test",
                    "user_input": "雑談しよう。",
                    "expected_frames": [],
                },
            ]
        }
        summary = audit_dataset(dataset, ontology)["summary"]
        self.assertEqual(summary["supported_target_recall"], 1.0)
        self.assertEqual(summary["candidate_precision"], 1.0)
        self.assertEqual(summary["case_exact_candidate_set_rate"], 1.0)
        self.assertEqual(summary["empty_supported_target_specificity"], 1.0)


if __name__ == "__main__":
    unittest.main()
