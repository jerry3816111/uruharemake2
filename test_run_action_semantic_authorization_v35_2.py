#!/usr/bin/env python3

import unittest

from run_action_semantic_authorization_v35_2 import ACTION_CATALOG_V35_2
from vrm_action_policy_v34 import ACTION_SPECS, _spec_key


class RunActionSemanticAuthorizationV352Test(unittest.TestCase):
    def test_catalog_defines_every_allowlisted_call(self):
        catalog_keys = set()
        for function_name, function in ACTION_CATALOG_V35_2.items():
            argument_name = next(
                key for key in function if key != "description_ja"
            )
            for value in function[argument_name]:
                catalog_keys.add(f"{function_name}:{argument_name}={value}")
        self.assertEqual(catalog_keys, {_spec_key(spec) for spec in ACTION_SPECS})

    def test_catalog_contains_no_retired_holdout_sentences(self):
        rendered = repr(ACTION_CATALOG_V35_2)
        for phrase in (
            "首を縦に動かして",
            "にこっとして",
            "目線をこっちにちょうだい",
            "うなずかないで、首を横に振って",
        ):
            self.assertNotIn(phrase, rendered)


if __name__ == "__main__":
    unittest.main()
