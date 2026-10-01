import json
import tempfile
import unittest
from pathlib import Path

import uruha_adaptive_person_model as uapm
from uruha_memory_observatory import collect_cognitive_graph, render_memory_observatory
from test_adaptive_person_model_m16 import (
    AMBIGUOUS_INPUT,
    TEASE_FEEDBACK,
    decision_for,
)
from test_personhood_loop_v2_13 import _IsolatedContractBrain


NEAR_AROUSAL = "像平常一樣，我腦袋又停不下來了。"
EXPLICIT_SOLUTION = "像平常一樣，我腦袋又停不下來了，現在該怎麼停？"
PHYSICAL_OVERRIDE = "我頭痛而且整晚沒睡，像平常一樣腦子又停不下來。"


def learn_arousal_tease():
    model = uapm.empty_model()
    _state, first = decision_for(AMBIGUOUS_INPUT, model, 1)
    model = uapm.set_pending_prediction(model, first, 1)
    model, feedback = uapm.observe_next_turn(model, TEASE_FEEDBACK, 2)
    return model, feedback


class HierarchicalAdaptivePolicyM18Tests(unittest.TestCase):
    def test_near_context_uses_domain_fallback_and_varied_japanese(self):
        model, _feedback = learn_arousal_tease()

        state3, decision3 = decision_for(NEAR_AROUSAL, model, 3)
        state4, decision4 = decision_for(NEAR_AROUSAL, model, 4)

        self.assertEqual(state3["scope_match"]["status"], "domain")
        self.assertEqual(decision3["selected"]["policy_id"], "playful_tease")
        self.assertEqual(decision4["selected"]["policy_id"], "playful_tease")
        self.assertNotEqual(
            decision3["selected"]["realization"]["variant_id"],
            decision4["selected"]["realization"]["variant_id"],
        )
        self.assertNotEqual(
            decision3["selected"]["core_message_jp"],
            decision4["selected"]["core_message_jp"],
        )
        self.assertTrue(
            all(
                row["level"] == "domain"
                for row in state3["scope_match"]["used"]
            )
        )

    def test_current_solution_request_blocks_conflicting_domain_prior(self):
        model, _feedback = learn_arousal_tease()

        state, decision = decision_for(EXPLICIT_SOLUTION, model, 3)

        self.assertEqual(state["scope_match"]["status"], "domain")
        self.assertEqual(decision["selected"]["policy_id"], "solve_regulation")
        self.assertTrue(
            any(
                row.get("atom") == "solution_request"
                and row.get("reason") == "current_explicit_cue_conflicts_with_prior"
                for row in state["learned_atoms_rejected"]
            )
        )
        self.assertGreater(
            decision["selected"]["response_dimensions"]["values"]["actionability"],
            0.85,
        )

    def test_physical_evidence_precedes_humor_transfer(self):
        model, _feedback = learn_arousal_tease()

        state, decision = decision_for(PHYSICAL_OVERRIDE, model, 3)

        self.assertEqual(state["context_scope"]["domain"], "physical_wellbeing")
        self.assertEqual(state["learned_atoms_used"], [])
        self.assertEqual(decision["selected"]["policy_id"], "care_physiology")
        dimensions = decision["selected"]["response_dimensions"]["values"]
        self.assertGreater(dimensions["care"], 0.85)
        self.assertLess(dimensions["humor"], 0.10)

    def test_relationship_fallback_transfers_style_not_content_need(self):
        model = uapm.empty_model()
        _state, tease = decision_for("像平常一樣吐槽我吧。", model, 1)
        model = uapm.set_pending_prediction(model, tease, 1)
        model, supported = uapm.observe_next_turn(model, "對就是這樣。", 2)
        self.assertEqual(supported["status"], "supported")
        self.assertEqual(len(supported["dimension_changes"]), 6)

        state, decision = decision_for(
            "像平常一樣，結果終於要公布了，我超期待。",
            model,
            3,
        )

        self.assertEqual(state["scope_match"]["status"], "relationship")
        self.assertEqual(decision["selected"]["policy_id"], "share_arousal")
        self.assertEqual(
            set(state["learned_dimension_priors"]),
            {"directness", "humor", "distance"},
        )
        dimensions = decision["selected"]["response_dimensions"]["values"]
        self.assertGreater(dimensions["humor"], 0.38)
        self.assertLess(dimensions["distance"], 0.18)
        self.assertNotEqual(decision["selected"]["policy_id"], "playful_tease")

    def test_generic_support_then_new_topic_is_segmented(self):
        model = uapm.empty_model()
        _state, tease = decision_for("像平常一樣吐槽我吧。", model, 1)
        model = uapm.set_pending_prediction(model, tease, 1)

        model, feedback = uapm.observe_next_turn(
            model,
            "Exactly, that's right. Like usual, I'm excited that the result is about to come out.",
            2,
        )

        self.assertEqual(feedback["status"], "supported")
        self.assertTrue(feedback["current_request_separated_from_feedback"])
        self.assertEqual(feedback["atom_changes"], [])
        self.assertEqual(len(feedback["dimension_changes"]), 6)
        state, decision = decision_for(
            "Exactly, that's right. Like usual, I'm excited that the result is about to come out.",
            model,
            2,
        )
        self.assertEqual(state["scope_match"]["status"], "relationship")
        self.assertEqual(decision["selected"]["policy_id"], "share_arousal")

    def test_indirect_revision_updates_previous_scope_and_dimensions(self):
        model = uapm.empty_model()
        _state, solve = decision_for("我現在需要一個方法，怎麼辦？", model, 1)
        model = uapm.set_pending_prediction(model, solve, 1)

        model, feedback = uapm.observe_next_turn(
            model,
            "其實我只想你先聽我講完。",
            2,
        )

        self.assertTrue(feedback["feedback_linked_to_previous_prediction"])
        self.assertEqual(feedback["feedback_linkage_reason"], "indirect_revision_cue")
        self.assertEqual(feedback["status"], "contradicted")
        self.assertEqual(feedback["explicit_target_policy"], "listen_presence")
        self.assertEqual(len(feedback["dimension_changes"]), 6)
        self.assertGreater(
            model["scoped_atoms"][feedback["context_scope"]["scope_id"]]
            ["dimensions"]["listening"]["value"],
            0.9,
        )

    def test_hierarchical_prior_expires_and_does_not_reactivate(self):
        model, _feedback = learn_arousal_tease()
        model["revision_count"] += uapm.DEFAULT_SCOPE_TTL_REVISIONS + 1

        state, decision = decision_for(NEAR_AROUSAL, model, 40)

        self.assertEqual(state["learned_atoms_used"], [])
        self.assertTrue(
            any(
                row.get("reason") == "scope_expired"
                for row in state["scope_match"]["rejected"]
            )
        )
        self.assertNotEqual(
            (decision.get("selected") or {}).get("policy_id"),
            "playful_tease",
        )

    def test_restart_keeps_dimensions_without_raw_dialogue(self):
        model, _feedback = learn_arousal_tease()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "adaptive.json"
            uapm.save_model(path, model)
            raw = path.read_text(encoding="utf-8")
            reloaded, trace = uapm.load_model(path)

        state, decision = decision_for(NEAR_AROUSAL, reloaded, 3)
        payload = json.loads(raw)
        self.assertEqual(trace["status"], "loaded")
        self.assertEqual(payload["schema"], uapm.MODEL_SCHEMA)
        self.assertEqual(payload["version"], uapm.STORE_VERSION)
        self.assertNotIn(AMBIGUOUS_INPUT, raw)
        self.assertNotIn(TEASE_FEEDBACK, raw)
        self.assertTrue(state["learned_dimension_priors"])
        self.assertEqual(decision["selected"]["policy_id"], "playful_tease")

    def test_graph_exposes_hierarchy_gate_dimensions_and_surface(self):
        blackboard = [
            {
                "stage": "learn",
                "label": "adaptive_person_feedback_update_m18",
                "payload": {
                    "schema": uapm.FEEDBACK_SCHEMA,
                    "status": "contradicted",
                    "previous_policy_id": "calibrate_need",
                    "context_scope": {"domain": "arousal_regulation"},
                },
            },
            {
                "stage": "other_model",
                "label": "adaptive_context_scope_m18",
                "payload": {
                    "schema": uapm.SCOPE_SCHEMA,
                    "domain": "arousal_regulation",
                    "interaction_kind": "state_disclosure",
                    "relationship_band": "familiar",
                },
            },
            {
                "stage": "other_model",
                "label": "adaptive_scope_hierarchy_m18",
                "payload": {
                    "schema": uapm.HIERARCHY_SCHEMA,
                    "status": "domain",
                    "used": [{"name": "humor_invitation", "level": "domain"}],
                    "negative_transfer_gate_count": 1,
                },
            },
            {
                "stage": "other_model",
                "label": "desired_response_state_m18",
                "payload": {
                    "schema": uapm.STATE_SCHEMA,
                    "active": True,
                    "learned_atoms_used": ["humor_invitation"],
                    "context_scope": {"domain": "arousal_regulation"},
                },
            },
            {
                "stage": "select",
                "label": "desired_response_candidates_m18",
                "payload": {
                    "schema": "uruha_desired_response_candidates_m18",
                    "candidates": [{"policy_id": "playful_tease"}],
                    "utility_margin": 0.2,
                },
            },
            {
                "stage": "select",
                "label": "adaptive_response_dimensions_m18",
                "payload": {
                    "schema": uapm.DIMENSION_SCHEMA,
                    "response_dimensions": {
                        "values": {"humor": 0.92, "directness": 0.88}
                    },
                },
            },
            {
                "stage": "predict",
                "label": "desired_response_prediction_m18",
                "payload": {
                    "schema": uapm.DECISION_SCHEMA,
                    "status": "applied",
                    "selected": {"policy_id": "playful_tease"},
                },
            },
            {
                "stage": "surface",
                "label": "adaptive_person_surface_commitment_m18",
                "payload": {
                    "schema": "uruha_adaptive_person_surface_commitment_m18",
                    "policy_id": "playful_tease",
                    "policy_performed": True,
                },
            },
        ]
        result = {
            "user_text": NEAR_AROUSAL,
            "reply": "また脳内会議だけ終電逃してんのかよ。",
            "runtime_trace": {"blackboard": blackboard},
        }

        graph = collect_cognitive_graph(result)
        labels = {node["label"] for node in graph["nodes"]}
        html = render_memory_observatory(result)

        self.assertTrue(
            {
                "adaptive_scope_hierarchy_m18",
                "adaptive_response_dimensions_m18",
                "desired_response_prediction_m18",
                "adaptive_person_surface_commitment_m18",
            }.issubset(labels)
        )
        self.assertIn("HIERARCHICAL ADAPTIVE MODEL · M18", html)
        self.assertIn("負遷移", html)

    def test_real_runtime_transfers_then_blocks_without_planner_regression(self):
        brain = _IsolatedContractBrain()
        first = brain.run_turn_debug(AMBIGUOUS_INPUT)
        corrected = brain.run_turn_debug(TEASE_FEEDBACK)
        transferred = brain.run_turn_debug(NEAR_AROUSAL)
        solution = brain.run_turn_debug(EXPLICIT_SOLUTION)
        physical = brain.run_turn_debug(PHYSICAL_OVERRIDE)

        self.assertEqual(first["logic"]["desired_response_policy_m18"], "calibrate_need")
        self.assertEqual(corrected["logic"]["desired_response_policy_m18"], "playful_tease")
        self.assertEqual(transferred["logic"]["desired_response_policy_m18"], "playful_tease")
        self.assertEqual(
            transferred["runtime_trace"]["adaptive_scope_hierarchy_m18"]["status"],
            "domain",
        )
        self.assertEqual(solution["logic"]["desired_response_policy_m18"], "solve_regulation")
        self.assertEqual(physical["logic"]["desired_response_policy_m18"], "care_physiology")
        self.assertIn("脳内", corrected["reply"])
        self.assertIn("脳内", transferred["reply"])
        self.assertNotIn("脳内", solution["reply"])
        self.assertNotIn("脳内", physical["reply"])
        self.assertEqual(brain.left_brain.think_calls, 1)
        labels = {row["label"] for row in transferred["runtime_trace"]["blackboard"]}
        self.assertTrue(
            {
                "adaptive_scope_hierarchy_m18",
                "adaptive_response_dimensions_m18",
                "desired_response_prediction_m18",
                "adaptive_person_surface_commitment_m18",
            }.issubset(labels)
        )

    def test_verified_domain_reuse_keeps_low_margin_fast_path(self):
        brain = _IsolatedContractBrain()
        plan, trace = brain._build_adaptive_planner_fast_path_m17(
            {
                "seed_plan": {
                    "intent": "chat",
                    "scene": "casual",
                    "cognitive_mode": "direct",
                }
            },
            {"route": "high_road"},
            {
                "active": True,
                "learned_atoms_used": ["humor_invitation"],
                "scope_match": {"status": "domain"},
                "context_scope": {"domain": "arousal_regulation"},
            },
            {
                "utility_margin": 0.0338,
                "selected": {
                    "policy_id": "playful_tease",
                    "instruction": "短く軽くいじる",
                    "core_message_jp": "また脳内会議だけ終電逃してんのかよ。",
                },
            },
        )

        self.assertIsNotNone(plan)
        self.assertTrue(trace["applied"])
        self.assertEqual(trace["minimum_utility_margin"], 0.03)


if __name__ == "__main__":
    unittest.main()
