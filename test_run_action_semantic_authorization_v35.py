#!/usr/bin/env python3

import unittest

from run_action_semantic_authorization_v35 import OUTPUT_SCHEMA, SYSTEM_PROMPT


class RunActionSemanticAuthorizationV35Test(unittest.TestCase):
    def test_prompt_freezes_narrow_non_inventing_role(self):
        self.assertIn("新しいcallの作成", SYSTEM_PROMPT)
        self.assertIn("禁止", SYSTEM_PROMPT)
        self.assertIn("一字も変えず", SYSTEM_PROMPT)
        self.assertNotIn("首を縦", SYSTEM_PROMPT)
        self.assertNotIn("にこっと", SYSTEM_PROMPT)
        self.assertNotIn("目線をこっち", SYSTEM_PROMPT)

    def test_json_schema_requires_traceable_verdicts(self):
        self.assertEqual(
            OUTPUT_SCHEMA["required"], ["utterance_state", "verdicts"]
        )
        verdict = OUTPUT_SCHEMA["properties"]["verdicts"]["items"]
        self.assertEqual(
            verdict["required"],
            ["index", "authorized", "reason_code", "evidence"],
        )
        self.assertFalse(verdict["additionalProperties"])


if __name__ == "__main__":
    unittest.main()
