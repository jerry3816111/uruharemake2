import json
import unittest

from uruha_brain_mac import RightBrain


class RightBrainForbiddenConflictProjectionV87Tests(unittest.TestCase):
    def setUp(self):
        self.rightbrain = RightBrain(load_model=False)
        self.logic = {
            "core_message_jp": "何を言っているのか聞き返す。",
            "must_avoid": ["何を言ってい", "そうなんだ", "私", "危険な指示"],
            "constraints": {"max_chars": 40},
            "human_speech_plan": {
                "content_units": ["何を言っているのか聞く"],
                "grounding_terms": [],
                "forbidden_repetition": {
                    "recent_openings": ["何を言ってい", "私"],
                    "avoid_generic_frames": ["そうなんだ"],
                },
            },
        }

    def test_default_preserves_legacy_forbidden_contract(self):
        self.assertFalse(self.rightbrain.forbidden_conflict_projection_enabled)
        self.assertEqual(
            self.rightbrain._model_surface_forbidden_markers(self.logic),
            self.logic["must_avoid"],
        )

    def test_enabled_drops_only_stale_recent_opening_conflict(self):
        self.rightbrain.forbidden_conflict_projection_enabled = True
        effective = self.rightbrain._model_surface_forbidden_markers(self.logic)
        self.assertNotIn("何を言ってい", effective)
        self.assertIn("そうなんだ", effective)
        self.assertIn("私", effective)
        self.assertIn("危険な指示", effective)
        self.assertEqual(
            self.logic["model_surface_forbidden_projection"]["dropped_stale_recent_opening_count"],
            1,
        )

    def test_payload_gate_and_selector_share_effective_contract(self):
        self.rightbrain.forbidden_conflict_projection_enabled = True
        payload = json.loads(
            self.rightbrain._build_model_surface_payload(
                self.logic,
                {"mood": 0, "trust": 60},
                40,
            )
        )
        selector = self.rightbrain._selector_contract_payload(self.logic)
        self.assertEqual(payload["forbidden_markers"], selector["forbidden_markers"])
        self.assertNotIn("何を言ってい", payload["forbidden_markers"])
        reasons = self.rightbrain._model_candidate_rejection_reasons(
            "何を言っているの？",
            self.logic,
            40,
        )
        self.assertNotIn("must_avoid_violation", reasons)

    def test_nonconflicting_recent_opening_remains_forbidden(self):
        self.rightbrain.forbidden_conflict_projection_enabled = True
        logic = {
            **self.logic,
            "core_message_jp": "別の話題に答える。",
            "human_speech_plan": {
                **self.logic["human_speech_plan"],
                "content_units": ["別の話題に答える"],
            },
        }
        self.assertIn(
            "何を言ってい",
            self.rightbrain._model_surface_forbidden_markers(logic),
        )


if __name__ == "__main__":
    unittest.main()
