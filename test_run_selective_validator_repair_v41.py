#!/usr/bin/env python3

import json
import unittest
from unittest.mock import patch

import run_selective_validator_repair_v41 as runner


class RunSelectiveValidatorRepairV41Tests(unittest.TestCase):
    def test_feedback_payload_contains_no_gold_or_benchmark_metadata(self):
        primary = {
            "user_input": "表情について話そう。",
            "raw_reply": json.dumps({"frames": []}),
            "parsed": {
                "errors": [],
                "warnings": [{"index": 0, "reasons": ["invalid_domain_value"], "raw_frame": {}}],
            },
        }
        payload = runner._feedback_payload(primary)
        self.assertEqual(
            set(payload), {"user_input", "previous_output", "validator_feedback"}
        )
        encoded = json.dumps(payload)
        self.assertNotIn("expected_calls", encoded)
        self.assertNotIn("expected_frames", encoded)
        self.assertNotIn("family", encoded)

    def test_trigger_set_must_match_preregistered_ids(self):
        config = {
            "repair_trigger": {
                "expected_development_case_ids": ["bad_a", "bad_b"]
            }
        }
        rows = [
            {"case_id": "bad_a", "parsed": {"trace_wellformed": False}},
            {"case_id": "bad_b", "parsed": {"trace_wellformed": False}},
            {"case_id": "good", "parsed": {"trace_wellformed": True}},
        ]
        runner._validate_trigger_set(config, rows)

    def test_trigger_set_rejects_unplanned_case(self):
        config = {
            "repair_trigger": {"expected_development_case_ids": ["bad_a"]}
        }
        rows = [
            {"case_id": "bad_a", "parsed": {"trace_wellformed": False}},
            {"case_id": "bad_b", "parsed": {"trace_wellformed": False}},
        ]
        with self.assertRaises(ValueError):
            runner._validate_trigger_set(config, rows)

    @patch.object(runner, "_call_ollama")
    def test_repair_call_uses_only_external_feedback_and_fixed_schema(self, mock_call):
        mock_call.return_value = (
            {"message": {"content": json.dumps({"frames": []})}},
            0.5,
            1,
            [],
        )
        primary = {
            "user_input": "今日は表情の変化について話したい。",
            "raw_reply": json.dumps(
                {
                    "frames": [
                        {
                            "domain": "expression",
                            "value": "mentioned",
                            "commitment": "mentioned",
                            "evidence": "表情の変化",
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            "parsed": {
                "trace_wellformed": False,
                "errors": [],
                "warnings": [
                    {"index": 0, "reasons": ["invalid_domain_value"], "raw_frame": {}}
                ],
                "frames": [],
            },
            "compilation": {
                "accepted_calls": [],
                "accepted_frames": [],
                "ungrounded_execution_count": 0,
                "fail_closed": False,
            },
        }
        generation = {
            "temperature": 0.0,
            "top_p": 1.0,
            "seed": 41,
            "context_tokens": 512,
            "maximum_output_tokens": 64,
        }
        model = {"model_tag": "test", "blob_bytes": 1, "thinking": False}
        result = runner._run_repair(
            primary, generation, model, runner.load_v39_anchor_ontology()
        )
        self.assertTrue(result["selection"]["repair_policy"]["accepted"])
        body = mock_call.call_args.args[0]
        self.assertEqual(body["format"], runner.OUTPUT_SCHEMA)
        user_payload = json.loads(body["messages"][1]["content"])
        self.assertEqual(
            set(user_payload), {"user_input", "previous_output", "validator_feedback"}
        )


if __name__ == "__main__":
    unittest.main()
