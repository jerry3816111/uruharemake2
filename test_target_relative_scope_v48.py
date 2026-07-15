#!/usr/bin/env python3

import json
import unittest
from pathlib import Path

from action_candidate_perception_v47 import load_v47_anchor_ontology
from grounded_commitment_classifier_v42 import ground_supported_targets
from target_relative_scope_v48 import (
    compile_target_relative_v48,
    perceive_target_relative_scope,
)


ROOT = Path(__file__).resolve().parent


def _frame(domain, value, commitment, evidence):
    return {
        "domain": domain,
        "value": value,
        "commitment": commitment,
        "evidence": evidence,
        "evidence_valid": True,
    }


class TargetRelativeScopeV48Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ontology = load_v47_anchor_ontology()

    def _scope(self, text):
        candidates = ground_supported_targets(text, self.ontology)
        return perceive_target_relative_scope(text, candidates)

    def _target(self, scope, target_id):
        return next(row for row in scope["targets"] if row["target_id"] == target_id)

    def test_negation_does_not_spill_to_later_positive_target(self):
        text = "左じゃなくて右を見て。"
        scope = self._scope(text)
        left = self._target(scope, "gaze.left")
        right = self._target(scope, "gaze.right")
        self.assertTrue(all(anchor["blocked"] for anchor in left["anchors"]))
        self.assertTrue(any(not anchor["blocked"] for anchor in right["anchors"]))

    def test_lexical_nod_stem_is_safe_but_negative_suffix_is_blocked(self):
        positive = self._target(self._scope("うなずいて。"), "motion.nod")
        self.assertTrue(all(not anchor["blocked"] for anchor in positive["anchors"]))
        negative = self._target(
            self._scope("うなずかずに、首を横に振って。"), "motion.nod"
        )
        self.assertTrue(all(anchor["blocked"] for anchor in negative["anchors"]))

    def test_same_target_late_correction_keeps_one_safe_occurrence(self):
        scope = self._scope("うなずかないで。いや、やっぱりうなずいて。")
        nod = self._target(scope, "motion.nod")
        self.assertGreaterEqual(sum(anchor["blocked"] for anchor in nod["anchors"]), 1)
        self.assertGreaterEqual(sum(not anchor["blocked"] for anchor in nod["anchors"]), 1)

    def test_compiler_accepts_positive_replacement_without_accepting_negated_target(self):
        text = "左じゃなくて右を見て。"
        parsed = {
            "parse_success": True,
            "frames": [
                _frame("gaze", "left", "negated", "左じゃなくて右を見"),
                _frame("gaze", "right", "requested", "右を見"),
            ],
        }
        compiled = compile_target_relative_v48(text, parsed, self.ontology)
        self.assertEqual(
            compiled["accepted_calls"],
            [{"name": "set_gaze", "arguments": {"target": "right"}}],
        )

    def test_referential_cancellation_blocks_preceding_request(self):
        text = "頷いて。いや、そのお願いはキャンセル。"
        scope = self._scope(text)
        nod = self._target(scope, "motion.nod")
        reason_types = {
            reason["marker_type"]
            for anchor in nod["anchors"]
            for reason in anchor["scope_reasons"]
        }
        self.assertIn("referential_cancellation", reason_types)
        self.assertTrue(all(anchor["blocked"] for anchor in nod["anchors"]))


if __name__ == "__main__":
    unittest.main()
