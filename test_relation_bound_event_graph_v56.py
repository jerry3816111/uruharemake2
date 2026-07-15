#!/usr/bin/env python3

import json
import unittest
from pathlib import Path

from action_candidate_perception_v47 import load_v47_anchor_ontology
from grounded_commitment_classifier_v42 import ground_supported_targets
from relation_bound_event_graph_v56 import resolve_target_state


ROOT = Path(__file__).resolve().parent
PATTERNS = json.loads(
    (ROOT / "configs" / "precise_target_mentions_v52_preregistration.json").read_text(
        encoding="utf-8"
    )
)["causal_change"]["target_mention_patterns"]


class RelationBoundEventGraphV56Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ontology = load_v47_anchor_ontology()

    def resolve(self, text, target_id):
        candidates = ground_supported_targets(text, self.ontology)
        self.assertIn(target_id, {row["target_id"] for row in candidates})
        return resolve_target_state(text, candidates, target_id, PATTERNS)

    def assert_commitment(self, text, target_id, expected):
        row = self.resolve(text, target_id)
        self.assertEqual(row["commitment"], expected)
        self.assertIn("v56_relation_graph", row)
        return row

    def test_polite_and_colloquial_directives_remain_requests(self):
        self.assert_commitment("こちらを見てください。", "gaze.user", "requested")
        self.assert_commitment("こちらを見てもらえる？", "gaze.user", "requested")
        self.assert_commitment("手だけ振って。", "motion.wave", "requested")
        self.assert_commitment("じっとしてて。", "motion.idle", "requested")

    def test_final_directive_shares_force_with_coordinated_action(self):
        text = "右へ視線を向けたまま、手を振って。"
        row = self.assert_commitment(text, "gaze.right", "requested")
        self.assertIn("shared_directive", row["v56_relation_graph"]["relation_types"])
        self.assert_commitment(text, "motion.wave", "requested")

    def test_condition_governs_consequent_in_another_clause(self):
        row = self.assert_commitment(
            "もし私が合図したら、左を向いて。", "gaze.left", "hypothetical"
        )
        self.assertIn(
            "conditional_governance", row["v56_relation_graph"]["relation_types"]
        )

    def test_past_event_is_description_not_request(self):
        self.assert_commitment("私は木を指差しました。", "motion.point", "mentioned")
        self.assert_commitment(
            "僕は黙って、軽くうなずき返した。", "motion.nod", "mentioned"
        )

    def test_progressive_target_does_not_inherit_later_request(self):
        self.assert_commitment(
            "無表情で考えているけど、気になるなら話してほしい。",
            "expression.neutral",
            "mentioned",
        )

    def test_narrative_coordination_is_description(self):
        self.assert_commitment(
            "私たちは手を振って別れを告げた。", "motion.wave", "mentioned"
        )
        self.assert_commitment(
            "地点を指し示し、場所を確認した。", "motion.point", "mentioned"
        )

    def test_explanatory_and_visible_states_are_descriptions(self):
        self.assert_commitment(
            "首を横に振ることで拒否を表す。", "motion.shake_head", "mentioned"
        )
        self.assert_commitment(
            "左に見える扉が入口です。", "gaze.left", "mentioned"
        )

    def test_execution_prohibition_binds_to_quoted_action(self):
        row = self.assert_commitment(
            "台本は『手を振って』だけど、実行は禁止。",
            "motion.wave",
            "negated",
        )
        self.assertEqual(row["resolution_rule"], "relation_bound_execution_prohibition")

    def test_cross_domain_correction_replaces_prior_action(self):
        text = "右を向いて。いや、今は動かないでいて。"
        self.assert_commitment(text, "gaze.right", "cancelled")
        self.assert_commitment(text, "motion.idle", "requested")

    def test_local_negation_stays_protected(self):
        text = "右は見ないで、左に視線を向けてください。"
        self.assert_commitment(text, "gaze.right", "negated")
        self.assert_commitment(text, "gaze.left", "requested")

    def test_output_has_no_execution_authority(self):
        row = self.resolve("笑って。", "expression.happy")
        self.assertNotIn("accepted_calls", row)
        self.assertNotIn("execute_now", row)
        self.assertNotIn("expected_calls", row)


if __name__ == "__main__":
    unittest.main()
