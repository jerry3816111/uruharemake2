#!/usr/bin/env python3

import json
import unittest
from pathlib import Path

from action_candidate_perception_v47 import load_v47_anchor_ontology
from grounded_commitment_classifier_v42 import ground_supported_targets
from mention_bound_discourse_operators_v55 import resolve_target_state


ROOT = Path(__file__).resolve().parent
V52_CONFIG_PATH = ROOT / "configs" / "precise_target_mentions_v52_preregistration.json"


class MentionBoundDiscourseOperatorsV55Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config = json.loads(V52_CONFIG_PATH.read_text(encoding="utf-8"))
        cls.patterns = config["causal_change"]["target_mention_patterns"]
        cls.ontology = load_v47_anchor_ontology()

    def resolve(self, text, target_id):
        candidates = ground_supported_targets(text, self.ontology)
        return resolve_target_state(text, candidates, target_id, self.patterns)

    def test_pending_operator_does_not_leak_from_another_clause(self):
        result = self.resolve(
            "彼は計画があるかどうか尋ねたので、私は地図を指差しました。",
            "motion.point",
        )
        self.assertEqual(result["commitment"], "mentioned")
        self.assertEqual(result["resolution_rule"], "mention_bound_scope_reassignment")

    def test_request_force_does_not_leak_to_described_expression(self):
        result = self.resolve(
            "ずっと無表情で考えているけれど、必要なら名前を教えてほしい。",
            "expression.neutral",
        )
        self.assertEqual(result["commitment"], "mentioned")
        self.assertEqual(result["resolution_rule"], "mention_bound_request_force")

    def test_execution_prohibition_paraphrase_binds_to_quoted_target(self):
        result = self.resolve(
            "台本の『手を振って』は例文だが、その動作は禁止。",
            "motion.wave",
        )
        self.assertEqual(result["commitment"], "negated")
        self.assertEqual(
            result["resolution_rule"], "mention_bound_execution_prohibition"
        )

    def test_correction_can_replace_an_action_in_another_domain(self):
        text = "左を向いて。いや、今はじっとしていて。"
        left = self.resolve(text, "gaze.left")
        idle = self.resolve(text, "motion.idle")
        self.assertEqual(left["commitment"], "cancelled")
        self.assertEqual(
            left["resolution_rule"], "mention_bound_cross_domain_replacement"
        )
        self.assertEqual(idle["commitment"], "requested")

    def test_finite_action_assertion_resolves_as_mention(self):
        result = self.resolve(
            "彼は返事の代わりに軽くうなずき返した。", "motion.nod"
        )
        self.assertEqual(result["commitment"], "mentioned")

    def test_colloquial_sentence_final_directive_resolves_as_request(self):
        result = self.resolve("ちょっとじっとしてて。", "motion.idle")
        self.assertEqual(result["commitment"], "requested")
        self.assertEqual(result["resolution_rule"], "mention_bound_local_directive")

    def test_local_pending_and_existing_direct_request_do_not_regress(self):
        pending = self.resolve("手を振るかどうかはまだ決めてない。", "motion.wave")
        direct = self.resolve("こちらを見て。", "gaze.user")
        self.assertEqual(pending["commitment"], "ambiguous")
        self.assertEqual(direct["commitment"], "requested")
        self.assertNotIn("v55_correction", direct)


if __name__ == "__main__":
    unittest.main()
