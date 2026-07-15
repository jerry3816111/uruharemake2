#!/usr/bin/env python3

import json
import unittest
from pathlib import Path

from action_candidate_perception_v47 import load_v47_anchor_ontology
from grounded_commitment_classifier_v42 import ground_supported_targets
from precise_target_mentions_v52 import (
    audit_precise_event_maps,
    build_precise_target_event_map,
)
from run_target_event_map_v51 import build_candidate_rows


class PreciseTargetMentionsV52Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ontology = load_v47_anchor_ontology()
        config = json.loads(
            Path("configs/precise_target_mentions_v52_preregistration.json").read_text(
                encoding="utf-8"
            )
        )
        cls.patterns = config["causal_change"]["target_mention_patterns"]

    def build(self, text, focus):
        candidates = ground_supported_targets(text, self.ontology)
        return build_precise_target_event_map(
            text, candidates, focus, self.patterns
        )

    def test_contrastive_targets_have_separate_exact_mentions(self):
        result = self.build("左じゃなくて右を見て。", "gaze.right")
        ordered = result["ordered_grounded_occurrences"]
        self.assertEqual(
            [row["target_id"] for row in ordered], ["gaze.left", "gaze.right"]
        )
        self.assertEqual(ordered[0]["target_mentions"][0]["text"], "左")
        self.assertEqual(ordered[1]["target_mentions"][0]["text"], "右")
        self.assertIn("右", ordered[0]["predicate_evidence"][0]["text"])
        self.assertTrue(ordered[0]["scope_reasons"])
        self.assertFalse(ordered[1]["scope_reasons"])

    def test_late_same_target_mentions_keep_original_order(self):
        result = self.build(
            "手を振らないで。いや、やっぱり手を振って。", "motion.wave"
        )
        focus = result["focus_occurrences"]
        self.assertEqual(len(focus), 2)
        self.assertLess(
            focus[0]["target_mentions"][0]["start"],
            focus[1]["target_mentions"][0]["start"],
        )
        self.assertFalse(focus[0]["is_latest_focus_occurrence"])
        self.assertTrue(focus[1]["is_latest_focus_occurrence"])

    def test_retired_dataset_has_full_nonfallback_mention_coverage(self):
        dataset = json.loads(
            Path("datasets/discourse_state_perception_v45_holdout.json").read_text(
                encoding="utf-8"
            )
        )
        rows = build_candidate_rows(dataset)
        audit = audit_precise_event_maps(rows, self.patterns)
        self.assertEqual(audit["grounded_occurrence_mention_coverage"], 1.0)
        self.assertEqual(audit["fallback_occurrence_count"], 0)
        self.assertEqual(audit["mention_inside_predicate_evidence_rate"], 1.0)
        self.assertEqual(audit["cross_target_mention_overlap_count"], 0)

    def test_map_has_no_commitment_or_execution_answer(self):
        result = self.build("右のほうを見てくれる？", "gaze.right")
        keys = set()

        def visit(value):
            if isinstance(value, dict):
                keys.update(value)
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        visit(result)
        self.assertTrue({"target_mentions", "predicate_evidence"}.issubset(keys))
        self.assertTrue(
            {"gold_commitment", "expected_calls", "execute_now"}.isdisjoint(keys)
        )


if __name__ == "__main__":
    unittest.main()
