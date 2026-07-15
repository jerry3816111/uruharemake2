#!/usr/bin/env python3

import unittest

from replay_action_ontology_grounding_v38 import CONDITIONS, replay


class ReplayActionOntologyGroundingV38Tests(unittest.TestCase):
    def test_replay_uses_no_model_inference_and_all_matched_conditions(self):
        report = replay()
        self.assertFalse(report["model_inference_performed"])
        self.assertEqual(len(report["compiler_sha256"]), 64)
        self.assertEqual(len(report["replay_script_sha256"]), 64)
        self.assertEqual(tuple(report["conditions"]), CONDITIONS)
        self.assertEqual(len(report["rows"]), 36)
        self.assertTrue(
            all(set(row["conditions"]) == set(CONDITIONS) for row in report["rows"])
        )


if __name__ == "__main__":
    unittest.main()
