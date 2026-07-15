#!/usr/bin/env python3

import json
import unittest
from unittest.mock import patch

import run_action_selective_deliberation_v37 as runner


class RunActionSelectiveDeliberationV37Tests(unittest.TestCase):
    def test_output_schema_has_only_local_frames(self):
        self.assertEqual(set(runner.OUTPUT_SCHEMA["properties"]), {"frames"})
        frame = runner.OUTPUT_SCHEMA["properties"]["frames"]["items"]
        self.assertEqual(
            set(frame["required"]),
            {"domain", "value", "commitment", "evidence"},
        )
        self.assertNotIn("utterance_state", runner.SYSTEM_PROMPT)

    def test_prompt_has_no_action_examples_or_function_calls(self):
        self.assertIn("関数呼び出しや全体状態は出力しません", runner.SYSTEM_PROMPT)
        self.assertNotIn("set_expression", runner.SYSTEM_PROMPT)
        self.assertNotIn("play_motion", runner.SYSTEM_PROMPT)

    @patch.object(runner, "_call_ollama")
    def test_judgment_uses_frozen_seed_and_scores_local_frame(self, mock_call):
        mock_call.return_value = (
            {
                "message": {
                    "content": json.dumps(
                        {
                            "frames": [
                                {
                                    "domain": "motion",
                                    "value": "wave",
                                    "commitment": "requested",
                                    "evidence": "手を振って",
                                }
                            ]
                        },
                        ensure_ascii=False,
                    )
                }
            },
            1.0,
            1,
            [],
        )
        case = {"user_input": "手を振って。"}
        generation = {"pass_id": "primary", "temperature": 0.0, "top_p": 1.0, "seed": 7}
        shared = {"context_tokens": 512, "maximum_output_tokens": 64}
        model = {"model_tag": "test", "blob_bytes": 1, "thinking": False}
        row = runner._run_judgment(case, generation, model, shared)
        self.assertTrue(row["parsed"]["parse_success"])
        self.assertEqual(row["compilation"]["accepted_calls"][0]["name"], "play_motion")
        body = mock_call.call_args.args[0]
        self.assertEqual(body["options"]["seed"], 7)
        self.assertEqual(body["format"], runner.OUTPUT_SCHEMA)

    def test_policy_names_match_preregistration(self):
        self.assertEqual(
            runner.POLICIES,
            (
                "single_pass_v37_control",
                "selective_three_pass_v37_candidate",
                "always_three_pass_v37_cost_reference",
            ),
        )


if __name__ == "__main__":
    unittest.main()
