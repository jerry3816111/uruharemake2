#!/usr/bin/env python3

import unittest

from run_action_semantic_authorization_v35_1 import SYSTEM_PROMPT_V35_1


class RunActionSemanticAuthorizationV351Test(unittest.TestCase):
    def test_only_contract_fields_are_added_without_action_examples(self):
        for field in (
            "utterance_state",
            "verdicts",
            "index",
            "authorized",
            "reason_code",
            "evidence",
        ):
            self.assertIn(field, SYSTEM_PROMPT_V35_1)
        self.assertNotIn("首を縦", SYSTEM_PROMPT_V35_1)
        self.assertNotIn("にこっと", SYSTEM_PROMPT_V35_1)
        self.assertNotIn("目線をこっち", SYSTEM_PROMPT_V35_1)
        self.assertNotIn("手を振って", SYSTEM_PROMPT_V35_1)

    def test_non_invention_and_exact_evidence_rules_remain(self):
        self.assertIn("新しいcallの作成", SYSTEM_PROMPT_V35_1)
        self.assertIn("一字も変えず", SYSTEM_PROMPT_V35_1)


if __name__ == "__main__":
    unittest.main()
