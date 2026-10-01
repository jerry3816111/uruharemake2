"""Causal-graph-aware feature ablations and interventions for frozen M6."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping, Sequence

from .predictor import behavior_logits, predict_behavior
from .transitions import TransitionExample, learned_transition


MASTER_ABLATIONS = (
    "memory",
    "emotion",
    "personality",
    "relationship",
    "preference",
    "goal",
    "habit",
    "temporal_dynamics",
    "explicit_state_transition",
    "llm_semantic_interpretation",
)

IDENTIFIABLE_ABLATIONS = (
    "memory",
    "emotion",
    "personality",
    "relationship",
    "goal",
    "temporal_dynamics",
    "explicit_state_transition",
    "llm_semantic_interpretation",
)

NOT_IDENTIFIABLE_ABLATIONS = {
    "preference": "M6 has no independently represented preference/value feature; assigning a proxy after seeing results would fabricate an ablation.",
    "habit": "M6 has no independently represented habit-prior feature; event.repetition is an observed context feature, not a habit state.",
}


def reconstruct_features(ours_row: Mapping[str, Any]) -> dict[str, float]:
    evidence = ours_row["explanation"]["evidence"]
    features: dict[str, float] = {}
    features.update({f"state.{name}": float(value) for name, value in evidence["state_features"].items()})
    features.update({f"event.{name}": float(value) for name, value in evidence["event_features"].items()})
    features.update({f"memory.{name}": float(value) for name, value in evidence["memory_signals"].items()})
    features.update({f"person.{name}": float(value) for name, value in evidence["person_parameters"].items()})
    return features


def _recompute_transition(
    features: dict[str, float],
    example: TransitionExample,
    transition_model: Mapping[str, Any],
    state_dimensions: Sequence[str],
    *,
    event_features: Mapping[str, float] | None = None,
    memory_signals: Mapping[str, float] | None = None,
    person_parameters: Mapping[str, float] | None = None,
) -> dict[str, float]:
    event = dict(event_features or {name.removeprefix("event."): value for name, value in features.items() if name.startswith("event.")})
    memory = dict(memory_signals or {name.removeprefix("memory."): value for name, value in features.items() if name.startswith("memory.")})
    person = dict(person_parameters or {name.removeprefix("person."): value for name, value in features.items() if name.startswith("person.")})
    changed = replace(example, event_features=event, memory_signals=memory, person_parameters=person)
    transition = learned_transition(
        "T3_HYBRID",
        changed,
        transition_model,
        state_dimensions,
        event_features=event,
        feature_source="m7_controlled_intervention",
    )
    updated = dict(features)
    updated.update({f"event.{name}": value for name, value in event.items()})
    updated.update({f"memory.{name}": value for name, value in memory.items()})
    updated.update({f"person.{name}": value for name, value in person.items()})
    updated.update({f"state.{name}": value for name, value in transition["next_state"].items()})
    return updated


def intervene_feature(
    features: Mapping[str, float],
    feature_name: str,
    value: float,
    *,
    example: TransitionExample,
    transition_model: Mapping[str, Any],
    state_dimensions: Sequence[str],
) -> dict[str, float]:
    if feature_name not in features:
        raise ValueError(f"unknown intervention feature {feature_name}")
    if not 0.0 <= float(value) <= 1.0:
        raise ValueError("intervention value must be within [0, 1]")
    updated = dict(features)
    updated[feature_name] = float(value)
    if feature_name.startswith("event."):
        event = {name.removeprefix("event."): val for name, val in updated.items() if name.startswith("event.")}
        return _recompute_transition(updated, example, transition_model, state_dimensions, event_features=event)
    if feature_name.startswith("memory."):
        memory = {name.removeprefix("memory."): val for name, val in updated.items() if name.startswith("memory.")}
        return _recompute_transition(updated, example, transition_model, state_dimensions, memory_signals=memory)
    if feature_name.startswith("person."):
        person = {name.removeprefix("person."): val for name, val in updated.items() if name.startswith("person.")}
        return _recompute_transition(updated, example, transition_model, state_dimensions, person_parameters=person)
    return updated


def ablate_component(
    component: str,
    features: Mapping[str, float],
    *,
    example: TransitionExample,
    transition_model: Mapping[str, Any],
    state_dimensions: Sequence[str],
) -> dict[str, float]:
    if component not in IDENTIFIABLE_ABLATIONS:
        raise ValueError(f"component is not identifiable in M6: {component}")
    updated = dict(features)
    if component == "memory":
        memory = {name.removeprefix("memory."): 0.0 for name in updated if name.startswith("memory.")}
        return _recompute_transition(updated, example, transition_model, state_dimensions, memory_signals=memory)
    if component == "personality":
        person = {name.removeprefix("person."): 0.0 for name in updated if name.startswith("person.")}
        return _recompute_transition(updated, example, transition_model, state_dimensions, person_parameters=person)
    if component == "llm_semantic_interpretation":
        event = {name.removeprefix("event."): 0.0 for name in updated if name.startswith("event.")}
        return _recompute_transition(updated, example, transition_model, state_dimensions, event_features=event)
    if component == "emotion":
        for name in ("state.arousal", "state.irritation", "state.uncertainty"):
            updated[name] = 0.0
    elif component == "relationship":
        updated["state.relationship_tension"] = 0.0
    elif component == "goal":
        updated["state.task_focus"] = 0.0
    elif component == "temporal_dynamics":
        updated.update({f"state.{name}": float(value) for name, value in example.previous_state.items()})
    elif component == "explicit_state_transition":
        for name in state_dimensions:
            updated[f"state.{name}"] = 0.0
    return updated


def intervention_effect(
    model: Mapping[str, Any],
    original_features: Mapping[str, float],
    intervened_features: Mapping[str, float],
    *,
    temperature: float,
    actual_label: str,
) -> dict[str, Any]:
    original = predict_behavior(model, original_features, temperature=temperature, evidence={})
    intervened = predict_behavior(model, intervened_features, temperature=temperature, evidence={})
    selected = original["selected_behavior"]
    return {
        "original_selected_behavior": selected,
        "intervened_selected_behavior": intervened["selected_behavior"],
        "original_selected_probability": original["probabilities"][selected],
        "intervened_selected_probability": intervened["probabilities"][selected],
        "delta_original_selected_probability": intervened["probabilities"][selected] - original["probabilities"][selected],
        "original_actual_probability": original["probabilities"][actual_label],
        "intervened_actual_probability": intervened["probabilities"][actual_label],
        "delta_actual_probability": intervened["probabilities"][actual_label] - original["probabilities"][actual_label],
        "selection_changed": intervened["selected_behavior"] != selected,
    }


def top_contributing_features(
    model: Mapping[str, Any],
    features: Mapping[str, float],
    selected_label: str,
    *,
    count: int,
) -> list[dict[str, float | str]]:
    terms = behavior_logits(model, features)["contributions"][selected_label]
    ranked = sorted(
        ((name, value) for name, value in terms.items() if name != "bias"),
        key=lambda item: (-abs(item[1]), item[0]),
    )
    return [{"feature": name, "contribution": value} for name, value in ranked[:count]]
