#!/usr/bin/env python3

import json
import unittest
from unittest.mock import patch

import run_commitment_carrier_v44_probe as runner


class RunCommitmentCarrierV44ProbeTests(unittest.TestCase):
    def setUp(self):
        self.case = {"id": "case", "nonce": "probe-1", "source_label": "requested"}
        self.config = {
            "frozen_environment": {
                "temperature": 0.0,
                "top_p": 1.0,
                "seed": 44,
                "context_tokens": 512,
                "maximum_output_tokens": 32,
            }
        }
        self.snapshot = {"model_tag": "test", "size": 1, "thinking": False}

    @patch.object(runner, "_call_ollama")
    def test_json_carrier_sends_schema_and_nonsemantic_payload(self, mock_call):
        mock_call.return_value = (
            {"message": {"content": '"requested"'}}, 0.2, 1, []
        )
        result = runner._call_carrier("scalar_enum_schema", self.case, self.config, self.snapshot)
        self.assertTrue(result["parsed"]["parse_success"])
        body = mock_call.call_args.args[0]
        self.assertEqual(body["format"], runner.SCHEMAS["scalar_enum_schema"])
        payload = json.loads(body["messages"][1]["content"])
        self.assertEqual(set(payload), {"nonce", "source_label"})

    @patch.object(runner, "_call_ollama")
    def test_tool_carrier_has_no_format_and_never_executes_tool(self, mock_call):
        mock_call.return_value = (
            {"message": {"content": "", "tool_calls": [{"function": {"name": "record_commitment", "arguments": {"commitment": "requested"}}}]}},
            0.2,
            1,
            [],
        )
        result = runner._call_carrier("tool_call_schema", self.case, self.config, self.snapshot)
        self.assertTrue(result["parsed"]["parse_success"])
        body = mock_call.call_args.args[0]
        self.assertNotIn("format", body)
        self.assertEqual(body["tools"], [runner.TOOL])


if __name__ == "__main__":
    unittest.main()
