#!/usr/bin/env python3

import json
import unittest
from unittest.mock import patch

import run_domain_separated_action_contract_v40 as runner


def _contains_key(value, key):
    if isinstance(value, dict):
        return key in value or any(_contains_key(child, key) for child in value.values())
    if isinstance(value, list):
        return any(_contains_key(child, key) for child in value)
    return False


class RunDomainSeparatedActionContractV40Tests(unittest.TestCase):
    def test_schema_uses_four_basic_arrays_without_conditionals(self):
        self.assertEqual(
            set(runner.OUTPUT_SCHEMA["properties"]),
            {"expression_frames", "motion_frames", "gaze_frames", "unsupported_frames"},
        )
        self.assertFalse(_contains_key(runner.OUTPUT_SCHEMA, "oneOf"))
        self.assertFalse(_contains_key(runner.OUTPUT_SCHEMA, "const"))
        expression = runner.OUTPUT_SCHEMA["properties"]["expression_frames"]["items"]
        self.assertNotIn("domain", expression["properties"])
        self.assertEqual(
            expression["properties"]["value"]["enum"],
            ["angry", "happy", "neutral", "sad", "surprised"],
        )

    def test_prompt_has_no_union_placeholder_or_function_call_names(self):
        self.assertNotIn("expression | motion", runner.SYSTEM_PROMPT)
        self.assertNotIn("set_expression", runner.SYSTEM_PROMPT)
        self.assertNotIn("play_motion", runner.SYSTEM_PROMPT)
        self.assertIn("対応する配列を空にします", runner.SYSTEM_PROMPT)

    @patch.object(runner, "_call_ollama")
    def test_run_case_uses_schema_and_unchanged_grounded_compiler(self, mock_call):
        mock_call.return_value = (
            {
                "message": {
                    "content": json.dumps(
                        {
                            "expression_frames": [],
                            "motion_frames": [
                                {
                                    "value": "wave",
                                    "commitment": "requested",
                                    "evidence": "手を振って",
                                }
                            ],
                            "gaze_frames": [],
                            "unsupported_frames": [],
                        },
                        ensure_ascii=False,
                    )
                }
            },
            1.0,
            1,
            [],
        )
        case = {
            "user_input": "手を振って。",
            "expected_calls": [{"name": "play_motion", "arguments": {"motion": "wave"}}],
            "forbidden_calls": [],
            "expected_no_action": False,
            "expected_derived_state": "explicit_current_request",
            "expected_frames": [
                {
                    "domain": "motion",
                    "value": "wave",
                    "commitment": "requested",
                    "evidence_options": ["手を振って"],
                }
            ],
        }
        generation = {
            "temperature": 0.0,
            "top_p": 1.0,
            "seed": 7,
            "context_tokens": 512,
            "maximum_output_tokens": 64,
        }
        model = {"model_tag": "test", "blob_bytes": 1, "thinking": False}
        result = runner._run_case(
            case, generation, model, runner.load_v39_anchor_ontology()
        )
        self.assertTrue(result["action_score"]["exact_match"])
        self.assertTrue(result["parsed"]["trace_wellformed"])
        body = mock_call.call_args.args[0]
        self.assertEqual(body["format"], runner.OUTPUT_SCHEMA)
        self.assertEqual(body["options"]["seed"], 7)


if __name__ == "__main__":
    unittest.main()
