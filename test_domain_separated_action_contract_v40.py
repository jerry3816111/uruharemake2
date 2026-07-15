#!/usr/bin/env python3

import json
import unittest

from domain_separated_action_contract_v40 import (
    compile_v40,
    load_v39_anchor_ontology,
    parse_domain_separated_frames,
)


def _payload(**overrides):
    payload = {
        "expression_frames": [],
        "motion_frames": [],
        "gaze_frames": [],
        "unsupported_frames": [],
    }
    payload.update(overrides)
    return json.dumps(payload, ensure_ascii=False)


class DomainSeparatedActionContractV40Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ontology = load_v39_anchor_ontology()

    def test_supported_array_supplies_domain_and_compiles(self):
        text = "挨拶代わりに手を振って。"
        raw = _payload(
            motion_frames=[
                {"value": "wave", "commitment": "requested", "evidence": "手を振って"}
            ]
        )
        parsed = parse_domain_separated_frames(text, raw)
        self.assertTrue(parsed["trace_wellformed"])
        self.assertEqual(parsed["frames"][0]["domain"], "motion")
        self.assertEqual(
            compile_v40(text, parsed, self.ontology)["accepted_calls"],
            [{"name": "play_motion", "arguments": {"motion": "wave"}}],
        )

    def test_generic_discussion_uses_empty_arrays(self):
        parsed = parse_domain_separated_frames(
            "今日は表情について話したい。", _payload()
        )
        self.assertTrue(parsed["trace_wellformed"])
        self.assertEqual(parsed["frames"], [])

    def test_wrong_domain_value_is_isolated(self):
        raw = _payload(
            expression_frames=[
                {"value": "wave", "commitment": "mentioned", "evidence": "表情"}
            ]
        )
        parsed = parse_domain_separated_frames("表情の話。", raw)
        self.assertTrue(parsed["execution_parse_success"])
        self.assertFalse(parsed["trace_wellformed"])
        self.assertEqual(parsed["warnings"][0]["reasons"], ["invalid_domain_value"])
        self.assertEqual(parsed["frames"], [])

    def test_unsupported_frame_normalizes_without_execution(self):
        text = "カメラを一周回して。"
        raw = _payload(
            unsupported_frames=[
                {"domain": "other", "commitment": "requested", "evidence": "カメラを一周回して"}
            ]
        )
        parsed = parse_domain_separated_frames(text, raw)
        self.assertEqual(parsed["frames"][0]["value"], "unsupported")
        self.assertEqual(compile_v40(text, parsed, self.ontology)["accepted_calls"], [])

    def test_non_exact_evidence_is_warning(self):
        raw = _payload(
            gaze_frames=[
                {"value": "left", "commitment": "requested", "evidence": "左を見て"}
            ]
        )
        parsed = parse_domain_separated_frames("左へ視線を向けて。", raw)
        self.assertTrue(parsed["execution_parse_success"])
        self.assertFalse(parsed["trace_wellformed"])
        self.assertEqual(
            parsed["warnings"][0]["reasons"],
            ["evidence_not_exact_input_substring"],
        )

    def test_duplicate_target_remains_observable_warning(self):
        text = "うなずかないで、やっぱりうなずいて。"
        raw = _payload(
            motion_frames=[
                {"value": "nod", "commitment": "negated", "evidence": "うなずかないで"},
                {"value": "nod", "commitment": "requested", "evidence": "うなずいて"},
            ]
        )
        parsed = parse_domain_separated_frames(text, raw)
        self.assertFalse(parsed["trace_wellformed"])
        self.assertEqual(parsed["warnings"][0]["reasons"], ["duplicate_frame_target"])

    def test_missing_root_array_is_fatal(self):
        payload = json.loads(_payload())
        del payload["gaze_frames"]
        parsed = parse_domain_separated_frames("何もしない。", json.dumps(payload))
        self.assertFalse(parsed["execution_parse_success"])
        self.assertIn("root_fields_mismatch", parsed["errors"])


if __name__ == "__main__":
    unittest.main()
