#!/usr/bin/env python3

import json
import unittest

from commitment_carrier_v44 import CARRIERS, SCHEMAS, carrier_instruction, parse_carrier_response


class CommitmentCarrierV44Tests(unittest.TestCase):
    def test_every_carrier_instruction_contains_its_exact_schema(self):
        for carrier in CARRIERS:
            prompt = carrier_instruction(carrier)
            self.assertIn("Exact carrier schema", prompt)
            self.assertNotIn("手を振", prompt)
            self.assertNotIn("expected", prompt)

    def test_scalar_and_object_carriers_are_strict(self):
        scalar = parse_carrier_response(
            "scalar_enum_schema", {"message": {"content": '"requested"'}}
        )
        two_field = parse_carrier_response(
            "two_field_object_schema",
            {"message": {"content": json.dumps({"commitment": "negated", "contract_ack": "v44"})}},
        )
        nested = parse_carrier_response(
            "nested_label_schema",
            {"message": {"content": json.dumps({"classification": {"commitment": "ambiguous"}})}},
        )
        self.assertTrue(scalar["parse_success"])
        self.assertTrue(two_field["parse_success"])
        self.assertTrue(nested["parse_success"])
        malformed = parse_carrier_response(
            "two_field_object_schema",
            {"message": {"content": json.dumps({"commitment": "requested"})}},
        )
        self.assertFalse(malformed["parse_success"])

    def test_tool_carrier_requires_one_exact_internal_call_and_no_content(self):
        response = {
            "message": {
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "record_commitment",
                            "arguments": {"commitment": "cancelled"},
                        }
                    }
                ],
            }
        }
        parsed = parse_carrier_response("tool_call_schema", response)
        self.assertTrue(parsed["parse_success"])
        self.assertEqual(parsed["commitment"], "cancelled")
        response["message"]["content"] = "done"
        self.assertFalse(parse_carrier_response("tool_call_schema", response)["parse_success"])

    def test_schema_does_not_contain_benchmark_or_action_values(self):
        encoded = json.dumps(SCHEMAS, ensure_ascii=False)
        for forbidden in ("wave", "happy", "gaze", "expected_calls"):
            self.assertNotIn(forbidden, encoded)


if __name__ == "__main__":
    unittest.main()
