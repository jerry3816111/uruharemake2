#!/usr/bin/env python3

import unittest

from selective_validator_repair_v41 import (
    evaluate_repair_acceptance,
    select_trace,
)


def _compilation(calls=None, grounded=True):
    calls = calls or []
    frames = [
        {"matched_anchor": {"text": "x"}} if grounded else {}
        for _ in calls
    ]
    return {
        "accepted_calls": calls,
        "accepted_frames": frames,
        "ungrounded_execution_count": 0 if grounded else len(calls),
        "fail_closed": False,
    }


class SelectiveValidatorRepairV41Tests(unittest.TestCase):
    def test_accepts_wellformed_call_preserving_repair(self):
        call = {"name": "play_motion", "arguments": {"motion": "wave"}}
        result = evaluate_repair_acceptance(
            _compilation([call]),
            {"trace_wellformed": True},
            _compilation([call]),
        )
        self.assertTrue(result["accepted"])
        self.assertTrue(result["grounded_calls_preserved"])

    def test_rejects_repair_that_introduces_action(self):
        call = {"name": "play_motion", "arguments": {"motion": "wave"}}
        result = evaluate_repair_acceptance(
            _compilation(),
            {"trace_wellformed": True},
            _compilation([call]),
        )
        self.assertFalse(result["accepted"])
        self.assertIn("grounded_calls_changed", result["reasons"])

    def test_rejects_structurally_imperfect_repair(self):
        result = evaluate_repair_acceptance(
            _compilation(),
            {"trace_wellformed": False},
            _compilation(),
        )
        self.assertFalse(result["accepted"])
        self.assertIn("repair_trace_not_wellformed", result["reasons"])

    def test_rejected_repair_falls_back_to_original(self):
        original_parsed = {"trace_wellformed": False, "frames": []}
        original_compilation = _compilation()
        selected = select_trace(
            original_parsed,
            original_compilation,
            {"trace_wellformed": False, "frames": []},
            _compilation(),
        )
        self.assertEqual(selected["source"], "original_v39_fallback")
        self.assertIs(selected["parsed"], original_parsed)


if __name__ == "__main__":
    unittest.main()
