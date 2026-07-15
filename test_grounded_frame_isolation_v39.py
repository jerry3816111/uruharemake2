#!/usr/bin/env python3

import json
import unittest

from grounded_frame_isolation_v39 import (
    compile_v39,
    load_v39_anchor_ontology,
    parse_frames_with_isolation,
)


class GroundedFrameIsolationV39Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ontology = load_v39_anchor_ontology()

    def test_colloquial_gesture_anchor_accepts_requested_nod(self):
        text = "うんって感じで首を縦に動かして。"
        raw = json.dumps(
            {
                "frames": [
                    {
                        "domain": "motion",
                        "value": "nod",
                        "commitment": "requested",
                        "evidence": "うんって感じで",
                    }
                ]
            },
            ensure_ascii=False,
        )
        parsed = parse_frames_with_isolation(text, raw)
        result = compile_v39(text, parsed, self.ontology)
        self.assertEqual(
            result["accepted_calls"],
            [{"name": "play_motion", "arguments": {"motion": "nod"}}],
        )

    def test_ordinary_verbal_acknowledgement_does_not_ground_nod(self):
        text = "うん、そうだね。"
        raw = json.dumps(
            {
                "frames": [
                    {
                        "domain": "motion",
                        "value": "nod",
                        "commitment": "requested",
                        "evidence": "うん",
                    }
                ]
            },
            ensure_ascii=False,
        )
        parsed = parse_frames_with_isolation(text, raw)
        self.assertEqual(compile_v39(text, parsed, self.ontology)["accepted_calls"], [])

    def test_invalid_individual_frame_is_warning_not_root_failure(self):
        text = "今日は表情の変化について話したい。"
        raw = json.dumps(
            {
                "frames": [
                    {
                        "domain": "expression",
                        "value": "mentioned",
                        "commitment": "mentioned",
                        "evidence": "今日は表情の変化について",
                    }
                ]
            },
            ensure_ascii=False,
        )
        parsed = parse_frames_with_isolation(text, raw)
        self.assertTrue(parsed["execution_parse_success"])
        self.assertFalse(parsed["trace_wellformed"])
        self.assertEqual(parsed["frames"], [])
        self.assertEqual(parsed["warnings"][0]["reasons"], ["invalid_domain_value"])

    def test_valid_grounded_frame_survives_invalid_neighbor(self):
        text = "手を振って、それから謎の操作もして。"
        raw = json.dumps(
            {
                "frames": [
                    {
                        "domain": "motion",
                        "value": "wave",
                        "commitment": "requested",
                        "evidence": "手を振って",
                    },
                    {
                        "domain": "invalid",
                        "value": "anything",
                        "commitment": "requested",
                        "evidence": "謎の操作",
                    },
                ]
            },
            ensure_ascii=False,
        )
        parsed = parse_frames_with_isolation(text, raw)
        result = compile_v39(text, parsed, self.ontology)
        self.assertTrue(parsed["execution_parse_success"])
        self.assertFalse(parsed["trace_wellformed"])
        self.assertEqual(
            result["accepted_calls"],
            [{"name": "play_motion", "arguments": {"motion": "wave"}}],
        )

    def test_root_error_remains_fatal(self):
        parsed = parse_frames_with_isolation("手を振って。", "not-json")
        self.assertFalse(parsed["execution_parse_success"])
        self.assertFalse(parsed["trace_wellformed"])


if __name__ == "__main__":
    unittest.main()
