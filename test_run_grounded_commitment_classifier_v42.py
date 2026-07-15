#!/usr/bin/env python3

import json
import unittest
from unittest.mock import patch

import run_grounded_commitment_classifier_v42 as runner


class RunGroundedCommitmentClassifierV42Tests(unittest.TestCase):
    def test_schema_is_dynamic_but_narrow(self):
        schema = runner.output_schema(3)
        self.assertEqual(set(schema["properties"]), {"commitment", "evidence_index"})
        self.assertEqual(schema["properties"]["evidence_index"]["enum"], [0, 1, 2])
        self.assertNotIn("frames", json.dumps(schema))

    def test_user_payload_contains_no_gold_or_case_metadata(self):
        row = {"user_input": "手を振って。"}
        candidate = {
            "domain": "motion",
            "value": "wave",
            "anchors": [{"text": "手を振", "start": 0, "end": 3}],
        }
        payload = runner._user_payload(row, candidate)
        self.assertEqual(
            set(payload), {"user_input", "target", "evidence_candidates"}
        )
        encoded = json.dumps(payload)
        self.assertNotIn("expected", encoded)
        self.assertNotIn("family", encoded)

    @patch.object(runner, "_call_ollama")
    def test_judgment_uses_fixed_generation_and_dynamic_schema(self, mock_call):
        mock_call.return_value = (
            {
                "message": {
                    "content": json.dumps(
                        {"commitment": "requested", "evidence_index": 0}
                    )
                }
            },
            0.5,
            1,
            [],
        )
        row = {"user_input": "手を振って。"}
        candidate = {
            "target_id": "motion.wave",
            "domain": "motion",
            "value": "wave",
            "anchors": [{"text": "手を振", "start": 0, "end": 3}],
        }
        generation = {
            "temperature": 0.0,
            "top_p": 1.0,
            "seed": 42,
            "context_tokens": 512,
            "maximum_output_tokens": 32,
        }
        model = {"model_tag": "test", "blob_bytes": 1, "thinking": False}
        result = runner._run_judgment(row, candidate, generation, model)
        self.assertTrue(result["parsed"]["parse_success"])
        body = mock_call.call_args.args[0]
        self.assertEqual(body["options"]["seed"], 42)
        self.assertEqual(body["format"], runner.output_schema(1))


if __name__ == "__main__":
    unittest.main()
