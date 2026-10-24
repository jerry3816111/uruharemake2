import json
import tempfile
import unittest
from pathlib import Path

import uruha_adaptive_person_model as uapm
import uruha_functional_understanding as ufu
import uruha_personhood_loop as upl
from uruha_memory_observatory import collect_cognitive_graph


AMBIGUOUS_INPUT = "我從早上就一直坐不住，腦子停不下來。"
TEASE_FEEDBACK = "不是要方法啦，我是在等你吐槽我，平常不是都會互相吐槽嗎？"


def decision_for(text, model, turn_index):
    hypothesis = ufu.build_user_mental_state_hypothesis(
        text,
        actual_signal={"actual_intent": "chat", "actual_valence": 0.0},
        appraisal={},
        attention_frame={},
        turn_index=turn_index,
        calibration_state={},
    )
    pragmatics = upl.build_human_pragmatic_understanding(
        text,
        hypothesis=hypothesis,
        turn_index=turn_index,
    )
    state = uapm.build_current_state(
        text,
        pragmatics,
        hypothesis,
        {},
        model,
        turn_index=turn_index,
    )
    return state, uapm.decide_response(state, model)


class AdaptivePersonModelM16Tests(unittest.TestCase):
    def test_ambiguous_correction_and_reuse_changes_real_response_policy(self):
        model = uapm.empty_model()

        model, first_feedback = uapm.observe_next_turn(model, AMBIGUOUS_INPUT, 1)
        _state1, decision1 = decision_for(AMBIGUOUS_INPUT, model, 1)
        self.assertEqual(first_feedback["status"], "not_available")
        self.assertEqual(decision1["selected"]["policy_id"], "calibrate_need")
        model = uapm.set_pending_prediction(model, decision1, 1)

        model, correction = uapm.observe_next_turn(model, TEASE_FEEDBACK, 2)
        _state2, decision2 = decision_for(TEASE_FEEDBACK, model, 2)
        self.assertEqual(correction["status"], "contradicted")
        self.assertEqual(correction["previous_policy_id"], "calibrate_need")
        self.assertEqual(decision2["selected"]["policy_id"], "playful_tease")
        self.assertIn("humor_invitation", {row["atom"] for row in correction["atom_changes"]})
        model = uapm.set_pending_prediction(model, decision2, 2)

        model, _uncertain = uapm.observe_next_turn(model, AMBIGUOUS_INPUT, 3)
        state3, decision3 = decision_for(AMBIGUOUS_INPUT, model, 3)
        self.assertEqual(decision3["selected"]["policy_id"], "playful_tease")
        self.assertIn("humor_invitation", state3["learned_atoms_used"])
        self.assertEqual(
            state3["atoms"]["uncertainty"]["status"],
            "bounded_by_verified_interaction_prior",
        )

    def test_support_contradiction_and_uncertainty_have_distinct_updates(self):
        model = uapm.empty_model()
        _state, decision = decision_for("我需要一個現在能做的方法，怎麼停？", model, 1)
        self.assertEqual(decision["selected"]["policy_id"], "solve_regulation")
        model = uapm.set_pending_prediction(model, decision, 1)

        supported_model, supported = uapm.observe_next_turn(model, "對就是這樣，先給我方法。", 2)
        self.assertEqual(supported["status"], "supported")
        self.assertGreater(
            supported_model["policy_reliability"]["solve_regulation"]["mean"],
            model["policy_reliability"]["solve_regulation"]["mean"],
        )

        _state2, decision2 = decision_for("我需要一個現在能做的方法，怎麼停？", supported_model, 2)
        supported_model = uapm.set_pending_prediction(supported_model, decision2, 2)
        uncertain_model, uncertain = uapm.observe_next_turn(supported_model, "今天外面下雨。", 3)
        self.assertEqual(uncertain["status"], "uncertain")
        self.assertEqual(
            uncertain_model["policy_reliability"]["solve_regulation"]["alpha"],
            supported_model["policy_reliability"]["solve_regulation"]["alpha"],
        )
        self.assertEqual(
            uncertain_model["policy_reliability"]["solve_regulation"]["beta"],
            supported_model["policy_reliability"]["solve_regulation"]["beta"],
        )

    def test_negated_policy_cue_is_a_correction_not_support(self):
        model = uapm.empty_model()
        _state, tease = decision_for(TEASE_FEEDBACK, model, 1)
        self.assertEqual(tease["selected"]["policy_id"], "playful_tease")
        model = uapm.set_pending_prediction(model, tease, 1)

        corrected_model, feedback = uapm.observe_next_turn(
            model,
            "不是要吐槽，是真的想要方法。",
            2,
        )
        _state2, corrected = decision_for("不是要吐槽，是真的想要方法。", corrected_model, 2)

        self.assertEqual(feedback["status"], "contradicted")
        self.assertEqual(feedback["explicit_target_policy"], "solve_regulation")
        self.assertEqual(corrected["selected"]["policy_id"], "solve_regulation")
        self.assertLess(corrected_model["learned_atoms"]["humor_invitation"]["value"], 0.1)
        self.assertEqual(
            corrected_model["policy_reliability"]["playful_tease"]["contradicted"],
            1,
        )

    def test_persistence_survives_reload_without_raw_dialogue(self):
        model = uapm.empty_model()
        _state, decision = decision_for(AMBIGUOUS_INPUT, model, 1)
        model = uapm.set_pending_prediction(model, decision, 1)
        model, correction = uapm.observe_next_turn(model, TEASE_FEEDBACK, 2)
        self.assertEqual(correction["status"], "contradicted")

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "adaptive.json"
            uapm.save_model(path, model)
            raw = path.read_text(encoding="utf-8")
            reloaded, trace = uapm.load_model(path)

        self.assertEqual(trace["status"], "loaded")
        self.assertNotIn(AMBIGUOUS_INPUT, raw)
        self.assertNotIn(TEASE_FEEDBACK, raw)
        self.assertFalse(json.loads(raw)["raw_dialogue_persisted"])
        self.assertIn("humor_invitation", reloaded["learned_atoms"])
        self.assertEqual(
            reloaded["policy_reliability"]["calibrate_need"]["contradicted"],
            1,
        )

    def test_safety_and_factual_memory_plans_are_never_overridden(self):
        model = uapm.empty_model()
        _state, decision = decision_for(TEASE_FEEDBACK, model, 1)
        self.assertEqual(decision["selected"]["policy_id"], "playful_tease")

        crisis, crisis_trace = uapm.apply_decision_to_plan(
            {"intent": "crisis_support", "scene": "support", "core_message_jp": "一人になるな。"},
            decision,
        )
        recall, recall_trace = uapm.apply_decision_to_plan(
            {
                "intent": "profile_grounded_recall",
                "scene": "casual",
                "core_message_jp": "いちごミルク。",
                "profile_grounding_shadow": {"schema": "test"},
            },
            decision,
        )

        self.assertFalse(crisis_trace["applied"])
        self.assertEqual(crisis["core_message_jp"], "一人になるな。")
        self.assertFalse(recall_trace["applied"])
        self.assertEqual(recall["core_message_jp"], "いちごミルク。")

    def test_decision_rewrites_the_actual_plan_content_not_only_debug_trace(self):
        model = uapm.empty_model()
        _state, decision = decision_for(TEASE_FEEDBACK, model, 1)
        plan, trace = uapm.apply_decision_to_plan(
            {"intent": "chat", "scene": "casual", "core_message_jp": "元の返事"},
            decision,
        )
        self.assertTrue(trace["applied"])
        self.assertEqual(plan["desired_response_policy_m16"], "playful_tease")
        self.assertEqual(plan["core_message_jp"], uapm.POLICIES["playful_tease"]["core_message_jp"])

    def test_correction_surface_must_perform_the_newly_selected_action(self):
        model = uapm.empty_model()
        _state, decision = decision_for(TEASE_FEEDBACK, model, 2)
        plan, _trace = uapm.apply_decision_to_plan(
            {
                "intent": "pragmatic_revision",
                "scene": "casual",
                "core_message_jp": "あ、そっちか。さっきは読みすぎた。今の言い方で直す。",
            },
            decision,
        )
        reply, surface = uapm.ensure_decision_reaches_visible_surface(
            "あ、そっちか。さっきは読みすぎた。今の言い方で直す。",
            plan,
        )
        self.assertTrue(surface["changed"])
        self.assertTrue(surface["policy_performed"])
        self.assertIn("二十四時間営業", reply)

        explicit, explicit_trace = uapm.ensure_decision_reaches_visible_surface(
            "ちょっと待てって。",
            uapm.apply_decision_to_plan(
                {"intent": "chat", "scene": "casual", "core_message_jp": "元の返事"},
                decision,
            )[0],
        )
        self.assertIn("二十四時間営業", explicit)
        self.assertTrue(explicit_trace["policy_commitment_required"])
        self.assertTrue(explicit_trace["changed"])

        ordinary_decision = dict(decision)
        ordinary_decision["state"] = dict(decision.get("state") or {})
        ordinary_decision["state"]["activation_reasons"] = []
        ordinary, ordinary_trace = uapm.ensure_decision_reaches_visible_surface(
            "ちょっと待てって。",
            uapm.apply_decision_to_plan(
                {"intent": "chat", "scene": "casual", "core_message_jp": "元の返事"},
                ordinary_decision,
            )[0],
        )
        self.assertEqual(ordinary, "ちょっと待てって。")
        self.assertFalse(ordinary_trace["changed"])

    def test_runtime_graph_shows_feedback_state_candidates_prediction_and_persistence(self):
        blackboard = [
            {"stage": "learn", "label": "adaptive_person_feedback_update_m16", "payload": {"schema": uapm.FEEDBACK_SCHEMA, "status": "contradicted", "previous_policy_id": "calibrate_need"}},
            {"stage": "other_model", "label": "desired_response_state_m16", "payload": {"schema": uapm.STATE_SCHEMA, "active": True, "learned_atoms_used": ["humor_invitation"]}},
            {"stage": "select", "label": "desired_response_candidates_m16", "payload": {"schema": "uruha_desired_response_candidates_m16", "candidates": [{"policy_id": "playful_tease"}], "utility_margin": 0.1}},
            {"stage": "predict", "label": "desired_response_prediction_m16", "payload": {"schema": uapm.DECISION_SCHEMA, "status": "applied", "selected": {"policy_id": "playful_tease"}}},
            {"stage": "write", "label": "adaptive_person_persistence_m16", "payload": {"schema": "uruha_adaptive_person_persistence_m16", "status": "saved", "revision_count": 1}},
            {"stage": "surface", "label": "adaptive_person_surface_commitment_m16", "payload": {"schema": "uruha_adaptive_person_surface_commitment_m16", "policy_id": "playful_tease", "policy_performed": True}},
        ]
        graph = collect_cognitive_graph(
            {"user_text": TEASE_FEEDBACK, "reply": "朝から脳内だけ二十四時間営業かよ。", "runtime_trace": {"blackboard": blackboard}}
        )
        labels = {node["label"] for node in graph["nodes"]}
        self.assertTrue(
            {
                "adaptive_person_feedback_update_m16",
                "desired_response_state_m16",
                "desired_response_candidates_m16",
                "desired_response_prediction_m16",
                "adaptive_person_persistence_m16",
                "adaptive_person_surface_commitment_m16",
            }.issubset(labels)
        )


if __name__ == "__main__":
    unittest.main()
