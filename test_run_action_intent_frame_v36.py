#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path

from run_action_intent_frame_v36 import OUTPUT_SCHEMA, SYSTEM_PROMPT


ROOT = Path(__file__).resolve().parent
FREEZE_PATH = ROOT / "configs" / "action_intent_frame_v36_dataset_freeze.json"


class RunActionIntentFrameV36Test(unittest.TestCase):
    def test_prompt_freezes_state_frame_commitment_and_evidence(self):
        for field in ("utterance_state", "frames", "frame", "value", "commitment", "evidence"):
            self.assertIn(field, SYSTEM_PROMPT)
        for commitment in (
            "requested",
            "mentioned",
            "hypothetical",
            "negated",
            "cancelled",
            "ambiguous",
            "unsupported",
        ):
            self.assertIn(commitment, SYSTEM_PROMPT)

    def test_prompt_contains_no_retired_case_phrase(self):
        for phrase in (
            "首を縦に動かして",
            "にこっとして",
            "目線をこっちにちょうだい",
            "うなずかないで、首を横に振って",
            "今の頼みは取り消し",
        ):
            self.assertNotIn(phrase, SYSTEM_PROMPT)

    def test_output_schema_requires_only_frozen_fields(self):
        self.assertEqual(OUTPUT_SCHEMA["required"], ["utterance_state", "frames"])
        frame_schema = OUTPUT_SCHEMA["properties"]["frames"]["items"]
        self.assertEqual(
            frame_schema["required"],
            ["frame", "value", "commitment", "evidence"],
        )
        self.assertFalse(frame_schema["additionalProperties"])

    def test_dataset_freeze_hash_matches_committed_dataset(self):
        freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
        dataset = ROOT / freeze["dataset"]
        digest = hashlib.sha256(dataset.read_bytes()).hexdigest()
        self.assertEqual(digest, freeze["dataset_sha256"])
        self.assertFalse(freeze["model_outputs_observed_before_freeze"])


if __name__ == "__main__":
    unittest.main()
