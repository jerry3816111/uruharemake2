#!/usr/bin/env python3

import json
import unittest
from pathlib import Path

from action_candidate_perception_v47 import load_v47_anchor_ontology
from grounded_commitment_classifier_v42 import ground_supported_targets
from relation_safety_state_v58 import resolve_target_state


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "relation_authorized_action_compiler_v57_holdout_preregistration.json"


class RelationSafetyStateV58Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patterns = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))[
            "target_mention_patterns"
        ]
        cls.ontology = load_v47_anchor_ontology()

    def _state(self, text, target_id):
        candidates = ground_supported_targets(text, self.ontology)
        self.assertIn(target_id, {row["target_id"] for row in candidates})
        return resolve_target_state(text, candidates, target_id, self.patterns)

    def test_same_domain_alternatives_are_ambiguous(self):
        cases = {
            "左か右を向いて。": ("gaze.left", "gaze.right"),
            "笑顔か無表情のどちらかにして。": (
                "expression.happy",
                "expression.neutral",
            ),
            "うなずくか首を横に振るか、どちらかで答えて。": (
                "motion.nod",
                "motion.shake_head",
            ),
        }
        for text, target_ids in cases.items():
            for target_id in target_ids:
                with self.subTest(text=text, target_id=target_id):
                    state = self._state(text, target_id)
                    self.assertEqual(state["commitment"], "ambiguous")
                    self.assertEqual(
                        state["resolution_rule"],
                        "relation_safety_exclusive_alternative",
                    )

    def test_ordered_sequences_and_joint_direction_are_not_alternatives(self):
        ordered = "まず左を向いて、それから右を向いて。"
        for target_id in ("gaze.left", "gaze.right"):
            state = self._state(ordered, target_id)
            self.assertEqual(state["commitment"], "requested")
            self.assertNotIn(
                "exclusive_alternative", state["v58_relation_graph"]["relation_types"]
            )
        joint = "通りを渡る前に左右を見なさい。"
        for target_id in ("gaze.left", "gaze.right"):
            state = self._state(joint, target_id)
            self.assertEqual(state["commitment"], "requested")

    def test_past_benefactive_is_description_but_current_polite_form_is_request(self):
        past = self._state("先生が手を振ってくださいました。", "motion.wave")
        self.assertEqual(past["commitment"], "mentioned")
        self.assertEqual(
            past["resolution_rule"],
            "relation_safety_past_benefactive_description",
        )
        current = self._state("手を振ってください。", "motion.wave")
        self.assertEqual(current["commitment"], "requested")
        self.assertNotIn(
            "past_benefactive_description",
            current["v58_relation_graph"]["relation_types"],
        )

    def test_tentative_unsettled_preference_is_ambiguous_not_direct_request(self):
        deferred = self._state(
            "笑ってほしい気もするけど、今は決められない。",
            "expression.happy",
        )
        self.assertEqual(deferred["commitment"], "ambiguous")
        self.assertEqual(
            deferred["resolution_rule"], "relation_safety_deferred_preference"
        )
        direct = self._state("笑ってほしい。", "expression.happy")
        self.assertEqual(direct["commitment"], "requested")

    def test_output_contains_no_answer_or_case_specific_fields(self):
        state = self._state("左か右を向いて。", "gaze.left")
        serialized = json.dumps(state, ensure_ascii=False)
        for forbidden in ("expected", "gold", "case_id", "sentence_id"):
            self.assertNotIn(forbidden, serialized)


if __name__ == "__main__":
    unittest.main()
