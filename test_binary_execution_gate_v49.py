#!/usr/bin/env python3

import json
import unittest
from pathlib import Path

from action_candidate_perception_v47 import load_v47_anchor_ontology
from binary_execution_gate_v49 import (
    binary_result_to_judgment,
    build_binary_gate_payload,
    parse_binary_gate_response,
)
from grounded_commitment_classifier_v42 import ground_supported_targets


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


class BinaryExecutionGateV49Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ontology = load_v47_anchor_ontology()
        cls.patterns = V45_CONFIG["deterministic_discourse_signals"]["patterns"]

    def test_parser_accepts_only_exact_boolean_contract(self):
        parsed = parse_binary_gate_response(
            {"message": {"content": '{"execute_now":true,"contract_ack":"v49"}'}}
        )
        self.assertTrue(parsed["parse_success"])
        self.assertTrue(parsed["execute_now"])
        for invalid in (
            '{"execute_now":1,"contract_ack":"v49"}',
            '{"execute_now":true,"contract_ack":"v48"}',
            '{"execute_now":true,"contract_ack":"v49","reason":"x"}',
            "not-json",
        ):
            with self.subTest(invalid=invalid):
                self.assertFalse(
                    parse_binary_gate_response({"message": {"content": invalid}})[
                        "parse_success"
                    ]
                )

    def test_binary_result_maps_true_to_request_and_failure_to_fail_closed(self):
        self.assertEqual(
            binary_result_to_judgment(
                {"parse_success": True, "errors": [], "execute_now": True}
            )["commitment"],
            "requested",
        )
        self.assertEqual(
            binary_result_to_judgment(
                {"parse_success": True, "errors": [], "execute_now": False}
            )["commitment"],
            "mentioned",
        )
        self.assertFalse(
            binary_result_to_judgment(
                {"parse_success": False, "errors": ["invalid_json"]}
            )["parse_success"]
        )

    def test_payload_separates_negated_left_from_safe_right(self):
        text = "左じゃなくて右を見て。"
        candidates = ground_supported_targets(text, self.ontology)
        by_id = {row["target_id"]: row for row in candidates}
        left = build_binary_gate_payload(
            text,
            by_id["gaze.left"],
            candidates,
            self.patterns,
            CONFIG["payload_fields"],
        )
        right = build_binary_gate_payload(
            text,
            by_id["gaze.right"],
            candidates,
            self.patterns,
            CONFIG["payload_fields"],
        )
        self.assertFalse(left["safe_anchor_evidence"])
        self.assertTrue(left["blocked_anchor_evidence"])
        self.assertTrue(right["safe_anchor_evidence"])
        self.assertFalse(right["blocked_anchor_evidence"])

    def test_payload_contains_no_gold_or_expected_answer(self):
        text = "軽く手を振ってみて。"
        candidates = ground_supported_targets(text, self.ontology)
        payload = build_binary_gate_payload(
            text,
            candidates[0],
            candidates,
            self.patterns,
            CONFIG["payload_fields"],
        )
        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertEqual(set(payload), set(CONFIG["payload_fields"]))
        self.assertNotIn("expected", serialized)
        self.assertNotIn("gold", serialized)
        self.assertNotIn("expected_calls", serialized)


if __name__ == "__main__":
    unittest.main()
