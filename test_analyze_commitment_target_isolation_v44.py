#!/usr/bin/env python3

import unittest

from analyze_commitment_target_isolation_v44 import _transition


class AnalyzeCommitmentTargetIsolationV44Tests(unittest.TestCase):
    def test_transition_separates_fixes_from_regressions(self):
        summaries = {
            "before": {
                "target_predictions": [
                    {"case_id": "a", "target_id": "motion.wave", "commitment": "mentioned"},
                    {"case_id": "b", "target_id": "gaze.user", "commitment": "requested"},
                ]
            },
            "after": {
                "target_predictions": [
                    {"case_id": "a", "target_id": "motion.wave", "commitment": "requested"},
                    {"case_id": "b", "target_id": "gaze.user", "commitment": "mentioned"},
                ]
            },
        }
        gold = {("a", "motion.wave"): "requested", ("b", "gaze.user"): "requested"}
        result = _transition("before", "after", summaries, gold)
        self.assertEqual([row["case_id"] for row in result["fixed"]], ["a"])
        self.assertEqual([row["case_id"] for row in result["regressed"]], ["b"])


if __name__ == "__main__":
    unittest.main()
