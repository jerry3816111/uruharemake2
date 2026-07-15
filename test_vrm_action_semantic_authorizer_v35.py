#!/usr/bin/env python3

import json
import unittest

from vrm_action_semantic_authorizer_v35 import (
    apply_semantic_authorization,
    parse_authorization_reply,
)


WAVE = {"name": "play_motion", "arguments": {"motion": "wave"}}
NOD = {"name": "play_motion", "arguments": {"motion": "nod"}}
INVALID = {"name": "send_email", "arguments": {"target": "x"}}


def reply(state, verdicts):
    return json.dumps({"utterance_state": state, "verdicts": verdicts}, ensure_ascii=False)


class VrmActionSemanticAuthorizerV35Test(unittest.TestCase):
    def test_colloquial_explicit_request_keeps_existing_call(self):
        text = "うんって感じで首を縦に動かして。"
        parsed = parse_authorization_reply(
            text,
            [NOD],
            reply(
                "explicit_current_request",
                [{
                    "index": 0,
                    "authorized": True,
                    "reason_code": "exact_supported_request",
                    "evidence": "首を縦に動かして",
                }],
            ),
        )
        result = apply_semantic_authorization(text, [NOD], parsed)
        self.assertTrue(parsed["parse_success"])
        self.assertEqual(result["accepted_calls"], [NOD])

    def test_discussion_blocks_proposed_call(self):
        text = "手を振る仕草って目立つかな。"
        parsed = parse_authorization_reply(
            text,
            [WAVE],
            reply(
                "not_a_request",
                [{
                    "index": 0,
                    "authorized": False,
                    "reason_code": "discussed_only",
                    "evidence": "手を振る仕草",
                }],
            ),
        )
        result = apply_semantic_authorization(text, [WAVE], parsed)
        self.assertEqual(result["accepted_calls"], [])

    def test_semantic_mismatch_cannot_replace_call(self):
        text = "前を指で示して。"
        parsed = parse_authorization_reply(
            text,
            [NOD],
            reply(
                "explicit_current_request",
                [{
                    "index": 0,
                    "authorized": False,
                    "reason_code": "semantic_mismatch",
                    "evidence": "指で示して",
                }],
            ),
        )
        result = apply_semantic_authorization(text, [NOD], parsed)
        self.assertEqual(result["accepted_calls"], [])
        self.assertEqual(len(result["blocked_calls"]), 1)

    def test_fabricated_evidence_fails_closed(self):
        text = "手を振って。"
        parsed = parse_authorization_reply(
            text,
            [WAVE],
            reply(
                "explicit_current_request",
                [{
                    "index": 0,
                    "authorized": True,
                    "reason_code": "exact_supported_request",
                    "evidence": "笑顔にして",
                }],
            ),
        )
        result = apply_semantic_authorization(text, [WAVE], parsed)
        self.assertTrue(parsed["parse_success"])
        self.assertEqual(result["accepted_calls"], [])
        self.assertIn(
            "authorized_call_lacks_exact_evidence",
            result["blocked_calls"][0]["reasons"],
        )

    def test_missing_verdict_fails_entire_parse(self):
        text = "手を振ってから、うなずいて。"
        parsed = parse_authorization_reply(
            text,
            [WAVE, NOD],
            reply(
                "explicit_current_request",
                [{
                    "index": 0,
                    "authorized": True,
                    "reason_code": "exact_supported_request",
                    "evidence": "手を振って",
                }],
            ),
        )
        result = apply_semantic_authorization(text, [WAVE, NOD], parsed)
        self.assertFalse(parsed["parse_success"])
        self.assertEqual(result["accepted_calls"], [])

    def test_non_allowlisted_call_is_never_accepted(self):
        text = "メールを送って。"
        parsed = parse_authorization_reply(
            text,
            [INVALID],
            reply(
                "explicit_current_request",
                [{
                    "index": 0,
                    "authorized": True,
                    "reason_code": "exact_supported_request",
                    "evidence": "メールを送って",
                }],
            ),
        )
        result = apply_semantic_authorization(text, [INVALID], parsed)
        self.assertEqual(result["accepted_calls"], [])
        self.assertIn(
            "invalid_or_non_allowlisted_call",
            result["blocked_calls"][0]["reasons"],
        )


if __name__ == "__main__":
    unittest.main()
