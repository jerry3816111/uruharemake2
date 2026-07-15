#!/usr/bin/env python3

import json
import unittest

from action_selective_deliberation_v37 import (
    apply_policy,
    assess_deliberation_risk,
    compile_consensus,
    compile_judgment,
    derive_utterance_state,
    parse_action_frames,
)


def _judgment(text, payload):
    parsed = parse_action_frames(text, json.dumps(payload, ensure_ascii=False))
    return {"parsed": parsed, "compilation": compile_judgment(text, parsed)}


class ActionSelectiveDeliberationV37Tests(unittest.TestCase):
    def test_unsupported_is_local_attribute_and_state_is_derived(self):
        text = "その場でしゃがんで。"
        parsed = parse_action_frames(
            text,
            json.dumps(
                {
                    "frames": [
                        {
                            "domain": "motion",
                            "value": "unsupported",
                            "commitment": "requested",
                            "evidence": "しゃがんで",
                        }
                    ]
                },
                ensure_ascii=False,
            ),
        )
        self.assertTrue(parsed["parse_success"])
        self.assertEqual(parsed["derived_state"], "unsupported_or_unsafe")
        self.assertEqual(compile_judgment(text, parsed)["accepted_calls"], [])

    def test_model_cannot_supply_duplicate_global_state(self):
        parsed = parse_action_frames("手を振って。", '{"frames":[],"utterance_state":"explicit_current_request"}')
        self.assertFalse(parsed["parse_success"])
        self.assertIn("root_fields_mismatch", parsed["errors"])

    def test_negated_clause_blocks_invented_neutral_request(self):
        text = "笑顔には変えないで。"
        row = _judgment(
            text,
            {
                "frames": [
                    {
                        "domain": "expression",
                        "value": "neutral",
                        "commitment": "requested",
                        "evidence": "笑顔には変えないで",
                    }
                ]
            },
        )
        self.assertEqual(row["compilation"]["accepted_calls"], [])
        self.assertTrue(row["compilation"]["scope_guard_blocked"])

    def test_positive_correction_after_negation_remains_eligible(self):
        text = "怒った顔じゃなく、普通の表情へ戻して。"
        row = _judgment(
            text,
            {
                "frames": [
                    {
                        "domain": "expression",
                        "value": "angry",
                        "commitment": "negated",
                        "evidence": "怒った顔じゃなく",
                    },
                    {
                        "domain": "expression",
                        "value": "neutral",
                        "commitment": "requested",
                        "evidence": "普通の表情へ戻して",
                    },
                ]
            },
        )
        self.assertEqual(
            row["compilation"]["accepted_calls"],
            [{"name": "set_expression", "arguments": {"expression": "neutral"}}],
        )

    def test_later_referential_cancellation_blocks_prior_request(self):
        text = "うなずいて。いや、今の頼みは取り消し。"
        row = _judgment(
            text,
            {
                "frames": [
                    {
                        "domain": "motion",
                        "value": "nod",
                        "commitment": "requested",
                        "evidence": "うなずいて",
                    }
                ]
            },
        )
        self.assertEqual(row["compilation"]["accepted_calls"], [])

    def test_risk_router_distinguishes_simple_and_conflicted_requests(self):
        simple = _judgment(
            "一度手を振って。",
            {
                "frames": [
                    {
                        "domain": "motion",
                        "value": "wave",
                        "commitment": "requested",
                        "evidence": "手を振って",
                    }
                ]
            },
        )
        risky = _judgment(
            "手を振らないで。",
            {
                "frames": [
                    {
                        "domain": "motion",
                        "value": "wave",
                        "commitment": "negated",
                        "evidence": "手を振らないで",
                    }
                ]
            },
        )
        self.assertFalse(assess_deliberation_risk("一度手を振って。", **simple)["escalate"])
        self.assertTrue(assess_deliberation_risk("手を振らないで。", **risky)["escalate"])

    def test_consensus_uses_two_matching_grounded_calls(self):
        text = "下は見ず、こっちだけ見て。"
        user = {
            "frames": [
                {
                    "domain": "gaze",
                    "value": "user",
                    "commitment": "requested",
                    "evidence": "こっちだけ見て",
                }
            ]
        }
        right = {
            "frames": [
                {
                    "domain": "gaze",
                    "value": "right",
                    "commitment": "requested",
                    "evidence": "こっちだけ見て",
                }
            ]
        }
        result = compile_consensus([_judgment(text, user), _judgment(text, right), _judgment(text, user)])
        self.assertEqual(
            result["accepted_calls"],
            [{"name": "set_gaze", "arguments": {"target": "user"}}],
        )

    def test_consensus_fails_closed_with_fewer_than_two_valid_judgments(self):
        text = "手を振って。"
        valid = _judgment(
            text,
            {
                "frames": [
                    {
                        "domain": "motion",
                        "value": "wave",
                        "commitment": "requested",
                        "evidence": "手を振って",
                    }
                ]
            },
        )
        invalid = _judgment(text, {"frames": "not-an-array"})
        result = compile_consensus([valid, invalid, invalid])
        self.assertTrue(result["fail_closed"])
        self.assertEqual(result["accepted_calls"], [])

    def test_selective_policy_spends_one_or_three_passes(self):
        simple_text = "一度手を振って。"
        simple = _judgment(
            simple_text,
            {
                "frames": [
                    {
                        "domain": "motion",
                        "value": "wave",
                        "commitment": "requested",
                        "evidence": "手を振って",
                    }
                ]
            },
        )
        simple_result = apply_policy(
            "selective_three_pass_v37_candidate",
            simple_text,
            [simple, simple, simple],
        )
        self.assertEqual(simple_result["passes_used"], 1)

        risky_text = "今は手を振らないで。"
        risky = _judgment(
            risky_text,
            {
                "frames": [
                    {
                        "domain": "motion",
                        "value": "wave",
                        "commitment": "negated",
                        "evidence": "手を振らないで",
                    }
                ]
            },
        )
        risky_result = apply_policy(
            "selective_three_pass_v37_candidate",
            risky_text,
            [risky, risky, risky],
        )
        self.assertEqual(risky_result["passes_used"], 3)
        self.assertTrue(risky_result["escalated"])

    def test_derived_state_prefers_supported_current_request(self):
        frames = [
            {"domain": "motion", "value": "unsupported", "commitment": "requested"},
            {"domain": "gaze", "value": "user", "commitment": "requested"},
        ]
        self.assertEqual(derive_utterance_state(frames), "explicit_current_request")


if __name__ == "__main__":
    unittest.main()
