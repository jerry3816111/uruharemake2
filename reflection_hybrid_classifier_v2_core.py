#!/usr/bin/env python3
"""Pure scoring for the rules-plus-local-model reflection classifier pilot."""

from __future__ import annotations

import math
import statistics
from collections import Counter


CLASSES = ("semantic", "procedural", "interpretive", "none")


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else 0.0


def _p95(values):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return round(ordered[index], 4)


def analyze_condition(cases, rules_predictions, fallback_rows, gates):
    case_by_id = {case["id"]: case for case in cases}
    if len(case_by_id) != len(cases) or set(case_by_id) != set(rules_predictions):
        raise ValueError("rules predictions do not exactly match cases")
    fallback_by_id = {row["id"]: row for row in fallback_rows}
    if len(fallback_by_id) != len(fallback_rows):
        raise ValueError("duplicate fallback case IDs")
    expected_fallback_ids = {
        case_id for case_id, label in rules_predictions.items() if label == "none"
    }
    if set(fallback_by_id) != expected_fallback_ids:
        raise ValueError("fallback rows must exactly match rules-only none decisions")

    rows = []
    for case in cases:
        control = rules_predictions[case["id"]]
        if control not in CLASSES:
            raise ValueError(f"unknown rules label: {case['id']}")
        fallback = fallback_by_id.get(case["id"])
        hybrid = control if fallback is None else fallback["observed_type"]
        if hybrid not in CLASSES:
            raise ValueError(f"unknown hybrid label: {case['id']}")
        rows.append(
            {
                "id": case["id"],
                "language": case["language"],
                "expected_type": case["expected_type"],
                "rules_observed_type": control,
                "hybrid_observed_type": hybrid,
                "rules_correct": control == case["expected_type"],
                "hybrid_correct": hybrid == case["expected_type"],
                "fallback_used": fallback is not None,
                "fallback_parse_success": (
                    None if fallback is None else fallback["parse_success"]
                ),
            }
        )

    class_metrics = {}
    for label in CLASSES:
        selected = [row for row in rows if row["expected_type"] == label]
        correct = sum(row["hybrid_correct"] for row in selected)
        class_metrics[label] = {
            "total": len(selected),
            "correct": correct,
            "accuracy": _rate(correct, len(selected)),
        }
    hybrid_correct = sum(row["hybrid_correct"] for row in rows)
    rules_correct = sum(row["rules_correct"] for row in rows)
    newly_correct = [
        row["id"] for row in rows if row["hybrid_correct"] and not row["rules_correct"]
    ]
    regressions = [
        row["id"] for row in rows if row["rules_correct"] and not row["hybrid_correct"]
    ]
    false_positives = [
        row["id"]
        for row in rows
        if row["expected_type"] == "none" and row["hybrid_observed_type"] != "none"
    ]
    parse_success_count = sum(row["parse_success"] for row in fallback_rows)
    elapsed = [float(row["wall_seconds"]) for row in fallback_rows]
    median_wall = round(statistics.median(elapsed), 4) if elapsed else 0.0
    warm_p95 = _p95(elapsed[1:])
    parse_rate = _rate(parse_success_count, len(fallback_rows))
    observed_counts = dict(
        sorted(Counter(row["hybrid_observed_type"] for row in rows).items())
    )

    checks = {
        "hybrid_correct_count_min": hybrid_correct
        >= gates["hybrid_correct_count_min"],
        "hybrid_accuracy_min": _rate(hybrid_correct, len(rows))
        >= gates["hybrid_accuracy_min"],
        "semantic_correct_min": class_metrics["semantic"]["correct"]
        >= gates["semantic_correct_min"],
        "procedural_correct_min": class_metrics["procedural"]["correct"]
        >= gates["procedural_correct_min"],
        "interpretive_correct_min": class_metrics["interpretive"]["correct"]
        >= gates["interpretive_correct_min"],
        "none_correct": class_metrics["none"]["correct"] == gates["none_correct"],
        "newly_correct_vs_rules_min": len(newly_correct)
        >= gates["newly_correct_vs_rules_min"],
        "regression_vs_rules_max": len(regressions)
        <= gates["regression_vs_rules_max"],
        "critical_false_positive_count_max": len(false_positives)
        <= gates["critical_false_positive_count_max"],
        "parse_success_rate_min": parse_rate >= gates["parse_success_rate_min"],
        "model_call_count_max": len(fallback_rows)
        <= gates["model_call_count_max"],
        "median_fallback_wall_seconds_max": median_wall
        <= gates["median_fallback_wall_seconds_max"],
        "warm_p95_fallback_wall_seconds_max": warm_p95
        <= gates["warm_p95_fallback_wall_seconds_max"],
    }
    return {
        "case_count": len(rows),
        "rules_correct_count": rules_correct,
        "rules_accuracy": _rate(rules_correct, len(rows)),
        "hybrid_correct_count": hybrid_correct,
        "hybrid_accuracy": _rate(hybrid_correct, len(rows)),
        "accuracy_delta": round(
            _rate(hybrid_correct, len(rows)) - _rate(rules_correct, len(rows)), 4
        ),
        "class_metrics": class_metrics,
        "observed_type_counts": observed_counts,
        "newly_correct_count": len(newly_correct),
        "newly_correct_case_ids": newly_correct,
        "regression_count": len(regressions),
        "regression_case_ids": regressions,
        "critical_false_positive_count": len(false_positives),
        "critical_false_positive_case_ids": false_positives,
        "model_call_count": len(fallback_rows),
        "parse_success_count": parse_success_count,
        "parse_success_rate": parse_rate,
        "median_fallback_wall_seconds": median_wall,
        "warm_p95_fallback_wall_seconds": warm_p95,
        "gate_checks": checks,
        "all_gates_pass": all(checks.values()),
        "rows": rows,
    }


def select_smallest_passing(ordered_models, analyses):
    for model in ordered_models:
        name = model["model"]
        if name in analyses and analyses[name]["all_gates_pass"]:
            return name
    return None
