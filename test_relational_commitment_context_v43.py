#!/usr/bin/env python3

import json
import unittest

from relational_commitment_context_v43 import (
    assemble_commitment_only_case,
    parse_commitment_only,
    select_evidence_anchor,
)


def _anchor(text, source, occurrence=0):
    start = -1
    offset = 0
    for _ in range(occurrence + 1):
        start = source.index(text, offset)
        offset = start + len(text)
    return {
        "start": start,
        "end": start + len(text),
        "text": text,
        "pattern": text,
    }


class RelationalCommitmentContextV43Tests(unittest.TestCase):
    def test_parser_accepts_only_one_valid_commitment_field(self):
        valid = parse_commitment_only(json.dumps({"commitment": "requested"}))
        extra = parse_commitment_only(
            json.dumps({"commitment": "requested", "evidence_index": 0})
        )
        invalid = parse_commitment_only(json.dumps({"commitment": "execute"}))
        nested = parse_commitment_only(
            json.dumps({"commitment": {"value": "requested"}})
        )
        self.assertTrue(valid["parse_success"])
        self.assertEqual(valid["commitment"], "requested")
        self.assertIn("root_fields_mismatch", extra["errors"])
        self.assertIn("invalid_commitment", invalid["errors"])
        self.assertIn("invalid_commitment", nested["errors"])

    def test_requested_evidence_prefers_latest_non_negated_anchor(self):
        text = "手を振らないで。でも最後に手を振って。"
        candidate = {
            "anchors": [
                _anchor("手を振", text, 0),
                _anchor("手を振", text, 1),
            ]
        }
        selected = select_evidence_anchor(text, candidate, "requested")
        self.assertEqual(selected["start"], text.rindex("手を振"))
        self.assertEqual(selected["selection_rule"], "preferred_requested")

    def test_negated_and_cancelled_evidence_use_their_local_scope(self):
        negated_text = "手を振らないで。でも最後に手を振って。"
        negated_candidate = {
            "anchors": [
                _anchor("手を振", negated_text, 0),
                _anchor("手を振", negated_text, 1),
            ]
        }
        negated = select_evidence_anchor(
            negated_text, negated_candidate, "negated"
        )
        self.assertEqual(negated["start"], negated_text.index("手を振"))
        self.assertIn(
            "anchor_inside_negated_clause", negated["selection_scope_reasons"]
        )

        cancelled_text = "うなずいて。いや、今の頼みは取り消し。"
        cancelled_candidate = {
            "anchors": [_anchor("うなず", cancelled_text)]
        }
        cancelled = select_evidence_anchor(
            cancelled_text, cancelled_candidate, "cancelled"
        )
        self.assertIn(
            "grounded_action_cancelled_later",
            cancelled["selection_scope_reasons"],
        )

    def test_one_invalid_target_fails_closed_for_the_whole_case(self):
        text = "手を振って、こちらを見て。"
        candidates = [
            {
                "target_id": "motion.wave",
                "domain": "motion",
                "value": "wave",
                "anchors": [_anchor("手を振", text)],
            },
            {
                "target_id": "gaze.user",
                "domain": "gaze",
                "value": "user",
                "anchors": [_anchor("こちらを見", text)],
            },
        ]
        assembled = assemble_commitment_only_case(
            text,
            candidates,
            {
                "motion.wave": {
                    "parse_success": True,
                    "commitment": "requested",
                },
                "gaze.user": {
                    "parse_success": False,
                    "commitment": None,
                    "errors": ["invalid_json"],
                },
            },
        )
        self.assertFalse(assembled["parse_success"])
        self.assertEqual(assembled["frames"], [])


if __name__ == "__main__":
    unittest.main()
