#!/usr/bin/env python3

import json
import unittest
from pathlib import Path

from action_candidate_perception_v47 import load_v47_anchor_ontology
from event_role_governor_v59 import resolve_target_state
from grounded_commitment_classifier_v42 import ground_supported_targets


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "relation_safety_state_v58_holdout_preregistration.json"


class EventRoleGovernorV59Tests(unittest.TestCase):
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

    def test_embedded_speech_request_governs_telling_not_the_action(self):
        cases = {
            "彼がどんなふうにあなたに微笑みかけたのか教えてください。": "expression.happy",
            "彼が手を振ったのか教えてください。": "motion.wave",
            "彼女が右を向いたのか説明してください。": "gaze.right",
        }
        for text, target_id in cases.items():
            with self.subTest(text=text):
                state = self._state(text, target_id)
                graph = state["v59_event_role_graph"]
                self.assertEqual(state["commitment"], "mentioned")
                self.assertEqual(graph["directive_governor"], "speech_act")
                self.assertIn("embedded_speech_content", graph["relation_types"])

    def test_third_party_habit_is_description(self):
        cases = {
            "彼女は、いつも笑顔で周りの人を温かい気持ちにさせてくれる。": "expression.happy",
            "彼は毎朝手を振ってくれる。": "motion.wave",
            "トムはよく右を向いてくれる。": "gaze.right",
        }
        for text, target_id in cases.items():
            with self.subTest(text=text):
                state = self._state(text, target_id)
                graph = state["v59_event_role_graph"]
                self.assertEqual(state["commitment"], "mentioned")
                self.assertEqual(graph["event_owner"], "third_party")
                self.assertEqual(graph["event_time"], "habitual")
                self.assertIn(
                    "third_party_habitual_description", graph["relation_types"]
                )

    def test_past_third_party_experience_is_description(self):
        cases = {
            "昔の友人に会ったら、昔と変わらない笑顔で話しかけてくれて嬉しかった。": "expression.happy",
            "昨日、先生に会ったら手を振ってくれて嬉しかった。": "motion.wave",
        }
        for text, target_id in cases.items():
            with self.subTest(text=text):
                state = self._state(text, target_id)
                graph = state["v59_event_role_graph"]
                self.assertEqual(state["commitment"], "mentioned")
                self.assertEqual(graph["event_owner"], "inferred_third_party")
                self.assertEqual(graph["event_time"], "past")
                self.assertIn(
                    "past_experiential_description", graph["relation_types"]
                )

    def test_direct_focus_requests_remain_executable(self):
        cases = {
            "笑ってください。": "expression.happy",
            "昨日みたいに笑ってください。": "expression.happy",
            "彼女が来たら、いつも笑ってください。": "expression.happy",
            "彼女に微笑みかけてください。": "expression.happy",
            "微笑みかけてから説明してください。": "expression.happy",
            "いつも笑顔にしてください。": "expression.happy",
            "彼に手を振ってください。": "motion.wave",
            "撮影を始めるので今は左を向いてください。": "gaze.left",
        }
        for text, target_id in cases.items():
            with self.subTest(text=text):
                state = self._state(text, target_id)
                graph = state["v59_event_role_graph"]
                self.assertEqual(state["commitment"], "requested")
                self.assertTrue(graph["direct_focus_request"])
                self.assertEqual(graph["directive_governor"], "focus_event")
                self.assertEqual(graph["event_time"], "current")
                self.assertEqual(graph["relation_types"], [])

    def test_existing_v58_safety_states_are_not_reinterpreted(self):
        cases = {
            "先生が手を振ってくださいました。": ("motion.wave", "mentioned"),
            "左か右を向いて。": ("gaze.left", "ambiguous"),
            "笑ってほしい気もするけど、今は決められない。": (
                "expression.happy",
                "ambiguous",
            ),
        }
        for text, (target_id, expected) in cases.items():
            with self.subTest(text=text):
                state = self._state(text, target_id)
                self.assertEqual(state["commitment"], expected)
                self.assertNotIn("v59_correction", state)

    def test_graph_contains_only_answer_free_role_evidence(self):
        state = self._state(
            "彼がどんなふうにあなたに微笑みかけたのか教えてください。",
            "expression.happy",
        )
        graph = state["v59_event_role_graph"]
        self.assertEqual(
            set(graph),
            {
                "focus_target_id",
                "event_owner",
                "directive_governor",
                "event_time",
                "direct_focus_request",
                "relations",
                "relation_types",
            },
        )
        serialized = json.dumps(graph, ensure_ascii=False)
        for forbidden in ("expected", "gold", "case_id", "sentence_id"):
            self.assertNotIn(forbidden, serialized)


if __name__ == "__main__":
    unittest.main()
