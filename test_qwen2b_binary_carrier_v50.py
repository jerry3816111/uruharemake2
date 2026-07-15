#!/usr/bin/env python3

import json
import unittest
from pathlib import Path

from qwen2b_binary_carrier_v50 import carrier_instruction, parse_carrier_response


ROOT = Path(__file__).resolve().parent
CONFIG = json.loads(
    (ROOT / "configs" / "qwen2b_binary_carrier_v50_preregistration.json").read_text(
        encoding="utf-8"
    )
)


class Qwen2BBinaryCarrierV50Tests(unittest.TestCase):
    def test_every_instruction_contains_its_exact_schema(self):
        for carrier in CONFIG["carrier_order"]:
            with self.subTest(carrier=carrier):
                prompt = carrier_instruction(CONFIG, carrier)
                schema = json.dumps(
                    CONFIG["carriers"][carrier]["schema"],
                    ensure_ascii=False,
                    sort_keys=True,
                )
                self.assertIn(schema, prompt)

    def test_boolean_parser_maps_true_and_false_to_decisions(self):
        for value, expected in ((True, "execute"), (False, "do_not_execute")):
            response = {
                "message": {
                    "content": json.dumps(
                        {"execute_now": value, "contract_ack": "v50"}
                    )
                }
            }
            parsed = parse_carrier_response(
                CONFIG, "boolean_two_field_control", response
            )
            self.assertTrue(parsed["parse_success"])
            self.assertEqual(parsed["decision"], expected)

    def test_enum_carriers_accept_only_exact_shapes(self):
        valid = {
            "enum_two_field_candidate": {
                "decision": "execute",
                "contract_ack": "v50",
            },
            "enum_single_field_candidate": {"decision": "do_not_execute"},
            "scalar_enum_candidate": "execute",
        }
        for carrier, payload in valid.items():
            with self.subTest(carrier=carrier):
                parsed = parse_carrier_response(
                    CONFIG, carrier, {"message": {"content": json.dumps(payload)}}
                )
                self.assertTrue(parsed["parse_success"])
                self.assertTrue(parsed["single_result"])

    def test_schema_echo_is_rejected(self):
        echo = {
            "additionalProperties": False,
            "properties": {"decision": "execute"},
        }
        parsed = parse_carrier_response(
            CONFIG,
            "enum_two_field_candidate",
            {"message": {"content": json.dumps(echo)}},
        )
        self.assertFalse(parsed["parse_success"])
        self.assertIn("root_fields_mismatch", parsed["errors"])


if __name__ == "__main__":
    unittest.main()
