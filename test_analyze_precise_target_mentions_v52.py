#!/usr/bin/env python3

import unittest

from analyze_precise_target_mentions_v52 import analyze


class AnalyzePreciseTargetMentionsV52Tests(unittest.TestCase):
    def test_incomplete_report_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "incomplete"):
            analyze(
                {"completed_at": None},
                {"cases": []},
                {"expected_judgment_count": 0},
            )

    def test_failed_representation_gate_is_rejected_before_scoring(self):
        raw = {
            "completed_at": "now",
            "judgment_rows": [],
            "representation_gate": {"passed": False},
        }
        with self.assertRaisesRegex(ValueError, "representation gate"):
            analyze(raw, {"cases": []}, {"expected_judgment_count": 0})


if __name__ == "__main__":
    unittest.main()
