#!/usr/bin/env python3

import json
import unittest

from action_intent_frame_v36 import (
    compile_action_intent_frame,
    parse_action_intent_frame,
)


def reply(state, frames):
    return json.dumps(
        {"utterance_state": state, "frames": frames}, ensure_ascii=False
    )


def frame(frame_name, value, commitment, evidence):
    return {
        "frame": frame_name,
        "value": value,
        "commitment": commitment,
        "evidence": evidence,
    }


class ActionIntentFrameV36Test(unittest.TestCase):
    def test_multiple_requested_frames_compile_without_prior_proposals(self):
        text = "笑った顔でこちらを見て。"
        parsed = parse_action_intent_frame(
            text,
            reply(
                "explicit_current_request",
                [
                    frame("expression", "happy", "requested", "笑った顔で"),
                    frame("gaze", "user", "requested", "こちらを見て"),
                ],
            ),
        )
        compiled = compile_action_intent_frame(parsed)
        self.assertTrue(parsed["parse_success"])
        self.assertEqual(
            compiled["accepted_calls"],
            [
                {"name": "set_expression", "arguments": {"expression": "happy"}},
                {"name": "set_gaze", "arguments": {"target": "user"}},
            ],
        )

    def test_negation_scope_keeps_only_positive_correction(self):
        text = "うなずかないで、首を横に振って。"
        parsed = parse_action_intent_frame(
            text,
            reply(
                "explicit_current_request",
                [
                    frame("motion", "nod", "negated", "うなずかないで"),
                    frame("motion", "shake_head", "requested", "首を横に振って"),
                ],
            ),
        )
        compiled = compile_action_intent_frame(parsed)
        self.assertEqual(
            compiled["accepted_calls"],
            [{"name": "play_motion", "arguments": {"motion": "shake_head"}}],
        )

    def test_discussed_action_remains_observable_but_never_compiles(self):
        text = "手を振る仕草って目立つかな。"
        parsed = parse_action_intent_frame(
            text,
            reply(
                "no_current_action",
                [frame("motion", "wave", "mentioned", "手を振る仕草")],
            ),
        )
        compiled = compile_action_intent_frame(parsed)
        self.assertTrue(parsed["parse_success"])
        self.assertEqual(compiled["accepted_calls"], [])
        self.assertEqual(len(compiled["blocked_frames"]), 1)

    def test_late_cancellation_never_compiles(self):
        text = "うなずいて。いや、今の頼みは取り消し。"
        parsed = parse_action_intent_frame(
            text,
            reply(
                "ambiguous_or_cancelled",
                [
                    frame(
                        "motion",
                        "nod",
                        "cancelled",
                        "うなずいて。いや、今の頼みは取り消し",
                    )
                ],
            ),
        )
        self.assertEqual(compile_action_intent_frame(parsed)["accepted_calls"], [])

    def test_unsupported_frame_cannot_become_arbitrary_function(self):
        text = "メールを送って。"
        parsed = parse_action_intent_frame(
            text,
            reply(
                "unsupported_or_unsafe",
                [
                    frame(
                        "unsupported",
                        "unsupported",
                        "unsupported",
                        "メールを送って",
                    )
                ],
            ),
        )
        compiled = compile_action_intent_frame(parsed)
        self.assertTrue(parsed["parse_success"])
        self.assertEqual(compiled["accepted_calls"], [])

    def test_fabricated_evidence_fails_closed_for_entire_utterance(self):
        text = "手を振って。"
        parsed = parse_action_intent_frame(
            text,
            reply(
                "explicit_current_request",
                [frame("motion", "wave", "requested", "首を縦に動かして")],
            ),
        )
        compiled = compile_action_intent_frame(parsed)
        self.assertFalse(parsed["parse_success"])
        self.assertTrue(compiled["fail_closed"])
        self.assertEqual(compiled["accepted_calls"], [])

    def test_conflicting_commitments_for_same_target_fail_closed(self):
        text = "手を振って、いや振らないで。"
        parsed = parse_action_intent_frame(
            text,
            reply(
                "no_current_action",
                [
                    frame("motion", "wave", "requested", "手を振って"),
                    frame("motion", "wave", "cancelled", "振らないで"),
                ],
            ),
        )
        self.assertFalse(parsed["parse_success"])
        self.assertEqual(compile_action_intent_frame(parsed)["accepted_calls"], [])

    def test_nonexplicit_state_with_requested_frame_is_rejected(self):
        text = "もし笑顔だったら話しやすいかな。"
        parsed = parse_action_intent_frame(
            text,
            reply(
                "no_current_action",
                [frame("expression", "happy", "requested", "笑顔だったら")],
            ),
        )
        self.assertFalse(parsed["parse_success"])


if __name__ == "__main__":
    unittest.main()
