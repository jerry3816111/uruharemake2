#!/usr/bin/env python3
"""Pure scoring helpers for reflection-type classifier experiments."""

from __future__ import annotations

from collections import Counter


CLASSES = ("semantic", "procedural", "interpretive", "none")


def score_predictions(cases, predictions):
    rows = []
    for case in cases:
        observed = predictions.get(case["id"])
        rows.append(
            {
                **case,
                "observed_type": observed,
                "correct": observed == case["expected_type"],
                "critical_false_positive": bool(
                    case["critical_false_positive"] and observed != "none"
                ),
            }
        )
    return rows


def _rate(rows, predicate):
    if not rows:
        return 0.0
    return round(sum(1 for row in rows if predicate(row)) / len(rows), 4)


def summarize(rows):
    by_expected = {
        label: [row for row in rows if row["expected_type"] == label]
        for label in CLASSES
    }
    return {
        "case_count": len(rows),
        "overall_accuracy": _rate(rows, lambda row: row["correct"]),
        "semantic_recall": _rate(
            by_expected["semantic"], lambda row: row["observed_type"] == "semantic"
        ),
        "procedural_recall": _rate(
            by_expected["procedural"],
            lambda row: row["observed_type"] == "procedural",
        ),
        "interpretive_recall": _rate(
            by_expected["interpretive"],
            lambda row: row["observed_type"] == "interpretive",
        ),
        "none_specificity": _rate(
            by_expected["none"], lambda row: row["observed_type"] == "none"
        ),
        "critical_false_positive_count": sum(
            row["critical_false_positive"] for row in rows
        ),
        "observed_type_counts": dict(Counter(row["observed_type"] for row in rows)),
        "correct_case_ids": [row["id"] for row in rows if row["correct"]],
        "failed_case_ids": [row["id"] for row in rows if not row["correct"]],
    }


def gate_checks(summary, gates, regression_count=0):
    checks = {
        "overall_accuracy": summary["overall_accuracy"]
        >= gates["overall_accuracy_min"],
        "semantic_recall": summary["semantic_recall"]
        >= gates["semantic_recall_min"],
        "procedural_recall": summary["procedural_recall"]
        >= gates["procedural_recall_min"],
        "interpretive_recall": summary["interpretive_recall"]
        >= gates["interpretive_recall_min"],
        "none_specificity": summary["none_specificity"]
        >= gates["none_specificity_min"],
        "critical_false_positive_count": summary["critical_false_positive_count"]
        <= gates["critical_false_positive_count_max"],
        "regression_vs_legacy_count": regression_count
        <= gates["regression_vs_legacy_count_max"],
    }
    return {**summary, "gate_checks": checks, "all_gates_pass": all(checks.values())}
