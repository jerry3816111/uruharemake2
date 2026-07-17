#!/usr/bin/env python3
"""Pure parsing and matched scoring for the V5 discourse-frame pilot."""

from __future__ import annotations

import math
import statistics
from collections import Counter


CLASSES = ("semantic", "procedural", "interpretive", "none")
FRAME_ENUMS = {
    "speaker_scope": {
        "first_person",
        "addressee",
        "third_party",
        "mixed_dialogue",
        "unclear",
    },
    "addressee_target": {
        "interlocutor",
        "self",
        "third_party",
        "general",
        "none",
        "unclear",
    },
    "time_scope": {
        "durable",
        "future_interaction",
        "current_or_one_time",
        "past",
        "unclear",
    },
    "communicative_act": {
        "self_attribute",
        "directive",
        "meaning_explanation",
        "question",
        "report",
        "other",
    },
    "relation_to_prior_words": {
        "explains_own_words",
        "corrects_interlocutor",
        "quotes_without_explaining",
        "none",
        "unclear",
    },
    "reflection_type": set(CLASSES),
}


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else 0.0


def _p95(values):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return round(ordered[index], 4)


def parse_discourse_frame_tool_response(response):
    message = response.get("message") or {}
    raw_content = str(message.get("content") or "")
    raw_tool_calls = message.get("tool_calls")
    if not isinstance(raw_tool_calls, list):
        return None, False, raw_content, raw_tool_calls, "missing_tool_calls"
    if len(raw_tool_calls) != 1:
        return None, False, raw_content, raw_tool_calls, "tool_call_count"
    function = raw_tool_calls[0].get("function") or {}
    if function.get("name") != "classify_reflection_with_discourse_frame":
        return None, False, raw_content, raw_tool_calls, "tool_name"
    arguments = function.get("arguments")
    if not isinstance(arguments, dict):
        return None, False, raw_content, raw_tool_calls, "arguments_type"
    if set(arguments) != set(FRAME_ENUMS):
        return None, False, raw_content, raw_tool_calls, "argument_keys"
    for key, allowed in FRAME_ENUMS.items():
        if arguments[key] not in allowed:
            return None, False, raw_content, raw_tool_calls, f"invalid_{key}"
    return dict(arguments), True, raw_content, raw_tool_calls, None


def parse_direct_tool_response(response):
    message = response.get("message") or {}
    raw_content = str(message.get("content") or "")
    raw_tool_calls = message.get("tool_calls")
    if not isinstance(raw_tool_calls, list):
        return None, False, raw_content, raw_tool_calls, "missing_tool_calls"
    if len(raw_tool_calls) != 1:
        return None, False, raw_content, raw_tool_calls, "tool_call_count"
    function = raw_tool_calls[0].get("function") or {}
    if function.get("name") != "classify_reflection":
        return None, False, raw_content, raw_tool_calls, "tool_name"
    arguments = function.get("arguments")
    if not isinstance(arguments, dict):
        return None, False, raw_content, raw_tool_calls, "arguments_type"
    if set(arguments) != {"reflection_type"}:
        return None, False, raw_content, raw_tool_calls, "argument_keys"
    label = arguments["reflection_type"]
    if label not in CLASSES:
        return None, False, raw_content, raw_tool_calls, "invalid_reflection_type"
    return label, True, raw_content, raw_tool_calls, None


def analyze_discourse_frame_condition(
    cases,
    rules_predictions,
    frozen_control_rows,
    live_control_fallback_rows,
    candidate_fallback_rows,
    candidate_gates,
    live_control_gates,
    total_model_call_count_exact,
):
    case_by_id = {case["id"]: case for case in cases}
    if len(case_by_id) != len(cases) or set(case_by_id) != set(rules_predictions):
        raise ValueError("rules predictions do not exactly match cases")
    control_by_id = {row["id"]: row for row in frozen_control_rows}
    if len(control_by_id) != len(frozen_control_rows):
        raise ValueError("duplicate frozen-control case IDs")
    if set(control_by_id) != set(case_by_id):
        raise ValueError("frozen-control rows do not exactly match cases")
    live_control_by_id = {row["id"]: row for row in live_control_fallback_rows}
    candidate_by_id = {row["id"]: row for row in candidate_fallback_rows}
    if len(live_control_by_id) != len(live_control_fallback_rows):
        raise ValueError("duplicate live-control fallback case IDs")
    if len(candidate_by_id) != len(candidate_fallback_rows):
        raise ValueError("duplicate candidate fallback case IDs")
    expected_fallback_ids = {
        case_id for case_id, label in rules_predictions.items() if label == "none"
    }
    if set(live_control_by_id) != expected_fallback_ids:
        raise ValueError(
            "live-control fallback rows must exactly match rules-only none decisions"
        )
    if set(candidate_by_id) != expected_fallback_ids:
        raise ValueError(
            "candidate fallback rows must exactly match rules-only none decisions"
        )

    rows = []
    for case in cases:
        case_id = case["id"]
        rules_label = rules_predictions[case_id]
        frozen_control_label = control_by_id[case_id]["hybrid_observed_type"]
        live_control_fallback = live_control_by_id.get(case_id)
        candidate_fallback = candidate_by_id.get(case_id)
        live_control_label = (
            rules_label
            if live_control_fallback is None
            else live_control_fallback["observed_type"]
        )
        candidate_label = (
            rules_label
            if candidate_fallback is None
            else candidate_fallback["observed_type"]
        )
        if rules_label not in CLASSES:
            raise ValueError(f"unknown rules label: {case_id}")
        if frozen_control_label not in CLASSES:
            raise ValueError(f"unknown frozen-control label: {case_id}")
        if live_control_label not in CLASSES:
            raise ValueError(f"unknown live-control label: {case_id}")
        if candidate_label not in CLASSES:
            raise ValueError(f"unknown candidate label: {case_id}")
        expected = case["expected_type"]
        rows.append(
            {
                "id": case_id,
                "language": case["language"],
                "expected_type": expected,
                "rules_observed_type": rules_label,
                "frozen_control_observed_type": frozen_control_label,
                "live_control_observed_type": live_control_label,
                "candidate_observed_type": candidate_label,
                "frozen_control_correct": frozen_control_label == expected,
                "live_control_correct": live_control_label == expected,
                "candidate_correct": candidate_label == expected,
                "fallback_used": candidate_fallback is not None,
                "live_control_parse_success": (
                    None
                    if live_control_fallback is None
                    else live_control_fallback["parse_success"]
                ),
                "candidate_parse_success": (
                    None
                    if candidate_fallback is None
                    else candidate_fallback["parse_success"]
                ),
            }
        )

    class_metrics = {}
    for label in CLASSES:
        selected = [row for row in rows if row["expected_type"] == label]
        correct = sum(row["candidate_correct"] for row in selected)
        class_metrics[label] = {
            "total": len(selected),
            "correct": correct,
            "accuracy": _rate(correct, len(selected)),
        }
    frozen_control_correct = sum(row["frozen_control_correct"] for row in rows)
    live_control_correct = sum(row["live_control_correct"] for row in rows)
    candidate_correct = sum(row["candidate_correct"] for row in rows)
    newly_correct = [
        row["id"]
        for row in rows
        if row["candidate_correct"] and not row["live_control_correct"]
    ]
    regressions = [
        row["id"]
        for row in rows
        if row["live_control_correct"] and not row["candidate_correct"]
    ]
    false_positives = [
        row["id"]
        for row in rows
        if row["expected_type"] == "none"
        and row["candidate_observed_type"] != "none"
    ]
    frozen_prediction_drift = [
        row["id"]
        for row in rows
        if row["live_control_observed_type"]
        != row["frozen_control_observed_type"]
    ]
    live_control_false_positives = [
        row["id"]
        for row in rows
        if row["expected_type"] == "none"
        and row["live_control_observed_type"] != "none"
    ]
    live_control_parse_success_count = sum(
        row["parse_success"] for row in live_control_fallback_rows
    )
    candidate_parse_success_count = sum(
        row["parse_success"] for row in candidate_fallback_rows
    )
    live_control_parse_rate = _rate(
        live_control_parse_success_count, len(live_control_fallback_rows)
    )
    candidate_parse_rate = _rate(
        candidate_parse_success_count, len(candidate_fallback_rows)
    )
    elapsed = [float(row["wall_seconds"]) for row in candidate_fallback_rows]
    median_wall = round(statistics.median(elapsed), 4) if elapsed else 0.0
    warm_p95 = _p95(elapsed[1:])

    checks = {
        "live_control_correct_count_exact": live_control_correct
        == live_control_gates["correct_count_exact"],
        "live_control_prediction_drift_max": len(frozen_prediction_drift)
        <= live_control_gates["prediction_drift_vs_frozen_v3_count_max"],
        "live_control_parse_success_rate_min": live_control_parse_rate
        >= live_control_gates["parse_success_rate_min"],
        "live_control_critical_false_positive_count_max": len(
            live_control_false_positives
        )
        <= live_control_gates["critical_false_positive_count_max"],
        "live_control_fallback_call_count_exact": len(live_control_fallback_rows)
        == live_control_gates["fallback_call_count_exact"],
        "candidate_correct_count_min": candidate_correct
        >= candidate_gates["candidate_correct_count_min"],
        "candidate_accuracy_min": _rate(candidate_correct, len(rows))
        >= candidate_gates["candidate_accuracy_min"],
        "candidate_semantic_correct_min": class_metrics["semantic"]["correct"]
        >= candidate_gates["candidate_semantic_correct_min"],
        "candidate_procedural_correct_min": class_metrics["procedural"]["correct"]
        >= candidate_gates["candidate_procedural_correct_min"],
        "candidate_interpretive_correct_min": class_metrics["interpretive"]["correct"]
        >= candidate_gates["candidate_interpretive_correct_min"],
        "candidate_none_correct": class_metrics["none"]["correct"]
        == candidate_gates["candidate_none_correct"],
        "newly_correct_vs_matched_control_min": len(newly_correct)
        >= candidate_gates["newly_correct_vs_matched_control_min"],
        "regression_vs_matched_control_max": len(regressions)
        <= candidate_gates["regression_vs_matched_control_max"],
        "critical_false_positive_count_max": len(false_positives)
        <= candidate_gates["critical_false_positive_count_max"],
        "parse_success_rate_min": candidate_parse_rate
        >= candidate_gates["parse_success_rate_min"],
        "total_model_call_count_exact": (
            len(live_control_fallback_rows) + len(candidate_fallback_rows)
        )
        == total_model_call_count_exact,
        "median_fallback_seconds_max": median_wall
        <= candidate_gates["median_fallback_seconds_max"],
        "warm_p95_fallback_seconds_max": warm_p95
        <= candidate_gates["warm_p95_fallback_seconds_max"],
    }
    return {
        "case_count": len(rows),
        "frozen_control_correct_count": frozen_control_correct,
        "frozen_control_accuracy": _rate(frozen_control_correct, len(rows)),
        "live_control_correct_count": live_control_correct,
        "live_control_accuracy": _rate(live_control_correct, len(rows)),
        "live_control_prediction_drift_count": len(frozen_prediction_drift),
        "live_control_prediction_drift_case_ids": frozen_prediction_drift,
        "live_control_parse_success_rate": live_control_parse_rate,
        "live_control_critical_false_positive_count": len(
            live_control_false_positives
        ),
        "candidate_correct_count": candidate_correct,
        "candidate_accuracy": _rate(candidate_correct, len(rows)),
        "accuracy_delta_vs_live_control": round(
            _rate(candidate_correct, len(rows))
            - _rate(live_control_correct, len(rows)),
            4,
        ),
        "class_metrics": class_metrics,
        "observed_type_counts": dict(
            sorted(Counter(row["candidate_observed_type"] for row in rows).items())
        ),
        "newly_correct_count": len(newly_correct),
        "newly_correct_case_ids": newly_correct,
        "regression_count": len(regressions),
        "regression_case_ids": regressions,
        "critical_false_positive_count": len(false_positives),
        "critical_false_positive_case_ids": false_positives,
        "live_control_model_call_count": len(live_control_fallback_rows),
        "candidate_model_call_count": len(candidate_fallback_rows),
        "total_model_call_count": len(live_control_fallback_rows)
        + len(candidate_fallback_rows),
        "candidate_parse_success_count": candidate_parse_success_count,
        "candidate_parse_success_rate": candidate_parse_rate,
        "median_fallback_wall_seconds": median_wall,
        "warm_p95_fallback_wall_seconds": warm_p95,
        "gate_checks": checks,
        "all_gates_pass": all(checks.values()),
        "rows": rows,
    }
