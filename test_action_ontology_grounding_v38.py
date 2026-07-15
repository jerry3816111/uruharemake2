#!/usr/bin/env python3

import json
import unittest

from action_ontology_grounding_v38 import (
    compile_anchor_grounded,
    load_anchor_ontology,
    parse_action_frames_with_local_warnings,
)
from action_selective_deliberation_v37 import parse_action_frames


def _parse(text, frames, local=True):
    raw = json.dumps({"frames": frames}, ensure_ascii=False)
    return (
        parse_action_frames_with_local_warnings(text, raw)
        if local
        else parse_action_frames(text, raw)
    )


class ActionOntologyGroundingV38Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ontology = load_anchor_ontology()

    def test_conversation_proposal_cannot_ground_idle_motion(self):
        text = "少し疲れたから、静かな曲の話をしよう。"
        parsed = _parse(
            text,
            [
                {
                    "domain": "motion",
                    "value": "idle",
                    "commitment": "requested",
                    "evidence": "静かな曲の話をしよう。",
                }
            ],
        )
        result = compile_anchor_grounded(text, parsed, self.ontology)
        self.assertEqual(result["accepted_calls"], [])
        self.assertIn("target_not_grounded_in_evidence", result["blocked_frames"][0]["reasons"])

    def test_positive_neutral_anchor_survives_oversized_evidence(self):
        text = "怒った顔じゃなく、普通の表情へ戻して。"
        parsed = _parse(
            text,
            [
                {
                    "domain": "expression",
                    "value": "neutral",
                    "commitment": "requested",
                    "evidence": "怒った顔じゃなく、普通の表情へ",
                }
            ],
        )
        result = compile_anchor_grounded(text, parsed, self.ontology)
        self.assertEqual(
            result["accepted_calls"],
            [{"name": "set_expression", "arguments": {"expression": "neutral"}}],
        )
        self.assertEqual(result["accepted_frames"][0]["matched_anchor"]["text"], "普通の表情")

    def test_wrong_neutral_value_has_no_anchor_in_negated_happy_request(self):
        text = "笑顔には変えないで。"
        parsed = _parse(
            text,
            [
                {
                    "domain": "expression",
                    "value": "neutral",
                    "commitment": "requested",
                    "evidence": "笑顔には変えないで",
                }
            ],
        )
        result = compile_anchor_grounded(text, parsed, self.ontology)
        self.assertEqual(result["accepted_calls"], [])

    def test_duplicate_target_is_warning_and_grounded_positive_action_survives(self):
        text = "うなずかないで、首を横に振って。"
        frames = [
            {
                "domain": "motion",
                "value": "shake_head",
                "commitment": "negated",
                "evidence": "うなずかないで",
            },
            {
                "domain": "motion",
                "value": "shake_head",
                "commitment": "requested",
                "evidence": "首を横に振って。",
            },
        ]
        strict = _parse(text, frames, local=False)
        local = _parse(text, frames, local=True)
        self.assertFalse(strict["parse_success"])
        self.assertTrue(local["parse_success"])
        self.assertEqual(local["warnings"], ["duplicate_frame_target"])
        result = compile_anchor_grounded(text, local, self.ontology)
        self.assertEqual(
            result["accepted_calls"],
            [{"name": "play_motion", "arguments": {"motion": "shake_head"}}],
        )

    def test_target_specific_anchor_rejects_right_for_interlocutor_gaze(self):
        text = "下は見ず、こっちだけ見て。"
        parsed = _parse(
            text,
            [
                {
                    "domain": "gaze",
                    "value": "right",
                    "commitment": "requested",
                    "evidence": "こっちだけ見て",
                }
            ],
        )
        self.assertEqual(
            compile_anchor_grounded(text, parsed, self.ontology)["accepted_calls"],
            [],
        )

    def test_unsupported_never_executes(self):
        text = "その場でしゃがんで。"
        parsed = _parse(
            text,
            [
                {
                    "domain": "motion",
                    "value": "unsupported",
                    "commitment": "requested",
                    "evidence": "しゃがんで",
                }
            ],
        )
        result = compile_anchor_grounded(text, parsed, self.ontology)
        self.assertEqual(result["accepted_calls"], [])
        self.assertEqual(result["ungrounded_execution_count"], 0)


if __name__ == "__main__":
    unittest.main()
