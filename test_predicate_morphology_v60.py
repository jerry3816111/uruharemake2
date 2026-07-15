#!/usr/bin/env python3

import json
import unittest
from pathlib import Path

from action_candidate_perception_v47 import load_v47_anchor_ontology
from grounded_commitment_classifier_v42 import ground_supported_targets
from predicate_morphology_v60 import (
    COMPLETED_RELATION,
    build_predicate_morphology,
    resolve_target_state,
)


ROOT = Path(__file__).resolve().parent
PATTERN_CONFIG_PATH = (
    ROOT / "configs" / "relation_safety_state_v58_holdout_preregistration.json"
)


class PredicateMorphologyV60Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ontology = load_v47_anchor_ontology()
        cls.patterns = json.loads(PATTERN_CONFIG_PATH.read_text(encoding="utf-8"))[
            "target_mention_patterns"
        ]

    def resolve(self, text, target_id):
        candidates = ground_supported_targets(text, self.ontology)
        self.assertIn(target_id, {row["target_id"] for row in candidates})
        return resolve_target_state(text, candidates, target_id, self.patterns)

    def test_completed_third_party_benefactive_needs_no_time_adverb(self):
        for text, target_id in (
            ("姉が玄関で笑顔を見せてくれた。", "expression.happy"),
            ("友人がこっちを見てくれて助かった。", "gaze.user"),
        ):
            with self.subTest(text=text):
                result = self.resolve(text, target_id)
                graph = result["v60_event_role_graph"]
                self.assertEqual(result["commitment"], "mentioned")
                self.assertIn(COMPLETED_RELATION, graph["relation_types"])
                self.assertEqual(graph["event_owner"], "third_party")
                self.assertEqual(graph["event_time"], "past")
                self.assertEqual(graph["directive_governor"], "none")
                self.assertFalse(graph["direct_focus_request"])

    def test_current_benefactive_requests_remain_direct(self):
        for text, target_id in (
            ("笑顔を見せてくれませんか。", "expression.happy"),
            ("こっちを見てくれるかな。", "gaze.user"),
            ("笑ってくれ。", "expression.happy"),
        ):
            with self.subTest(text=text):
                result = self.resolve(text, target_id)
                graph = result["v60_event_role_graph"]
                self.assertEqual(result["commitment"], "requested")
                self.assertNotIn(COMPLETED_RELATION, graph["relation_types"])
                self.assertEqual(graph["event_owner"], "addressee")
                self.assertEqual(graph["event_time"], "current")
                self.assertEqual(graph["directive_governor"], "focus_event")
                self.assertTrue(graph["direct_focus_request"])

    def test_negative_benefactive_is_not_promoted_to_positive_completed_relation(self):
        result = self.resolve(
            "彼女は舞台で笑顔を見せてくれなかった。", "expression.happy"
        )
        graph = result["v60_event_role_graph"]
        self.assertNotIn(COMPLETED_RELATION, graph["relation_types"])
        self.assertNotEqual(
            graph["v60_predicate_morphology"]["predicate_force"],
            "completed_benefactive",
        )

    def test_nonimperative_kureru_suffixes_are_not_requests(self):
        for text in (
            "彼女は舞台で笑ってくれる。",
            "彼女が舞台で笑ってくれれば助かる。",
        ):
            with self.subTest(text=text):
                result = self.resolve(text, "expression.happy")
                morphology = result["v60_event_role_graph"][
                    "v60_predicate_morphology"
                ]
                self.assertNotEqual(morphology["predicate_force"], "current_directive")
                self.assertFalse(morphology["direct_focus_request"])

    def test_embedded_speech_still_governs_the_speech_act(self):
        result = self.resolve(
            "彼女がなぜ笑顔を見せたのか教えてください。", "expression.happy"
        )
        graph = result["v60_event_role_graph"]
        self.assertEqual(result["commitment"], "mentioned")
        self.assertEqual(graph["directive_governor"], "speech_act")
        self.assertFalse(graph["direct_focus_request"])

    def test_full_expression_predicate_recovers_direct_request_from_short_mentions(self):
        for text, target_id in (
            ("怒った顔を見せてください。", "expression.angry"),
            ("悲しい顔を見せてください。", "expression.sad"),
            ("驚いた顔をしてください。", "expression.surprised"),
        ):
            with self.subTest(text=text):
                result = self.resolve(text, target_id)
                morphology = result["v60_event_role_graph"][
                    "v60_predicate_morphology"
                ]
                self.assertEqual(result["commitment"], "requested")
                self.assertEqual(morphology["predicate_force"], "current_directive")
                self.assertTrue(morphology["direct_focus_request"])
                self.assertIn("顔", morphology["predicate_span"])

    def test_third_party_declarative_does_not_become_a_directive(self):
        result = self.resolve("彼女は舞台で笑顔を見せた。", "expression.happy")
        graph = result["v60_event_role_graph"]
        self.assertNotEqual(result["commitment"], "requested")
        self.assertEqual(
            graph["v60_predicate_morphology"]["predicate_force"], "declarative"
        )
        self.assertFalse(graph["direct_focus_request"])

    def test_implementation_contains_no_holdout_ids_or_exact_failure_sentences(self):
        source = (ROOT / "predicate_morphology_v60.py").read_text(encoding="utf-8")
        for forbidden in (
            "v59h_",
            "87104",
            "89563",
            "96980",
            "10550376",
            "彼女は微笑んで私を迎えてくれた",
            "トムが私のジョークで笑ってくれた",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
