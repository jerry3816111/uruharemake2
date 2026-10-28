import json
import tempfile
import unittest
from pathlib import Path

import uruha_adaptive_person_model as uapm
from test_adaptive_person_model_m16 import (
    AMBIGUOUS_INPUT,
    TEASE_FEEDBACK,
    decision_for,
)


TASK_INPUT = "我明天要交報告，進度做不完，現在該先做什麼？"
BODY_INPUT = "我頭痛而且整晚沒睡，現在很不舒服。"


def learn_tease_for_arousal():
    model = uapm.empty_model()
    _state, first = decision_for(AMBIGUOUS_INPUT, model, 1)
    model = uapm.set_pending_prediction(model, first, 1)
    model, feedback = uapm.observe_next_turn(model, TEASE_FEEDBACK, 2)
    return model, feedback


class ContextScopedAdaptationM17Tests(unittest.TestCase):
    def test_feedback_is_bound_to_previous_context_not_correction_wording(self):
        model, feedback = learn_tease_for_arousal()
        scope = feedback["context_scope"]

        self.assertEqual(feedback["status"], "contradicted")
        self.assertEqual(scope["domain"], "arousal_regulation")
        self.assertIn(scope["scope_id"], model["scoped_atoms"])
        self.assertNotIn(
            "relationship_play:play_invitation:familiar",
            model["scoped_atoms"],
        )

    def test_same_context_reuses_correction_but_unrelated_task_does_not(self):
        model, _feedback = learn_tease_for_arousal()

        same_state, same_decision = decision_for(AMBIGUOUS_INPUT, model, 3)
        task_state, task_decision = decision_for(TASK_INPUT, model, 3)
        body_state, body_decision = decision_for(BODY_INPUT, model, 3)

        self.assertEqual(same_decision["selected"]["policy_id"], "playful_tease")
        self.assertIn("humor_invitation", same_state["learned_atoms_used"])
        self.assertEqual(task_state["context_scope"]["domain"], "task_execution")
        self.assertEqual(task_state["learned_atoms_used"], [])
        self.assertEqual(task_decision["selected"]["policy_id"], "solve_regulation")
        self.assertEqual(body_state["context_scope"]["domain"], "physical_wellbeing")
        self.assertEqual(body_state["learned_atoms_used"], [])
        self.assertEqual(body_decision["selected"]["policy_id"], "care_physiology")

    def test_withdrawal_revises_only_the_original_scope(self):
        model, _feedback = learn_tease_for_arousal()
        _state, tease = decision_for(AMBIGUOUS_INPUT, model, 3)
        model = uapm.set_pending_prediction(model, tease, 3)

        model, withdrawal = uapm.observe_next_turn(
            model,
            "不是要吐槽，是真的想要方法。",
            4,
        )
        revised_state, revised = decision_for(AMBIGUOUS_INPUT, model, 5)
        task_state, _task = decision_for(TASK_INPUT, model, 5)

        self.assertEqual(withdrawal["status"], "contradicted")
        self.assertEqual(withdrawal["context_scope"]["domain"], "arousal_regulation")
        self.assertEqual(revised["selected"]["policy_id"], "solve_regulation")
        self.assertLess(revised_state["atoms"]["humor_invitation"]["value"], 0.2)
        self.assertGreater(revised_state["atoms"]["solution_request"]["value"], 0.7)
        self.assertEqual(task_state["learned_atoms_used"], [])

    def test_topic_shift_is_not_mislearned_as_feedback_about_previous_reply(self):
        model, _feedback = learn_tease_for_arousal()
        _play_state, play_decision = decision_for(TEASE_FEEDBACK, model, 3)
        model = uapm.set_pending_prediction(model, play_decision, 3)

        model, topic_shift = uapm.observe_next_turn(model, TASK_INPUT, 4)

        relationship_scope = "relationship_play:play_invitation:familiar"
        learned = (model.get("scoped_atoms", {}).get(relationship_scope) or {}).get("atoms") or {}
        self.assertEqual(topic_shift["status"], "uncertain")
        self.assertFalse(topic_shift["feedback_linked_to_previous_prediction"])
        self.assertEqual(topic_shift["atom_changes"], [])
        self.assertNotIn("solution_request", learned)

    def test_scope_expires_by_revision_age(self):
        model, _feedback = learn_tease_for_arousal()
        model["revision_count"] += uapm.DEFAULT_SCOPE_TTL_REVISIONS + 1

        state, decision = decision_for(AMBIGUOUS_INPUT, model, 40)

        self.assertEqual(state["learned_atoms_used"], [])
        self.assertTrue(
            any(row["reason"] == "scope_expired" for row in state["learned_atoms_rejected"])
        )
        self.assertEqual(decision["selected"]["policy_id"], "calibrate_need")

    def test_restart_keeps_scope_without_raw_dialogue(self):
        model, feedback = learn_tease_for_arousal()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "adaptive.json"
            uapm.save_model(path, model)
            raw = path.read_text(encoding="utf-8")
            reloaded, load_trace = uapm.load_model(path)

        state, decision = decision_for(AMBIGUOUS_INPUT, reloaded, 1)
        payload = json.loads(raw)
        self.assertEqual(load_trace["status"], "loaded")
        self.assertEqual(payload["schema"], uapm.MODEL_SCHEMA)
        self.assertNotIn(AMBIGUOUS_INPUT, raw)
        self.assertNotIn(TEASE_FEEDBACK, raw)
        self.assertEqual(
            state["context_scope"]["scope_id"],
            feedback["context_scope"]["scope_id"],
        )
        self.assertEqual(decision["selected"]["policy_id"], "playful_tease")

    def test_legacy_unscoped_atoms_are_retained_but_not_silently_applied(self):
        legacy = uapm.empty_model()
        legacy["schema"] = uapm.LEGACY_MODEL_SCHEMA
        legacy["learned_atoms"] = {
            "humor_invitation": {
                "value": 0.99,
                "confidence": 0.99,
                "source_kind": "legacy_explicit_feedback",
                "evidence_digest": "deadbeef",
                "updated_turn": 9,
                "contradiction_count": 0,
            }
        }

        migrated = uapm._normalise_model(legacy)
        state, decision = decision_for(AMBIGUOUS_INPUT, migrated, 10)

        self.assertEqual(migrated["legacy_unscoped_atom_count"], 1)
        self.assertEqual(state["scope_match"]["legacy_unscoped_atoms_ignored"], 1)
        self.assertEqual(state["learned_atoms_used"], [])
        self.assertEqual(decision["selected"]["policy_id"], "calibrate_need")


if __name__ == "__main__":
    unittest.main()
