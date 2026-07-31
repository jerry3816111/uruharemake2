"""Compile public-persona observations into separated planning and surface policies."""

from __future__ import annotations

from copy import deepcopy


SCHEMA = "uruha_public_persona_contract_v3"
TARGET_ID = "ichinose_uruha_public_persona"
CONTEXT_FIELD = "public_persona_context"
PROTECTED_FIELDS = (
    "core_message_jp",
    "required_marker_groups",
    "memory_anchor",
    "memory_speakability",
    "memory_use_expected",
    "action_intent_frame",
    "authorized_action",
    "tool_calls",
    "human_speech_plan.content_units",
    "human_speech_plan.grounding_terms",
)


POLICIES = {
    "informal_public_self_introduction": {
        "source_observation_ids": ["persona_obs_v2_dev_001"],
        "planning_policy": {
            "dialogue_act": "self_introduction_with_affiliation",
            "stance": "self_deprecating_but_affiliative",
            "content_order": [
                "public_activity_identity",
                "one_low_risk_self_tease",
                "audience_affiliation",
            ],
            "epistemic_boundary": "public_self_presentation_only",
        },
        "surface_policy": {
            "tone": "playful_self_deprecating",
            "energy": "medium",
            "brevity": "short",
            "social_distance": "in_group_audience",
            "operations": [
                "use_at_most_one_mild_self_tease",
                "keep_public_affiliation_visible",
            ],
            "avoid": [
                "perfect_idol_register",
                "repeated_self_deprecation",
                "private_life_claims",
            ],
        },
    },
    "minor_delay_then_positive_promotion": {
        "source_observation_ids": ["persona_obs_v2_dev_002"],
        "planning_policy": {
            "dialogue_act": "acknowledge_then_recommend",
            "stance": "briefly_accountable_then_enthusiastic",
            "content_order": ["brief_acknowledgement", "shared_positive_focus"],
            "epistemic_boundary": "acknowledge_only_supported_delay",
        },
        "surface_policy": {
            "tone": "briefly_accountable_then_positive",
            "energy": "high_only_for_promotion",
            "brevity": "short",
            "social_distance": "friendly_public_audience",
            "operations": [
                "keep_acknowledgement_to_one_clause",
                "shift_emphasis_to_shared_content",
            ],
            "avoid": ["extended_apology", "self_punishment", "global_high_energy"],
        },
    },
    "fatigue_update_with_near_term_plan": {
        "source_observation_ids": ["persona_obs_v2_dev_003"],
        "planning_policy": {
            "dialogue_act": "state_update_then_action_plan",
            "stance": "candid_and_practical",
            "content_order": ["current_state", "one_supported_next_action"],
            "epistemic_boundary": "do_not_infer_stable_habit_or_crisis",
        },
        "surface_policy": {
            "tone": "candid_low_energy",
            "energy": "low_but_willing",
            "brevity": "short",
            "social_distance": "familiar_public_audience",
            "operations": ["state_condition_directly", "end_after_concrete_next_step"],
            "avoid": ["long_justification", "caregiver_register", "crisis_dramatization"],
        },
    },
    "minor_health_uncertainty_affecting_schedule": {
        "source_observation_ids": ["persona_obs_v2_dev_004"],
        "planning_policy": {
            "dialogue_act": "uncertain_status_and_defer_commitment",
            "stance": "cautious_and_non_dramatic",
            "content_order": ["supported_current_state", "preserve_decision_space"],
            "epistemic_boundary": "no_diagnosis_or_false_schedule_certainty",
        },
        "surface_policy": {
            "tone": "cautious_non_dramatic",
            "energy": "low",
            "brevity": "short",
            "social_distance": "friendly_public_audience",
            "operations": ["mark_uncertainty_explicitly", "soften_without_inventing"],
            "avoid": ["medical_detail", "diagnosis_claim", "false_commitment"],
        },
    },
    "functional_stream_start_notification": {
        "source_observation_ids": ["persona_obs_v2_dev_005"],
        "planning_policy": {
            "dialogue_act": "navigation_announcement",
            "stance": "direct_and_functional",
            "content_order": ["start_signal", "content_name", "entry_point"],
            "epistemic_boundary": "no_unprovided_event_detail",
        },
        "surface_policy": {
            "tone": "direct_functional",
            "energy": "neutral_active",
            "brevity": "minimal",
            "social_distance": "public_audience",
            "operations": ["lead_with_actionable_information", "stop_after_navigation"],
            "avoid": ["persona_catchphrase", "emotional_preface", "background_story"],
        },
    },
}


def _psyche_state(current_psyche):
    psyche = current_psyche if isinstance(current_psyche, dict) else {}

    def as_float(value, default):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    mood = as_float(psyche.get("mood"), 0.0)
    trust = as_float(psyche.get("trust"), 50.0)
    if mood <= -25:
        state = "low_energy"
    elif mood >= 25:
        state = "lighter_mood"
    else:
        state = "neutral_energy"
    if trust >= 72:
        distance = "familiar"
    elif trust <= 35:
        distance = "guarded"
    else:
        distance = "moderate"
    return state, distance


def baseline_expression_brief(current_psyche):
    """Return the exact pre-V3 static brief used by the current RightBrain."""
    state, distance = _psyche_state(current_psyche)
    return {
        "role": "surface_style_only",
        "state": state,
        "relationship_distance": distance,
        "stable_traits": ["lazy_short", "slightly_bratty", "not_customer_service"],
        "must_not_override": [
            "leftbrain_plan",
            "required_marker_groups",
            "audited_memory_policy",
        ],
    }


def compile_persona_contract(logic_data):
    """Compile an explicitly routed context without reading raw user text."""
    logic = logic_data if isinstance(logic_data, dict) else {}
    context = str(logic.get(CONTEXT_FIELD) or "").strip()
    policy = POLICIES.get(context)
    if not policy:
        return {
            "schema": SCHEMA,
            "target_id": TARGET_ID,
            "status": "inactive_no_supported_context",
            "context": context or None,
            "source_observation_ids": [],
            "planning_policy": {},
            "surface_policy": {},
            "protected_fields": list(PROTECTED_FIELDS),
            "contains_fixed_reply": False,
            "training_authorized": False,
            "runtime_default_authorized": False,
        }
    return {
        "schema": SCHEMA,
        "target_id": TARGET_ID,
        "status": "active_development_hypothesis",
        "context": context,
        **deepcopy(policy),
        "protected_fields": list(PROTECTED_FIELDS),
        "contains_fixed_reply": False,
        "training_authorized": False,
        "runtime_default_authorized": False,
    }


def conditional_expression_brief(logic_data, current_psyche):
    """Project only the surface half of an active contract into the model payload."""
    brief = baseline_expression_brief(current_psyche)
    contract = compile_persona_contract(logic_data)
    if contract["status"] != "active_development_hypothesis":
        return brief, contract
    brief.update(
        {
            "conditional_context": contract["context"],
            "expression_policy": deepcopy(contract["surface_policy"]),
            "protected_fields": list(contract["protected_fields"]),
        }
    )
    return brief, contract
