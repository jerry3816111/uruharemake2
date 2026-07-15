#!/usr/bin/env python3

import json
import unittest
from pathlib import Path

from action_candidate_perception_v47 import load_v47_anchor_ontology
from grounded_commitment_classifier_v42 import ground_supported_targets
from metalinguistic_nonrequest_v54 import resolve_target_state


ROOT = Path(__file__).resolve().parent
PATTERNS = json.loads(
    (ROOT / "configs" / "precise_target_mentions_v52_preregistration.json").read_text(
        encoding="utf-8"
    )
)["causal_change"]["target_mention_patterns"]


class MetalinguisticNonrequestV54Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ontology = load_v47_anchor_ontology()

    def resolve(self, text, target_id):
        candidates = ground_supported_targets(text, self.ontology)
        self.assertIn(target_id, {row["target_id"] for row in candidates})
        return resolve_target_state(text, candidates, target_id, PATTERNS)

    def test_denial_that_quote_is_instruction_is_mentioned(self):
        row = self.resolve(
            "JSONには『手を振って』とあるが、これは指示ではない。",
            "motion.wave",
        )
        self.assertEqual(row["commitment"], "mentioned")
        self.assertEqual(row["resolution_rule"], "quoted_data_declared_nonrequest")

    def test_denial_that_quote_is_request_is_mentioned(self):
        row = self.resolve(
            "分類例は『笑顔にして』だが、あなたへのお願いではありません。",
            "expression.happy",
        )
        self.assertEqual(row["commitment"], "mentioned")

    def test_explicit_execution_prohibition_remains_negated(self):
        row = self.resolve(
            "引用文は『左を向いて』。この動作は実行しないで。",
            "gaze.left",
        )
        self.assertEqual(row["commitment"], "negated")
        self.assertEqual(row["resolution_rule"], "quoted_data_with_explicit_nonexecution")

    def test_unrelated_v53_direct_request_is_unchanged(self):
        row = self.resolve("右を向いてください。", "gaze.right")
        self.assertEqual(row["commitment"], "requested")
        self.assertEqual(row["resolution_rule"], "explicit_request_force")
        self.assertNotIn("v54_correction", row)

    def test_unrelated_v53_description_is_unchanged(self):
        row = self.resolve("彼女はうなずいている。", "motion.nod")
        self.assertEqual(row["commitment"], "mentioned")
        self.assertEqual(row["resolution_rule"], "descriptive_or_habitual_mention")
        self.assertNotIn("v54_correction", row)


if __name__ == "__main__":
    unittest.main()
