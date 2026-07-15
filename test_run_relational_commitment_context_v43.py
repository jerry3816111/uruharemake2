#!/usr/bin/env python3

import json
import unittest
from unittest.mock import patch

import run_relational_commitment_context_v43 as runner


class RunRelationalCommitmentContextV43Tests(unittest.TestCase):
    def setUp(self):
        self.row = {
            "user_input": "笑った顔でこちらを見て。",
            "candidates": [
                {
                    "target_id": "expression.happy",
                    "domain": "expression",
                    "value": "happy",
                    "anchors": [
                        {
                            "text": "笑った顔",
                            "start": 0,
                            "end": 4,
                            "pattern": "笑った顔",
                        }
                    ],
                },
                {
                    "target_id": "gaze.user",
                    "domain": "gaze",
                    "value": "user",
                    "anchors": [
                        {
                            "text": "こちらを見",
                            "start": 5,
                            "end": 10,
                            "pattern": "こちらを見",
                        }
                    ],
                },
            ],
        }

    def test_schema_contains_only_commitment(self):
        self.assertEqual(set(runner.OUTPUT_SCHEMA["properties"]), {"commitment"})
        self.assertEqual(runner.OUTPUT_SCHEMA["required"], ["commitment"])
        self.assertFalse(runner.OUTPUT_SCHEMA["additionalProperties"])

    def test_base_payload_matches_v42_input_shape_without_gold(self):
        payload = runner._user_payload(
            "commitment_only_candidate", self.row, self.row["candidates"][0]
        )
        self.assertEqual(
            set(payload), {"user_input", "target", "evidence_candidates"}
        )
        self.assertEqual(payload["target"], {"domain": "expression", "value": "happy"})
        self.assertEqual(
            payload["evidence_candidates"], [{"index": 0, "text": "笑った顔"}]
        )
        encoded = json.dumps(payload)
        self.assertNotIn("expected", encoded)
        self.assertNotIn("family", encoded)

    def test_relational_payload_adds_all_targets_with_exact_spans(self):
        payload = runner._user_payload(
            "relational_context_candidate", self.row, self.row["candidates"][0]
        )
        self.assertEqual(len(payload["all_grounded_targets"]), 2)
        self.assertEqual(
            payload["all_grounded_targets"][1]["anchors"][0],
            {"text": "こちらを見", "start": 5, "end": 10},
        )
        self.assertNotIn("commitment", json.dumps(payload["all_grounded_targets"]))

    def test_relational_guidance_is_general_not_lexical_demonstration(self):
        prompt = runner.SYSTEM_PROMPTS["relational_context_candidate"]
        self.assertIn("all_grounded_targets", prompt)
        self.assertIn("局所範囲", prompt)
        for lexical_example in ("手を振", "首を横", "笑った顔", "こちらを見"):
            self.assertNotIn(lexical_example, prompt)

    @patch.object(runner, "_call_ollama")
    def test_judgment_uses_fixed_schema_and_condition_prompt(self, mock_call):
        mock_call.return_value = (
            {"message": {"content": json.dumps({"commitment": "requested"})}},
            0.5,
            1,
            [],
        )
        generation = {
            "temperature": 0.0,
            "top_p": 1.0,
            "seed": 42,
            "context_tokens": 512,
            "maximum_output_tokens": 32,
        }
        model = {"model_tag": "test", "blob_bytes": 1, "thinking": False}
        result = runner._run_judgment(
            "relational_context_candidate",
            self.row,
            self.row["candidates"][0],
            generation,
            model,
        )
        self.assertTrue(result["parsed"]["parse_success"])
        body = mock_call.call_args.args[0]
        self.assertEqual(body["options"]["seed"], 42)
        self.assertEqual(body["format"], runner.OUTPUT_SCHEMA)
        self.assertEqual(
            body["messages"][0]["content"],
            runner.SYSTEM_PROMPTS["relational_context_candidate"],
        )


if __name__ == "__main__":
    unittest.main()
