#!/usr/bin/env python3

import json
import unittest
from unittest.mock import patch

import run_discourse_state_perception_v45 as runner


class RunDiscourseStatePerceptionV45Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(runner.CONFIG_PATH.read_text(encoding="utf-8"))
        cls.v44_lock = json.loads(runner.V44_LOCK_PATH.read_text(encoding="utf-8"))
        cls.prompts = runner.build_system_prompts(cls.config, cls.v44_lock)
        text = "手を振るかは、後で決める。"
        cls.row = {
            "user_input": text,
            "candidates": [
                {
                    "target_id": "motion.wave",
                    "domain": "motion",
                    "value": "wave",
                    "anchors": [{"text": "手を振", "start": 0, "end": 3, "pattern": "手を振"}],
                }
            ],
        }

    def test_candidate_only_adds_discourse_signals_without_gold(self):
        focus = self.row["candidates"][0]
        control = runner._user_payload(
            "taxonomy_definition_only", self.row, focus, self.config
        )
        candidate = runner._user_payload(
            "taxonomy_plus_discourse_signals_candidate", self.row, focus, self.config
        )
        self.assertEqual(set(candidate) - set(control), {"focus_discourse_state_signals"})
        encoded = json.dumps(candidate)
        self.assertNotIn("expected", encoded)
        self.assertNotIn("gold", encoded)

    def test_prompts_define_boundaries_without_action_examples(self):
        candidate = self.prompts["taxonomy_plus_discourse_signals_candidate"]
        self.assertIn("ongoing_action_cessation", candidate)
        self.assertIn("pending_choice", candidate)
        for example in ("手を振", "うなず", "笑顔"):
            self.assertNotIn(example, candidate)

    @patch.object(runner, "_call_ollama")
    def test_judgment_uses_frozen_two_field_carrier(self, mock_call):
        mock_call.return_value = (
            {"message": {"content": json.dumps({"commitment": "ambiguous", "contract_ack": "v44"})}},
            0.5,
            1,
            [],
        )
        snapshot = {"model_tag": "test", "size": 1, "thinking": False}
        result = runner._run_judgment(
            "taxonomy_plus_discourse_signals_candidate",
            self.row,
            self.row["candidates"][0],
            self.config,
            self.prompts,
            snapshot,
        )
        self.assertTrue(result["parsed"]["parse_success"])
        self.assertEqual(
            mock_call.call_args.args[0]["format"],
            runner.SCHEMAS["two_field_object_schema"],
        )


if __name__ == "__main__":
    unittest.main()
