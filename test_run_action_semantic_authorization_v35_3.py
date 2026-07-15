#!/usr/bin/env python3

import unittest

from run_action_semantic_authorization_v35 import select_proposed_action_catalog
from run_action_semantic_authorization_v35_2 import ACTION_CATALOG_V35_2


class RunActionSemanticAuthorizationV353Test(unittest.TestCase):
    def test_only_proposed_definitions_enter_working_context(self):
        proposals = [
            {"name": "set_expression", "arguments": {"expression": "angry"}},
            {"name": "play_motion", "arguments": {"motion": "shake_head"}},
        ]
        selected = select_proposed_action_catalog(ACTION_CATALOG_V35_2, proposals)
        self.assertEqual(set(selected), {"set_expression", "play_motion"})
        self.assertEqual(set(selected["set_expression"]["expression"]), {"angry"})
        self.assertEqual(set(selected["play_motion"]["motion"]), {"shake_head"})
        self.assertNotIn("happy", repr(selected))
        self.assertNotIn("set_gaze", selected)

    def test_invalid_proposal_receives_no_invented_definition(self):
        proposals = [
            {"name": "set_gaze", "arguments": {"target": "front"}},
            {"name": "send_email", "arguments": {"target": "x"}},
        ]
        selected = select_proposed_action_catalog(ACTION_CATALOG_V35_2, proposals)
        self.assertEqual(selected, {})


if __name__ == "__main__":
    unittest.main()
