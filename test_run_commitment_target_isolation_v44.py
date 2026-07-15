#!/usr/bin/env python3

import json
import unittest
from unittest.mock import patch

import run_commitment_target_isolation_v44 as runner


class RunCommitmentTargetIsolationV44Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(runner.LOCK_PATH.read_text(encoding="utf-8"))
        cls.prereg = json.loads(runner.PREREG_PATH.read_text(encoding="utf-8"))
        cls.prompts = runner.build_system_prompts(cls.lock)
        cls.row = {
            "user_input": "笑った顔でこちらを見て。",
            "candidates": [
                {
                    "target_id": "expression.happy",
                    "domain": "expression",
                    "value": "happy",
                    "anchors": [{"text": "笑った顔", "start": 0, "end": 4, "pattern": "笑った顔"}],
                },
                {
                    "target_id": "gaze.user",
                    "domain": "gaze",
                    "value": "user",
                    "anchors": [{"text": "こちらを見", "start": 5, "end": 10, "pattern": "こちらを見"}],
                },
            ],
        }

    def test_prompts_use_selected_schema_without_lexical_examples(self):
        for prompt in self.prompts.values():
            self.assertIn("contract_ack", prompt)
            self.assertIn("Exact output schema", prompt)
            self.assertNotIn("手を振", prompt)
            self.assertNotIn("expected_calls", prompt)

    def test_payload_layers_match_the_frozen_conditions(self):
        focus = self.row["candidates"][0]
        target_only = runner._user_payload("target_only_control", self.row, focus)
        all_targets = runner._user_payload("all_targets_relational", self.row, focus)
        isolated = runner._user_payload("isolated_other_targets", self.row, focus)
        scoped = runner._user_payload("isolated_scope_signals_candidate", self.row, focus)
        self.assertEqual(set(target_only), {"user_input", "target", "evidence_candidates"})
        self.assertEqual(len(all_targets["all_grounded_targets"]), 2)
        self.assertEqual(len(isolated["context_only_other_targets"]), 1)
        self.assertEqual(isolated["context_only_other_targets"][0]["value"], "user")
        self.assertIn("focus_anchor_scope_signals", scoped)
        encoded = json.dumps(scoped)
        self.assertNotIn("expected", encoded)
        self.assertNotIn("commitment", encoded)

    @patch.object(runner, "_call_ollama")
    def test_judgment_uses_selected_two_field_carrier(self, mock_call):
        mock_call.return_value = (
            {"message": {"content": json.dumps({"commitment": "requested", "contract_ack": "v44"})}},
            0.5,
            1,
            [],
        )
        snapshot = {"model_tag": "test", "size": 1, "thinking": False}
        result = runner._run_judgment(
            "isolated_other_targets",
            self.row,
            self.row["candidates"][0],
            self.prompts,
            self.lock,
            self.prereg,
            snapshot,
        )
        self.assertTrue(result["parsed"]["parse_success"])
        body = mock_call.call_args.args[0]
        self.assertEqual(body["format"], runner.SCHEMAS["two_field_object_schema"])


if __name__ == "__main__":
    unittest.main()
