#!/usr/bin/env python3

import json
import unittest
from collections import Counter
from pathlib import Path

from build_action_intent_frame_v36_development import ANNOTATIONS, build


ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "datasets" / "action_intent_frame_v36_development.json"

FRAME_VALUES = {
    "expression": {"neutral", "happy", "sad", "angry", "surprised"},
    "motion": {"idle", "wave", "nod", "shake_head", "point"},
    "gaze": {"left", "right", "user", "down"},
    "unsupported": {"unsupported"},
}
COMMITMENTS = {
    "requested",
    "mentioned",
    "hypothetical",
    "negated",
    "cancelled",
    "ambiguous",
    "unsupported",
}
FRAME_TO_CALL = {
    ("expression", value): {"name": "set_expression", "arguments": {"expression": value}}
    for value in FRAME_VALUES["expression"]
}
FRAME_TO_CALL.update(
    {
        ("motion", value): {"name": "play_motion", "arguments": {"motion": value}}
        for value in FRAME_VALUES["motion"]
    }
)
FRAME_TO_CALL.update(
    {
        ("gaze", value): {"name": "set_gaze", "arguments": {"target": value}}
        for value in FRAME_VALUES["gaze"]
    }
)


def call_key(call):
    return json.dumps(call, sort_keys=True, separators=(",", ":"))


class ActionIntentFrameV36DevelopmentDatasetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))

    def test_generated_dataset_is_deterministically_rebuildable(self):
        self.assertEqual(self.dataset, build())

    def test_all_retired_cases_are_annotated_once(self):
        self.assertEqual(len(self.dataset["cases"]), 36)
        self.assertEqual(
            {case["id"] for case in self.dataset["cases"]}, set(ANNOTATIONS)
        )
        self.assertEqual(
            Counter(case["family"] for case in self.dataset["cases"]),
            Counter({family: 6 for family in {
                "single_explicit_action",
                "multiple_compatible_actions",
                "no_action_conversation",
                "negated_action",
                "ambiguous_or_conflicting_action",
                "invalid_or_safety_blocked_action",
            }}),
        )

    def test_frames_have_valid_values_commitments_and_exact_gold_evidence(self):
        for case in self.dataset["cases"]:
            for frame in case["expected_frames"]:
                self.assertIn(frame["frame"], FRAME_VALUES)
                self.assertIn(frame["value"], FRAME_VALUES[frame["frame"]])
                self.assertIn(frame["commitment"], COMMITMENTS)
                self.assertTrue(frame["evidence_options"])
                for evidence in frame["evidence_options"]:
                    self.assertTrue(evidence)
                    self.assertIn(evidence, case["user_input"])

    def test_requested_frames_independently_reconstruct_expected_calls(self):
        for case in self.dataset["cases"]:
            compiled = [
                FRAME_TO_CALL[(frame["frame"], frame["value"])]
                for frame in case["expected_frames"]
                if frame["commitment"] == "requested"
            ]
            self.assertEqual(
                sorted(map(call_key, compiled)),
                sorted(map(call_key, case["expected_calls"])),
                case["id"],
            )

    def test_state_and_requested_commitment_are_coherent(self):
        for case in self.dataset["cases"]:
            requested = [
                frame
                for frame in case["expected_frames"]
                if frame["commitment"] == "requested"
            ]
            self.assertEqual(
                bool(requested),
                case["expected_state"] == "explicit_current_request",
                case["id"],
            )
            if case["expected_no_action"]:
                self.assertFalse(requested, case["id"])


if __name__ == "__main__":
    unittest.main()
