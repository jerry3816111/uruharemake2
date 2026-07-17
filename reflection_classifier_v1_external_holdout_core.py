#!/usr/bin/env python3
"""Pure matched scoring for the external reflection classifier holdout."""

from __future__ import annotations

from collections import Counter


CLASSES = ("semantic", "procedural", "interpretive", "none")


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else 0.0


def _condition_summary(rows, observed_key):
    class_metrics = {}
    for label in CLASSES:
        selected = [row for row in rows if row["expected_type"] == label]
        correct = sum(row[observed_key] == label for row in selected)
        class_metrics[label] = {
            "total": len(selected),
            "correct": correct,
            "accuracy": _rate(correct, len(selected)),
        }
    correct_count = sum(row[observed_key] == row["expected_type"] for row in rows)
    return {
        "case_count": len(rows),
        "correct_count": correct_count,
        "accuracy": _rate(correct_count, len(rows)),
        "class_metrics": class_metrics,
        "observed_type_counts": dict(
            sorted(Counter(row[observed_key] for row in rows).items())
        ),
    }


def analyze_matched(cases, raw_rows, gates):
    case_by_id = {case["id"]: case for case in cases}
    raw_by_id = {row["id"]: row for row in raw_rows}
    if len(case_by_id) != len(cases) or len(raw_by_id) != len(raw_rows):
        raise ValueError("duplicate case IDs")
    if set(case_by_id) != set(raw_by_id):
        raise ValueError("raw result IDs do not match dataset")

    rows = []
    for case in cases:
        observed = raw_by_id[case["id"]]
        legacy_type = observed["legacy_observed_type"]
        candidate_type = observed["candidate_observed_type"]
        if legacy_type not in CLASSES or candidate_type not in CLASSES:
            raise ValueError(f"unknown observed type: {case['id']}")
        rows.append(
            {
                "id": case["id"],
                "language": case["language"],
                "text": case["text"],
                "expected_type": case["expected_type"],
                "legacy_observed_type": legacy_type,
                "candidate_observed_type": candidate_type,
                "legacy_correct": legacy_type == case["expected_type"],
                "candidate_correct": candidate_type == case["expected_type"],
            }
        )

    legacy = _condition_summary(rows, "legacy_observed_type")
    candidate = _condition_summary(rows, "candidate_observed_type")
    newly_correct = [
        row["id"] for row in rows if row["candidate_correct"] and not row["legacy_correct"]
    ]
    regressions = [
        row["id"] for row in rows if row["legacy_correct"] and not row["candidate_correct"]
    ]
    critical_false_positives = [
        row["id"]
        for row in rows
        if row["expected_type"] == "none"
        and row["candidate_observed_type"] != "none"
    ]
    candidate_classes = candidate["class_metrics"]
    checks = {
        "candidate_correct_count_min": candidate["correct_count"]
        >= gates["candidate_correct_count_min"],
        "candidate_overall_accuracy_min": candidate["accuracy"]
        >= gates["candidate_overall_accuracy_min"],
        "candidate_semantic_correct_min": candidate_classes["semantic"]["correct"]
        >= gates["candidate_semantic_correct_min"],
        "candidate_procedural_correct_min": candidate_classes["procedural"]["correct"]
        >= gates["candidate_procedural_correct_min"],
        "candidate_interpretive_correct_min": candidate_classes["interpretive"][
            "correct"
        ]
        >= gates["candidate_interpretive_correct_min"],
        "candidate_none_correct": candidate_classes["none"]["correct"]
        == gates["candidate_none_correct"],
        "critical_false_positive_count_max": len(critical_false_positives)
        <= gates["critical_false_positive_count_max"],
        "regression_vs_legacy_count_max": len(regressions)
        <= gates["regression_vs_legacy_count_max"],
        "newly_correct_vs_legacy_count_min": len(newly_correct)
        >= gates["newly_correct_vs_legacy_count_min"],
    }
    return {
        "legacy": legacy,
        "candidate": candidate,
        "accuracy_delta": round(candidate["accuracy"] - legacy["accuracy"], 4),
        "newly_correct_count": len(newly_correct),
        "newly_correct_case_ids": newly_correct,
        "regression_count": len(regressions),
        "regression_case_ids": regressions,
        "critical_false_positive_count": len(critical_false_positives),
        "critical_false_positive_case_ids": critical_false_positives,
        "gate_checks": checks,
        "all_gates_pass": all(checks.values()),
        "rows": rows,
    }
