#!/usr/bin/env python3
"""Translate the frozen V4 protocol into the existing pure scorer contract."""

from __future__ import annotations


def scorer_gates(preregistration: dict, amendment: dict):
    original = dict(preregistration["success_gates"])
    original_call_ceiling = original.pop("fallback_call_count_max")
    change = amendment["protocol_change"]
    if change["original_value"] != original_call_ceiling:
        raise ValueError("protocol amendment does not match original call ceiling")
    if original != amendment["unchanged_success_gates"]:
        raise ValueError("protocol amendment changed a capability gate")
    if change["corrected_value"] != amendment["frozen_rules_feasibility_snapshot"][
        "rules_none_count"
    ]:
        raise ValueError("corrected call ceiling does not match required fallbacks")
    gates = preregistration["success_gates"]
    return {
        "hybrid_correct_count_min": gates["candidate_correct_count_min"],
        "hybrid_accuracy_min": gates["candidate_overall_accuracy_min"],
        "semantic_correct_min": gates["candidate_semantic_correct_min"],
        "procedural_correct_min": gates["candidate_procedural_correct_min"],
        "interpretive_correct_min": gates["candidate_interpretive_correct_min"],
        "none_correct": gates["candidate_none_correct"],
        "critical_false_positive_count_max": gates[
            "critical_false_positive_count_max"
        ],
        "regression_vs_rules_max": gates["regression_vs_rules_count_max"],
        "newly_correct_vs_rules_min": gates["newly_correct_vs_rules_count_min"],
        "parse_success_rate_min": gates["parse_success_rate_min"],
        "model_call_count_max": change["corrected_value"],
        "median_fallback_wall_seconds_max": gates[
            "median_fallback_seconds_max"
        ],
        "warm_p95_fallback_wall_seconds_max": gates[
            "warm_p95_fallback_seconds_max"
        ],
    }
