#!/usr/bin/env python3
"""Scoring extensions for structured, program-grounded reflection V4."""

from __future__ import annotations

import typed_reflection_v3_core as v3


def score_rows(raw_rows, control_name, treatment_name):
    scored = v3.score_rows(raw_rows, control_name, treatment_name)
    raw_by_id = {row["case"]["id"]: row for row in raw_rows}
    for row in scored:
        treatment = raw_by_id[row["id"]]["conditions"][treatment_name]
        reflection = treatment.get("reflection_return") or {}
        records = treatment.get("reflection_records") or []
        row["japanese_surface_quality_valid"] = bool(
            row["treatment_wrote"]
            and reflection.get("extraction_version") == "v4_structured_grounded"
            and not reflection.get("validation_reasons")
            and all(
                (record.get("metadata") or {}).get("extraction_version")
                == "v4_structured_grounded"
                for record in records
            )
        )
        row["model_attempt_count"] = int(reflection.get("attempt_count") or 0)
    return scored


def summarize(scored_rows, gates):
    summary = v3.summarize(scored_rows, gates)
    valid_written = [
        row
        for row in scored_rows
        if row["expected_write"]
        and row["treatment_wrote"]
        and row["treatment_reflection_valid"]
    ]
    summary["japanese_surface_quality_rate"] = v3._rate(
        valid_written, lambda row: row["japanese_surface_quality_valid"]
    )
    summary["model_attempt_count"] = sum(
        row["model_attempt_count"] for row in scored_rows
    )
    summary["retried_case_count"] = sum(
        1 for row in scored_rows if row["model_attempt_count"] > 1
    )
    summary["gate_checks"]["japanese_surface_quality_rate"] = (
        summary["japanese_surface_quality_rate"]
        >= gates["japanese_surface_quality_rate_min"]
    )
    summary["all_gates_pass"] = all(summary["gate_checks"].values())
    return summary


def decision_for(summary, decision_rule):
    if summary["all_gates_pass"]:
        return decision_rule["all_gates_pass"]
    safety_precision = (
        "reflection_type_accuracy",
        "valid_rule_precision",
        "no_rule_specificity",
        "collection_routing_accuracy",
        "source_provenance_rate",
        "japanese_surface_quality_rate",
    )
    if any(not summary["gate_checks"][key] for key in safety_precision):
        return decision_rule["any_safety_or_precision_gate_fails"]
    return decision_rule["extraction_passes_behavior_fails"]
