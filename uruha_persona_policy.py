"""Structured public-persona policy providers with no final-reply content."""

from __future__ import annotations

from copy import deepcopy

import public_persona_contract_v3 as public_contract


SCHEMA = "uruha_persona_policy_projection_v1"
LEGACY_PROVIDER = "legacy_runtime"
TARGET_PROVIDER = "structured_target_public_persona"
NEUTRAL_PROVIDER = "structured_neutral_dialogue"
NEUTRAL_TARGET_ID = "neutral_dialogue_control"
PROVIDER_IDS = frozenset({LEGACY_PROVIDER, TARGET_PROVIDER, NEUTRAL_PROVIDER})
LEGACY_SURFACE_MODE = "legacy_deterministic_surface"
STRUCTURED_SURFACE_MODE = "structured_local_model_surface"
PROTECTED_PLAN_FIELDS = (
    "core_message_jp",
    "required_marker_groups",
    "memory_anchor",
    "memory_speakability",
    "memory_use_expected",
    "action_intent_frame",
    "authorized_action",
    "tool_calls",
    "human_speech_plan",
)


def _psyche_state(current_psyche):
    baseline = public_contract.baseline_expression_brief(current_psyche)
    return baseline["state"], baseline["relationship_distance"]


def _neutral_policy_like(contract):
    planning = contract.get("planning_policy") or {}
    surface = contract.get("surface_policy") or {}
    content_order = [f"neutral_content_step_{index + 1}" for index, _ in enumerate(planning.get("content_order") or [])]
    operations = [f"neutral_surface_operation_{index + 1}" for index, _ in enumerate(surface.get("operations") or [])]
    avoid = [f"neutral_surface_avoid_{index + 1}" for index, _ in enumerate(surface.get("avoid") or [])]
    return {
        "planning_policy": {
            "dialogue_act": "preserve_cognitive_plan",
            "stance": "neutral_casual",
            "content_order": content_order,
            "epistemic_boundary": "preserve_existing_evidence_boundary",
        },
        "surface_policy": {
            "tone": "neutral_casual",
            "energy": "context_matched",
            "brevity": "short",
            "social_distance": "moderate",
            "operations": operations,
            "avoid": avoid,
        },
    }


class PersonaPolicyProvider:
    """Compile persona constraints without producing words for the final reply."""

    def __init__(self, provider_id):
        if provider_id not in PROVIDER_IDS:
            raise ValueError(f"unknown persona policy provider: {provider_id}")
        self.provider_id = provider_id

    @property
    def is_legacy(self):
        return self.provider_id == LEGACY_PROVIDER

    @property
    def surface_mode(self):
        if self.is_legacy:
            return LEGACY_SURFACE_MODE
        return STRUCTURED_SURFACE_MODE

    @property
    def permits_legacy_fixed_surface(self):
        return self.is_legacy

    @property
    def requires_structured_model_surface(self):
        return not self.is_legacy

    def planner_goal_line(self):
        if self.provider_id == LEGACY_PROVIDER:
            return "- Final output should sound like Ichinose Uruha."
        if self.provider_id == TARGET_PROVIDER:
            return "- Apply only the attached structured public-persona policy; never copy or invent a target utterance."
        return "- Apply only the attached neutral dialogue policy; do not imitate a named person."

    def compile(self, logic_data, current_psyche):
        logic = logic_data if isinstance(logic_data, dict) else {}
        state, distance = _psyche_state(current_psyche)
        if self.provider_id == LEGACY_PROVIDER:
            return {
                "schema": SCHEMA,
                "provider_id": self.provider_id,
                "status": "legacy_runtime_passthrough",
                "target_id": public_contract.TARGET_ID,
                "surface_mode": self.surface_mode,
                "legacy_fixed_surface_allowed": self.permits_legacy_fixed_surface,
                "source_observation_ids": [],
                "planning_policy": {},
                "expression_brief": public_contract.baseline_expression_brief(current_psyche),
                "protected_fields": list(PROTECTED_PLAN_FIELDS),
                "contains_fixed_reply": False,
                "contains_target_utterance": False,
            }

        target_contract = public_contract.compile_persona_contract(logic)
        active = target_contract["status"] == "active_development_hypothesis"
        if self.provider_id == TARGET_PROVIDER:
            expression_brief, _ = public_contract.conditional_expression_brief(logic, current_psyche)
            planning_policy = deepcopy(target_contract.get("planning_policy") or {})
            source_ids = list(target_contract.get("source_observation_ids") or [])
            status = "active_structured_target_policy" if active else "inactive_no_supported_target_context"
        else:
            neutral = _neutral_policy_like(target_contract)
            expression_brief = {
                "role": "surface_style_only",
                "state": state,
                "relationship_distance": distance,
                "stable_traits": ["neutral_casual", "moderate_directness", "not_customer_service"],
                "must_not_override": [
                    "leftbrain_plan",
                    "required_marker_groups",
                    "audited_memory_policy",
                ],
            }
            if active:
                expression_brief.update(
                    {
                        "conditional_context": target_contract["context"],
                        "expression_policy": neutral["surface_policy"],
                        "protected_fields": list(target_contract["protected_fields"]),
                    }
                )
            planning_policy = neutral["planning_policy"] if active else {}
            source_ids = [
                f"neutral_control_policy_{index + 1:03d}"
                for index, _ in enumerate(target_contract.get("source_observation_ids") or [])
            ]
            status = "active_structured_neutral_policy" if active else "inactive_no_supported_target_context"

        return {
            "schema": SCHEMA,
            "provider_id": self.provider_id,
            "status": status,
            "target_id": (
                public_contract.TARGET_ID
                if self.provider_id == TARGET_PROVIDER
                else NEUTRAL_TARGET_ID
            ),
            "surface_mode": self.surface_mode,
            "legacy_fixed_surface_allowed": self.permits_legacy_fixed_surface,
            "source_observation_ids": source_ids,
            "planning_policy": planning_policy,
            "expression_brief": expression_brief,
            "protected_fields": list(PROTECTED_PLAN_FIELDS),
            "contains_fixed_reply": False,
            "contains_target_utterance": False,
        }

    def attach_to_plan(self, plan, current_psyche):
        source = plan if isinstance(plan, dict) else {}
        projected = deepcopy(source)
        protected_before = {key: deepcopy(source.get(key)) for key in PROTECTED_PLAN_FIELDS}
        projected["public_persona_policy"] = self.compile(source, current_psyche)
        protected_after = {key: deepcopy(projected.get(key)) for key in PROTECTED_PLAN_FIELDS}
        if protected_before != protected_after:
            raise ValueError("persona policy provider modified a protected cognitive field")
        return projected

    def expression_brief(self, logic_data, current_psyche):
        projection = self.compile(logic_data, current_psyche)
        return deepcopy(projection["expression_brief"]), projection


def build_persona_policy_provider(provider_id):
    return PersonaPolicyProvider(provider_id)
