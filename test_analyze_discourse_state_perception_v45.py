#!/usr/bin/env python3

import unittest

from analyze_discourse_state_perception_v45 import evaluate_development_decision


class AnalyzeDiscourseStatePerceptionV45Tests(unittest.TestCase):
    def test_metric_pass_cannot_hide_a_semantic_regression(self):
        result = evaluate_development_decision(
            {"passed": True},
            {"fixed": [{"case_id": "a"}], "regressed": [{"case_id": "b"}]},
        )
        self.assertFalse(result["passed"])
        self.assertFalse(result["no_semantic_regression_vs_v44"])

    def test_full_metric_pass_without_regression_can_advance(self):
        result = evaluate_development_decision(
            {"passed": True}, {"fixed": [{"case_id": "a"}], "regressed": []}
        )
        self.assertTrue(result["passed"])


if __name__ == "__main__":
    unittest.main()
