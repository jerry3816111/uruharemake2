#!/usr/bin/env python3

import json
import re
import unittest

from grounded_commitment_classifier_v42 import (
    assemble_supported_case,
    frame_from_judgment,
    ground_supported_targets,
    parse_commitment_judgment,
)


class GroundedCommitmentClassifierV42Tests(unittest.TestCase):
    def test_grounding_returns_exact_numbered_anchor_candidates(self):
        ontology = {("motion", "wave"): [re.compile("手を振")]}
        candidates = ground_supported_targets("一度手を振って。", ontology)
        self.assertEqual(candidates[0]["target_id"], "motion.wave")
        self.assertEqual(candidates[0]["anchors"][0]["text"], "手を振")

    def test_parse_accepts_narrow_contract(self):
        parsed = parse_commitment_judgment(
            json.dumps({"commitment": "requested", "evidence_index": 0}), 1
        )
        self.assertTrue(parsed["parse_success"])
        self.assertEqual(parsed["commitment"], "requested")

    def test_parse_rejects_boolean_or_out_of_range_index(self):
        boolean = parse_commitment_judgment(
            json.dumps({"commitment": "requested", "evidence_index": True}), 1
        )
        outside = parse_commitment_judgment(
            json.dumps({"commitment": "requested", "evidence_index": 2}), 1
        )
        self.assertIn("evidence_index_not_integer", boolean["errors"])
        self.assertIn("evidence_index_out_of_range", outside["errors"])

    def test_frame_uses_existing_anchor_without_model_copy(self):
        candidate = {
            "domain": "motion",
            "value": "wave",
            "anchors": [{"text": "手を振", "start": 2, "end": 5}],
        }
        judgment = {"parse_success": True, "commitment": "negated", "evidence_index": 0}
        frame = frame_from_judgment(candidate, judgment)
        self.assertEqual(frame["evidence"], "手を振")
        self.assertEqual(frame["commitment"], "negated")

    def test_one_invalid_target_fails_closed_for_whole_case(self):
        candidates = [
            {
                "target_id": "motion.wave",
                "domain": "motion",
                "value": "wave",
                "anchors": [{"text": "手を振"}],
            },
            {
                "target_id": "gaze.user",
                "domain": "gaze",
                "value": "user",
                "anchors": [{"text": "こちらを見"}],
            },
        ]
        assembled = assemble_supported_case(
            candidates,
            {
                "motion.wave": {
                    "parse_success": True,
                    "commitment": "requested",
                    "evidence_index": 0,
                },
                "gaze.user": {"parse_success": False, "errors": ["invalid_json"]},
            },
        )
        self.assertFalse(assembled["parse_success"])
        self.assertEqual(assembled["frames"], [])


if __name__ == "__main__":
    unittest.main()
