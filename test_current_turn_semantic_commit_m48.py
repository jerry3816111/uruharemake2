from copy import deepcopy

import uruha_adaptive_person_model as uapm
import uruha_web_ui as web
from uruha_memory_observatory import collect_cognitive_graph


BASE_CORE = "第三版まで来て、また注釈かよ。"
POLICY_CORE = "寝てないのか、考え事で止まんないのか、まずそこだけどっち？"


def _decision(domain="task_execution", *, explicit=False, correction=False):
    return {
        "prediction_id": "m48-test",
        "utility_margin": 0.2,
        "selected": {
            "policy_id": "calibrate_need",
            "core_message_jp": POLICY_CORE,
            "instruction": "短く確認する",
            "response_dimensions": {"values": {"listening": 0.8}},
            "realization": {"schema": "test_realization"},
        },
        "state": {
            "context_scope": {"domain": domain},
            "activation_reasons": [
                "explicit_current_turn_desired_response_or_state_cue"
            ],
        },
        "explicit_desired_response_m25": {
            "schema": uapm.EXPLICIT_DESIRED_RESPONSE_SCHEMA_M25,
            "authoritative": explicit,
            "negated_policies": [],
        },
        "correction_aware_surface_m20": {
            "schema": uapm.CORRECTION_SCHEMA,
            "authoritative": correction,
        },
    }


def _plan():
    return {
        "intent": "chat",
        "scene": "casual",
        "core_message_jp": BASE_CORE,
        "must_avoid": [],
    }


def test_cross_domain_policy_preserves_current_turn_semantics():
    plan, trace = uapm.apply_decision_to_plan(_plan(), _decision())
    commit = plan["current_turn_semantic_commit_m48"]

    assert plan["core_message_jp"] == BASE_CORE
    assert plan["desired_response_policy_m18"] == "calibrate_need"
    assert plan["response_mode"] == "clarify_light"
    assert trace["reason"] == "desired_response_policy_applied_without_cross_domain_semantic_override"
    assert commit["schema"] == uapm.CURRENT_TURN_SEMANTIC_COMMIT_SCHEMA_M48
    assert commit["status"] == "current_turn_semantics_preserved_cross_domain"
    assert commit["current_turn_semantics_preserved"] is True
    assert commit["semantic_template_authorized"] is False
    assert commit["raw_dialogue_persisted"] is False


def test_current_turn_explicit_response_form_retains_surface_authority():
    plan, _trace = uapm.apply_decision_to_plan(
        _plan(),
        _decision(explicit=True),
    )

    assert plan["core_message_jp"] == POLICY_CORE
    assert plan["response_mode"] == "clarify_light"
    assert "明示" in plan["reply_goal"]
    assert plan["current_turn_semantic_commit_m48"]["semantic_template_authorized"] is True
    assert plan["current_turn_semantic_commit_m48"]["current_turn_surface_authority"] is True


def test_original_arousal_domain_keeps_existing_policy_semantics():
    plan, trace = uapm.apply_decision_to_plan(
        _plan(),
        _decision(domain="arousal_regulation"),
    )

    assert plan["core_message_jp"] == POLICY_CORE
    assert trace["reason"] == "desired_response_prediction_authorized_plan_content"
    assert plan["current_turn_semantic_commit_m48"]["status"] == "policy_semantic_template_authorized_in_domain"
    assert plan["current_turn_semantic_commit_m48"]["semantic_template_authorized"] is True


def test_surface_commit_cannot_reintroduce_cross_domain_template():
    plan, _trace = uapm.apply_decision_to_plan(_plan(), _decision())
    reply, surface = uapm.ensure_decision_reaches_visible_surface(
        "別の自然な返事。",
        plan,
    )

    assert reply == BASE_CORE
    assert POLICY_CORE not in reply
    assert surface["changed"] is True
    assert surface["policy_performed"] is False


def test_runtime_graph_exposes_current_turn_semantic_commit():
    plan, _trace = uapm.apply_decision_to_plan(_plan(), _decision())
    graph = collect_cognitive_graph(
        {
            "user_text": "報告がまた増えた。",
            "reply": BASE_CORE,
            "runtime_trace": {
                "blackboard": [
                    {
                        "stage": "select",
                        "label": "current_turn_semantic_commit_m48",
                        "payload": deepcopy(plan["current_turn_semantic_commit_m48"]),
                    },
                    {
                        "stage": "surface",
                        "label": "adaptive_person_surface_commitment_m18",
                        "payload": {
                            "schema": "uruha_adaptive_person_surface_commitment_m18",
                            "policy_id": "calibrate_need",
                            "policy_performed": False,
                        },
                    },
                ]
            },
        }
    )
    labels = {node["label"] for node in graph["nodes"]}
    edges = {(edge["source"], edge["target"]) for edge in graph["edges"]}
    semantic_id = next(
        node["id"] for node in graph["nodes"]
        if node["label"] == "current_turn_semantic_commit_m48"
    )
    surface_id = next(
        node["id"] for node in graph["nodes"]
        if node["label"] == "adaptive_person_surface_commitment_m18"
    )

    assert "current_turn_semantic_commit_m48" in labels
    assert (semantic_id, surface_id) in edges


def test_web_compact_trace_keeps_m48_commit():
    payload = {
        "cycle_index": 3,
        "current_turn_semantic_commit_m48": {
            "schema": uapm.CURRENT_TURN_SEMANTIC_COMMIT_SCHEMA_M48,
            "status": "current_turn_semantics_preserved_cross_domain",
        },
    }
    compact = web._compact_runtime_trace_m24(payload)
    assert compact["current_turn_semantic_commit_m48"]["status"] == "current_turn_semantics_preserved_cross_domain"
