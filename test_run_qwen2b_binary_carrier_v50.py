#!/usr/bin/env python3

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from run_qwen2b_binary_carrier_v50 import _call_carrier, _validate_inputs


ROOT = Path(__file__).resolve().parent
CONFIG = json.loads(
    (ROOT / "configs" / "qwen2b_binary_carrier_v50_preregistration.json").read_text(
        encoding="utf-8"
    )
)
DATASET = json.loads(
    (ROOT / "datasets" / "qwen2b_binary_carrier_v50_format_probe.json").read_text(
        encoding="utf-8"
    )
)


class RunQwen2BBinaryCarrierV50Tests(unittest.TestCase):
    def test_frozen_inputs_validate_without_inference(self):
        _validate_inputs(CONFIG, DATASET)

    @patch("run_qwen2b_binary_carrier_v50._call_ollama")
    def test_call_uses_exact_carrier_and_nonsemantic_payload(self, mock_call):
        mock_call.return_value = (
            {
                "message": {
                    "role": "assistant",
                    "content": '{"decision":"execute","contract_ack":"v50"}',
                }
            },
            0.1,
            1,
            [],
        )
        snapshot = {
            "model_tag": "qwen3.5:2b",
            "size": CONFIG["frozen_model"]["blob_bytes"],
            "thinking": False,
        }
        result = _call_carrier(
            "enum_two_field_candidate", DATASET["cases"][0], CONFIG, snapshot
        )
        body = mock_call.call_args.args[0]
        payload = json.loads(body["messages"][1]["content"])
        self.assertEqual(
            body["format"],
            CONFIG["carriers"]["enum_two_field_candidate"]["schema"],
        )
        self.assertEqual(set(payload), {"nonce", "source_decision"})
        self.assertNotIn("user_input", body["messages"][1]["content"])
        self.assertTrue(result["parsed"]["parse_success"])


if __name__ == "__main__":
    unittest.main()
