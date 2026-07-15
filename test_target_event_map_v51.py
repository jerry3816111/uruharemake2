#!/usr/bin/env python3

import unittest

from action_candidate_perception_v47 import load_v47_anchor_ontology
from grounded_commitment_classifier_v42 import ground_supported_targets
from target_event_map_v51 import build_target_event_map


class TargetEventMapV51Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ontology = load_v47_anchor_ontology()

    def build(self, text, focus):
        candidates = ground_supported_targets(text, self.ontology)
        return build_target_event_map(text, candidates, focus)

    def test_late_positive_occurrence_is_ordered_after_negated_occurrence(self):
        result = self.build(
            "手を振らないで。いや、やっぱり手を振って。", "motion.wave"
        )
        focus = result["focus_occurrences"]
        self.assertEqual(len(focus), 2)
        self.assertLess(focus[0]["sentence_index"], focus[1]["sentence_index"])
        self.assertTrue(focus[0]["scope_reasons"])
        self.assertFalse(focus[1]["scope_reasons"])
        self.assertFalse(focus[0]["is_latest_focus_occurrence"])
        self.assertTrue(focus[1]["is_latest_focus_occurrence"])

    def test_other_target_negation_is_not_attached_to_focus_target(self):
        result = self.build(
            "キックはしないで、待機姿勢にして。", "motion.idle"
        )
        focus = result["focus_occurrences"]
        self.assertEqual(len(focus), 1)
        self.assertFalse(focus[0]["scope_reasons"])
        self.assertEqual(focus[0]["relation_to_focus"], "focus")
        self.assertTrue(
            all(
                row["target_id"] == "motion.idle"
                for row in result["ordered_grounded_occurrences"]
            )
        )

    def test_cross_target_clauses_remain_observable_and_separate(self):
        result = self.build(
            "笑顔にはしない。普通の表情へ戻して。", "expression.neutral"
        )
        ordered = result["ordered_grounded_occurrences"]
        self.assertEqual(
            [row["target_id"] for row in ordered],
            ["expression.happy", "expression.neutral"],
        )
        self.assertEqual([row["sentence_index"] for row in ordered], [0, 1])
        self.assertEqual(ordered[0]["relation_to_focus"], "other")
        self.assertEqual(ordered[1]["relation_to_focus"], "focus")

    def test_map_contains_no_answer_or_execution_fields(self):
        result = self.build("軽く手を振ってみて。", "motion.wave")
        serialized_keys = set()

        def visit(value):
            if isinstance(value, dict):
                serialized_keys.update(value)
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        visit(result)
        self.assertTrue(
            {
                "ordered_grounded_occurrences",
                "focus_occurrences",
                "sentence_index",
                "clause_index",
            }.issubset(serialized_keys)
        )
        self.assertTrue(
            {"gold_commitment", "expected_calls", "execute_now"}.isdisjoint(
                serialized_keys
            )
        )

    def test_unknown_focus_is_rejected(self):
        candidates = ground_supported_targets("手を振って。", self.ontology)
        with self.assertRaises(ValueError):
            build_target_event_map("手を振って。", candidates, "motion.nod")


if __name__ == "__main__":
    unittest.main()
