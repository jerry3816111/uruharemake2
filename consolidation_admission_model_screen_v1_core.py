#!/usr/bin/env python3
"""Pure scoring and selection for the consolidation model screen V1."""

from __future__ import annotations

import math
import statistics
from collections import Counter

from consolidation_admission_v3_role_separated_core import (
    TARGETS,
    evidence_grounded,
)


CONTROL = "qwen25_7b_control"
CANDIDATES = ("qwen35_4b_candidate", "qwen35_9b_candidate")
CONDITIONS = (CONTROL, *CANDIDATES)


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else 0.0


def _p95(values):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return round(ordered[index], 4)


def _normalize_condition(cases, rows):
    case_by_id = {case["id"]: case for case in cases}
    row_by_id = {row["id"]: row for row in rows}
    if len(case_by_id) != len(cases):
        raise ValueError("duplicate dataset case IDs")
    if len(row_by_id) != len(rows):
        raise ValueError("duplicate condition case IDs")
    if set(row_by_id) != set(case_by_id):
        raise ValueError("condition rows do not exactly match dataset cases")

    normalized = []
    for case in cases:
        row = row_by_id[case["id"]]
        if row.get("observed_target") not in TARGETS:
            raise ValueError(f"invalid observed target: {case['id']}")
        expected = case["expected_memory_kind"]
        semantic_frame_exact = (
            bool(row.get("parse_success"))
            and row.get("memory_kind") == expected
            and row.get("persistence_basis")
            == case["expected_persistence_basis"]
        )
        normalized.append(
            {
                **row,
                "expected_target": expected,
                "correct": row["observed_target"] == expected,
                "semantic_frame_exact": semantic_frame_exact,
                "evidence_grounded": evidence_grounded(case, row),
                "derived_applicability_success": (
                    row.get("compiled_applies_to")
                    == case["expected_applies_to"]
                ),
            }
        )
    return normalized


def _condition_summary(cases, rows):
    normalized = _normalize_condition(cases, rows)
    elapsed = [float(row["wall_seconds"]) for row in normalized]
    correct = sum(bool(row["correct"]) for row in normalized)
    parse_count = sum(bool(row.get("parse_success")) for row in normalized)
    index_count = sum(
        bool(row.get("index_contract_success")) for row in normalized
    )
    frame_count = sum(
        bool(row["semantic_frame_exact"]) for row in normalized
    )
    evidence_count = sum(
        bool(row["evidence_grounded"]) for row in normalized
    )
    positive_evidence_count = sum(
        bool(row["evidence_grounded"])
        for row in normalized
        if row["expected_target"] != "none"
    )
    applicability_count = sum(
        bool(row["derived_applicability_success"]) for row in normalized
    )
    class_metrics = {}
    for target in TARGETS:
        selected = [
            row for row in normalized if row["expected_target"] == target
        ]
        target_correct = sum(bool(row["correct"]) for row in selected)
        class_metrics[target] = {
            "total": len(selected),
            "correct_count": target_correct,
            "accuracy": _rate(target_correct, len(selected)),
        }
    false_writes = [
        row["id"]
        for row in normalized
        if row["expected_target"] == "none"
        and row["observed_target"] != "none"
    ]
    missed_writes = [
        row["id"]
        for row in normalized
        if row["expected_target"] != "none"
        and row["observed_target"] == "none"
    ]
    return {
        "correct_count": correct,
        "accuracy": _rate(correct, len(normalized)),
        "class_metrics": class_metrics,
        "observed_target_counts": dict(
            sorted(
                Counter(
                    row["observed_target"] for row in normalized
                ).items()
            )
        ),
        "parse_success_count": parse_count,
        "parse_success_rate": _rate(parse_count, len(normalized)),
        "index_contract_success_count": index_count,
        "index_contract_success_rate": _rate(index_count, len(normalized)),
        "semantic_frame_exact_count": frame_count,
        "semantic_frame_exact_rate": _rate(frame_count, len(normalized)),
        "evidence_grounded_count": evidence_count,
        "evidence_grounded_rate": _rate(evidence_count, len(normalized)),
        "positive_evidence_grounded_count": positive_evidence_count,
        "positive_evidence_grounded_rate": _rate(
            positive_evidence_count,
            sum(
                case["expected_memory_kind"] != "none" for case in cases
            ),
        ),
        "derived_applicability_success_count": applicability_count,
        "derived_applicability_success_rate": _rate(
            applicability_count, len(normalized)
        ),
        "false_long_term_write_count": len(false_writes),
        "false_long_term_write_case_ids": false_writes,
        "missed_long_term_write_count": len(missed_writes),
        "missed_long_term_write_case_ids": missed_writes,
        "median_wall_seconds": (
            round(statistics.median(elapsed), 4) if elapsed else 0.0
        ),
        "warm_p95_wall_seconds": _p95(elapsed[1:]),
        "rows": normalized,
    }


def _paired(candidate_summary, control_summary):
    candidate_by_id = {
        row["id"]: row for row in candidate_summary["rows"]
    }
    control_by_id = {row["id"]: row for row in control_summary["rows"]}
    if set(candidate_by_id) != set(control_by_id):
        raise ValueError("paired conditions do not share case IDs")
    newly_correct = []
    regressions = []
    matched_rows = []
    for case_id in control_by_id:
        control = control_by_id[case_id]
        candidate = candidate_by_id[case_id]
        if candidate["correct"] and not control["correct"]:
            newly_correct.append(case_id)
        if control["correct"] and not candidate["correct"]:
            regressions.append(case_id)
        matched_rows.append(
            {
                "id": case_id,
                "expected_target": control["expected_target"],
                "control_target": control["observed_target"],
                "candidate_target": candidate["observed_target"],
                "control_correct": control["correct"],
                "candidate_correct": candidate["correct"],
                "candidate_semantic_frame_exact": candidate[
                    "semantic_frame_exact"
                ],
                "candidate_evidence_grounded": candidate[
                    "evidence_grounded"
                ],
            }
        )
    net_gain = (
        candidate_summary["correct_count"]
        - control_summary["correct_count"]
    )
    return {
        "accuracy_delta_vs_control": round(
            candidate_summary["accuracy"] - control_summary["accuracy"], 4
        ),
        "net_correct_gain_vs_control": net_gain,
        "newly_correct_count": len(newly_correct),
        "newly_correct_case_ids": newly_correct,
        "regression_count": len(regressions),
        "regression_case_ids": regressions,
        "matched_rows": matched_rows,
    }


def _candidate_checks(
    condition,
    summary,
    paired,
    eligibility_gates,
    latency_gates,
):
    checks = {
        "candidate_correct_count_min": summary["correct_count"]
        >= eligibility_gates["candidate_correct_count_min"],
        "candidate_accuracy_min": summary["accuracy"]
        >= eligibility_gates["candidate_accuracy_min"],
        "candidate_wisdom_correct_min": summary["class_metrics"]["wisdom"][
            "correct_count"
        ]
        >= eligibility_gates["candidate_wisdom_correct_min"],
        "candidate_procedural_correct_min": summary["class_metrics"][
            "procedural"
        ]["correct_count"]
        >= eligibility_gates["candidate_procedural_correct_min"],
        "candidate_none_correct_min": summary["class_metrics"]["none"][
            "correct_count"
        ]
        >= eligibility_gates["candidate_none_correct_min"],
        "candidate_semantic_frame_exact_count_min": summary[
            "semantic_frame_exact_count"
        ]
        >= eligibility_gates["candidate_semantic_frame_exact_count_min"],
        "candidate_evidence_grounded_count_min": summary[
            "evidence_grounded_count"
        ]
        >= eligibility_gates["candidate_evidence_grounded_count_min"],
        "candidate_positive_evidence_grounded_count_min": summary[
            "positive_evidence_grounded_count"
        ]
        >= eligibility_gates[
            "candidate_positive_evidence_grounded_count_min"
        ],
        "newly_correct_vs_control_min": paired["newly_correct_count"]
        >= eligibility_gates["newly_correct_vs_control_min"],
        "regression_vs_control_max": paired["regression_count"]
        <= eligibility_gates["regression_vs_control_max"],
        "net_correct_gain_vs_control_min": paired[
            "net_correct_gain_vs_control"
        ]
        >= eligibility_gates["net_correct_gain_vs_control_min"],
        "candidate_false_long_term_write_count_max": summary[
            "false_long_term_write_count"
        ]
        <= eligibility_gates[
            "candidate_false_long_term_write_count_max"
        ],
        "candidate_missed_long_term_write_count_max": summary[
            "missed_long_term_write_count"
        ]
        <= eligibility_gates[
            "candidate_missed_long_term_write_count_max"
        ],
        "candidate_tool_parse_success_count": summary[
            "parse_success_count"
        ]
        == eligibility_gates["candidate_tool_parse_success_count"],
        "candidate_index_contract_success_count": summary[
            "index_contract_success_count"
        ]
        == eligibility_gates["candidate_index_contract_success_count"],
        "candidate_median_wall_seconds_max": summary["median_wall_seconds"]
        <= latency_gates[f"{condition}_median_wall_seconds_max"],
        "candidate_warm_p95_wall_seconds_max": summary[
            "warm_p95_wall_seconds"
        ]
        <= latency_gates[f"{condition}_warm_p95_wall_seconds_max"],
    }
    return checks


def _selection_key(condition, result, models):
    summary = result["summary"]
    return (
        summary["false_long_term_write_count"]
        + summary["missed_long_term_write_count"],
        -summary["semantic_frame_exact_count"],
        -summary["evidence_grounded_count"],
        summary["median_wall_seconds"],
        models[condition]["blob_bytes"],
    )


def analyze_model_screen(
    cases,
    rows_by_condition,
    *,
    models,
    eligibility_gates,
    latency_gates,
    run_invariants,
    model_calls,
    transport_attempts,
):
    if set(rows_by_condition) != set(CONDITIONS):
        raise ValueError("model screen condition set drift")
    summaries = {
        condition: _condition_summary(cases, rows_by_condition[condition])
        for condition in CONDITIONS
    }
    control_summary = summaries[CONTROL]
    candidates = {}
    for condition in CANDIDATES:
        paired = _paired(summaries[condition], control_summary)
        checks = _candidate_checks(
            condition,
            summaries[condition],
            paired,
            eligibility_gates,
            latency_gates,
        )
        candidates[condition] = {
            "summary": summaries[condition],
            "paired_vs_control": paired,
            "gate_checks": checks,
            "eligible": all(checks.values()),
        }

    run_checks = {
        "model_call_count_exact": model_calls
        == run_invariants["model_call_count_exact"],
        "transport_attempt_count_exact": transport_attempts
        == run_invariants["transport_attempt_count_exact"],
        "calls_per_model_exact": all(
            len(rows_by_condition[condition])
            == run_invariants["calls_per_model_exact"]
            for condition in CONDITIONS
        ),
    }
    eligible = [
        condition
        for condition in CANDIDATES
        if candidates[condition]["eligible"]
    ]
    selected = None
    shortlist = []
    if eligible and all(run_checks.values()):
        highest_correct = max(
            candidates[condition]["summary"]["correct_count"]
            for condition in eligible
        )
        shortlist = [
            condition
            for condition in eligible
            if candidates[condition]["summary"]["correct_count"]
            >= highest_correct - 1
        ]
        selected = min(
            shortlist,
            key=lambda condition: _selection_key(
                condition, candidates[condition], models
            ),
        )

    for summary in summaries.values():
        summary.pop("rows")

    return {
        "case_count": len(cases),
        "model_call_count": model_calls,
        "transport_attempt_count": transport_attempts,
        "run_checks": run_checks,
        "control": control_summary,
        "candidates": candidates,
        "eligible_candidates": eligible,
        "selection_shortlist": shortlist,
        "selected_model_condition": selected,
        "decision": (
            "authorize_fresh_integration_pilot_for_selected_model"
            if selected
            else "reject_model_replacement_and_proceed_to_two_stage_architecture"
        ),
    }
