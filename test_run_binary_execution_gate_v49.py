#!/usr/bin/env python3

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from run_binary_execution_gate_v49 import (
    _run_judgment,
    build_candidate_rows,
    build_prompt,
)


ROOT = Path(__file__).resolve().parent
CONFIG = json.loads(
    (ROOT / "configs" / "binary_execution_gate_v49_preregistration.json").read_text(
        encoding="utf-8"
    )
)
V45_CONFIG = json.loads(
    (ROOT / "configs" / "discourse_state_perception_v45_preregistration.json").read_text(
        encoding="utf-8"
    )
)
DATASET = json.loads(
    (ROOT / "datasets" / "discourse_state_perception_v45_holdout.json").read_text(
        encoding="utf-8"
    )
)


class RunBinaryExecutionGateV49Tests(unittest.TestCase):
    def test_prompt_is_frozen_binary_task_without_benchmark_answers(self):
        prompt = build_prompt(CONFIG)
        self.assertIn("execute_now", prompt)
        self.assertIn("v49", prompt)
        self.assertNotIn("ToMBench", prompt)
        self.assertNotIn("expected_calls", prompt)
        self.assertNotIn("gold", prompt.lower())

    def test_v47_candidate_rows_match_preregistered_count(self):
        rows = build_candidate_rows(DATASET)
        self.assertEqual(len(rows), 48)
        self.assertEqual(sum(len(row["candidates"]) for row in rows), 61)

    @patch("run_binary_execution_gate_v49._call_ollama")
    def test_judgment_sends_exact_schema_and_non_gold_payload(self, mock_call):
        mock_call.return_value = (
            {
                "message": {
                    "role": "assistant",
                    "content": '{"execute_now":true,"contract_ack":"v49"}',
                }
            },
            0.1,
            1,
            [],
        )
        row = build_candidate_rows(DATASET)[0]
        snapshot = {
            "model_tag": "qwen3.5:0.8b",
            "size": 1,
            "thinking": False,
        }
        result = _run_judgment(
            "qwen35_0_8b_binary",
            row,
            row["candidates"][0],
            build_prompt(CONFIG),
            CONFIG,
            V45_CONFIG,
            snapshot,
        )
        body = mock_call.call_args.args[0]
        payload = json.loads(body["messages"][1]["content"])
        self.assertEqual(body["format"], CONFIG["binary_contract"])
        self.assertEqual(set(payload), set(CONFIG["payload_fields"]))
        self.assertNotIn("expected", body["messages"][1]["content"])
        self.assertTrue(result["parsed"]["parse_success"])


if __name__ == "__main__":
    unittest.main()
