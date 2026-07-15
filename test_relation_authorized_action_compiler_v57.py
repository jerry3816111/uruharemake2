#!/usr/bin/env python3

import unittest

from relation_authorized_action_compiler_v57 import compile_relation_authorized_v57


def _frame(domain, value, evidence, commitment="requested"):
    return {
        "domain": domain,
        "value": value,
        "commitment": commitment,
        "evidence": evidence,
        "evidence_valid": True,
    }


def _state(
    target_id,
    *,
    commitment="requested",
    resolved=True,
    rule="relation_bound_local_directive",
    relation_types=("local_directive",),
    clause_text="",
    sentence_text="",
):
    focus = []
    if clause_text or sentence_text:
        focus.append(
            {
                "sentence_index": 0,
                "clause_index": 0,
                "clause_text": clause_text,
                "sentence_text": sentence_text or clause_text,
            }
        )
    return {
        "resolved": resolved,
        "commitment": commitment if resolved else None,
        "resolution_rule": rule,
        "event_map": {"focus_occurrences": focus},
        "v56_relation_graph": {
            "focus_target_id": target_id,
            "relations": [
                {"type": name, "source": "test", "target": "focus_event"}
                for name in relation_types
            ],
            "relation_types": list(relation_types),
        },
    }


def _parsed(*frames):
    return {"parse_success": True, "frames": list(frames)}


class RelationAuthorizedActionCompilerV57Tests(unittest.TestCase):
    def test_positive_idle_is_not_blocked_by_surface_negation(self):
        text = "今は動かないでいてください。"
        result = compile_relation_authorized_v57(
            text,
            _parsed(_frame("motion", "idle", "動かない")),
            {"motion.idle": _state("motion.idle")},
        )
        self.assertEqual(
            result["accepted_calls"],
            [{"name": "play_motion", "arguments": {"motion": "idle"}}],
        )
        self.assertEqual(result["execution_plan"][0]["step"], 1)

    def test_blocking_relation_wins_over_requested_label(self):
        text = "台本の『笑って』は実行禁止です。"
        result = compile_relation_authorized_v57(
            text,
            _parsed(_frame("expression", "happy", "笑って")),
            {
                "expression.happy": _state(
                    "expression.happy",
                    relation_types=("local_directive", "execution_prohibition"),
                )
            },
        )
        self.assertEqual(result["accepted_calls"], [])
        self.assertIn(
            "blocking_relation:execution_prohibition",
            result["blocked_frames"][0]["reasons"],
        )

    def test_finite_description_is_not_authorized_by_later_request(self):
        text = "先ほど右を向きましたが、今は笑ってほしい。"
        result = compile_relation_authorized_v57(
            text,
            _parsed(_frame("gaze", "right", "右を向")),
            {
                "gaze.right": _state(
                    "gaze.right",
                    rule="explicit_request_force",
                    relation_types=(),
                    clause_text="先ほど右を向きましたが、",
                    sentence_text=text,
                )
            },
        )
        self.assertEqual(result["accepted_calls"], [])
        self.assertIn(
            "requested_state_lacks_event_authorization",
            result["blocked_frames"][0]["reasons"],
        )

    def test_nonfinite_coordination_bridge_preserves_valid_request(self):
        text = "私を見て、私がするようにしなさい。"
        result = compile_relation_authorized_v57(
            text,
            _parsed(_frame("gaze", "user", "私を見")),
            {
                "gaze.user": _state(
                    "gaze.user",
                    rule="explicit_request_force",
                    relation_types=(),
                    clause_text="私を見て、",
                    sentence_text=text,
                )
            },
        )
        self.assertEqual(len(result["accepted_calls"]), 1)
        self.assertEqual(
            result["execution_plan"][0]["authorization"]["type"],
            "legacy_coordination_bridge",
        )

    def test_same_domain_directives_become_an_ordered_plan(self):
        text = "通りを横断する前に左右を見なさい。"
        result = compile_relation_authorized_v57(
            text,
            _parsed(
                _frame("gaze", "left", "左右を見"),
                _frame("gaze", "right", "右を見"),
            ),
            {
                "gaze.left": _state("gaze.left"),
                "gaze.right": _state("gaze.right"),
            },
        )
        self.assertEqual(
            [step["target_id"] for step in result["execution_plan"]],
            ["gaze.left", "gaze.right"],
        )
        self.assertEqual(
            result["same_domain_sequences"],
            [
                {
                    "domain": "gaze",
                    "target_ids": ["gaze.left", "gaze.right"],
                    "order_rule": "grounded_mention_order",
                }
            ],
        )

    def test_unresolved_model_only_request_fails_closed(self):
        text = "左を向いて。"
        result = compile_relation_authorized_v57(
            text,
            _parsed(_frame("gaze", "left", "左を向")),
            {
                "gaze.left": _state(
                    "gaze.left", resolved=False, relation_types=()
                )
            },
        )
        self.assertEqual(result["accepted_calls"], [])
        self.assertIn(
            "unresolved_model_only_request",
            result["blocked_frames"][0]["reasons"],
        )

    def test_exact_evidence_and_grounded_anchor_remain_required(self):
        result = compile_relation_authorized_v57(
            "右を向いて。",
            _parsed(_frame("gaze", "right", "存在しない根拠")),
            {"gaze.right": _state("gaze.right")},
        )
        self.assertEqual(result["accepted_calls"], [])
        reasons = result["blocked_frames"][0]["reasons"]
        self.assertIn("frame_evidence_not_exact_substring", reasons)
        self.assertIn("target_not_grounded_in_evidence", reasons)

    def test_nonrequested_frame_never_executes(self):
        result = compile_relation_authorized_v57(
            "彼は右を向いた。",
            _parsed(_frame("gaze", "right", "右を向", "mentioned")),
            {
                "gaze.right": _state(
                    "gaze.right", commitment="mentioned", relation_types=()
                )
            },
        )
        self.assertEqual(result["accepted_calls"], [])
        self.assertIn("frame_not_requested", result["blocked_frames"][0]["reasons"])


if __name__ == "__main__":
    unittest.main()
