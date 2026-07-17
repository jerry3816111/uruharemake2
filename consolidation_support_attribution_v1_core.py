#!/usr/bin/env python3
"""Pure parsing and scoring for consolidation support attribution V1."""

from __future__ import annotations

import math
import statistics


TOOL_NAME = "attribute_memory_support"
TOOL_KEYS = {"support_event_indices"}
EVENT_INDICES = frozenset(range(1, 7))


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else 0.0


def _p95(values):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return round(ordered[index], 4)


def _empty_parse(error, *, raw_content="", raw_tool_calls=None):
    return {
        "parse_success": False,
        "index_contract_success": False,
        "parse_error": error,
        "support_event_indices": [],
        "raw_content": raw_content,
        "raw_tool_calls": raw_tool_calls or [],
    }


def parse_support_tool_response(response):
    message = response.get("message") or {}
    content = str(message.get("content") or "")
    calls = message.get("tool_calls")
    if content.strip():
        return _empty_parse(
            "narrative_content",
            raw_content=content,
            raw_tool_calls=calls if isinstance(calls, list) else [],
        )
    if not isinstance(calls, list) or len(calls) != 1:
        return _empty_parse(
            "tool_call_count",
            raw_content=content,
            raw_tool_calls=calls if isinstance(calls, list) else [],
        )
    function = (
        calls[0].get("function")
        if isinstance(calls[0], dict)
        else None
    )
    if not isinstance(function, dict):
        return _empty_parse(
            "function_shape",
            raw_content=content,
            raw_tool_calls=calls,
        )
    if function.get("name") != TOOL_NAME:
        return _empty_parse(
            "function_name",
            raw_content=content,
            raw_tool_calls=calls,
        )
    arguments = function.get("arguments")
    if not isinstance(arguments, dict):
        return _empty_parse(
            "arguments_type",
            raw_content=content,
            raw_tool_calls=calls,
        )
    if set(arguments) != TOOL_KEYS:
        return _empty_parse(
            "argument_keys",
            raw_content=content,
            raw_tool_calls=calls,
        )
    indices = arguments["support_event_indices"]
    if not isinstance(indices, list):
        return _empty_parse(
            "indices_type",
            raw_content=content,
            raw_tool_calls=calls,
        )
    valid = (
        all(
            not isinstance(index, bool)
            and isinstance(index, int)
            and index in EVENT_INDICES
            for index in indices
        )
        and len(indices) == len(set(indices))
    )
    if not valid:
        return _empty_parse(
            "index_contract",
            raw_content=content,
            raw_tool_calls=calls,
        )
    return {
        "parse_success": True,
        "index_contract_success": True,
        "parse_error": None,
        "support_event_indices": sorted(indices),
        "raw_content": content,
        "raw_tool_calls": calls,
    }


def build_coarse_control_rows(cases):
    return [
        {
            "id": case["id"],
            "condition": "coarse_all_source_ids_control",
            "parse_success": True,
            "index_contract_success": True,
            "parse_error": None,
            "support_event_indices": list(range(1, 7)),
            "wall_seconds": 0.0,
            "transport_attempts": 0,
            "transport_error": None,
        }
        for case in cases
    ]


def _case_score(case, row):
    expected = set(case["gold_support_event_indices"])
    predicted = set(row.get("support_event_indices") or [])
    true_positive = len(expected & predicted)
    false_positive = len(predicted - expected)
    false_negative = len(expected - predicted)
    if not expected:
        case_f1 = 1.0 if not predicted else 0.0
    else:
        denominator = (2 * true_positive) + false_positive + false_negative
        case_f1 = (
            (2 * true_positive) / denominator if denominator else 0.0
        )
    return {
        "id": case["id"],
        "language": case["language"],
        "memory_kind": case["memory_kind"],
        "support_mode": case["support_mode"],
        "expected_indices": sorted(expected),
        "predicted_indices": sorted(predicted),
        "exact_set_match": predicted == expected,
        "complete_positive_support": bool(expected)
        and expected <= predicted,
        "unsupported_empty": not expected and not predicted,
        "true_positive_count": true_positive,
        "false_positive_count": false_positive,
        "false_negative_count": false_negative,
        "case_f1": round(case_f1, 4),
        "parse_success": bool(row.get("parse_success")),
        "index_contract_success": bool(
            row.get("index_contract_success")
        ),
        "transport_error": row.get("transport_error"),
    }


def summarize_condition(cases, rows):
    case_by_id = {case["id"]: case for case in cases}
    row_by_id = {row["id"]: row for row in rows}
    if len(case_by_id) != len(cases):
        raise ValueError("duplicate case IDs")
    if len(row_by_id) != len(rows):
        raise ValueError("duplicate result IDs")
    if set(case_by_id) != set(row_by_id):
        raise ValueError("result rows do not match dataset cases")
    scored = [
        _case_score(case, row_by_id[case["id"]])
        for case in cases
    ]
    true_positive = sum(row["true_positive_count"] for row in scored)
    false_positive = sum(
        row["false_positive_count"] for row in scored
    )
    false_negative = sum(
        row["false_negative_count"] for row in scored
    )
    elapsed = [
        float(row.get("wall_seconds") or 0.0)
        for row in rows
        if float(row.get("wall_seconds") or 0.0) > 0.0
    ]
    return {
        "case_count": len(cases),
        "exact_set_match_count": sum(
            row["exact_set_match"] for row in scored
        ),
        "exact_set_accuracy": _rate(
            sum(row["exact_set_match"] for row in scored),
            len(scored),
        ),
        "positive_complete_support_count": sum(
            row["complete_positive_support"] for row in scored
        ),
        "unsupported_empty_count": sum(
            row["unsupported_empty"] for row in scored
        ),
        "evidence_precision": _rate(
            true_positive,
            true_positive + false_positive,
        ),
        "evidence_recall": _rate(
            true_positive,
            true_positive + false_negative,
        ),
        "mean_case_f1": round(
            statistics.mean(row["case_f1"] for row in scored),
            4,
        ),
        "false_source_count": false_positive,
        "missed_source_count": false_negative,
        "parse_success_count": sum(
            row["parse_success"] for row in scored
        ),
        "index_contract_success_count": sum(
            row["index_contract_success"] for row in scored
        ),
        "transport_error_count": sum(
            bool(row["transport_error"]) for row in scored
        ),
        "median_wall_seconds": (
            round(statistics.median(elapsed), 4) if elapsed else 0.0
        ),
        "warm_p95_wall_seconds": _p95(elapsed[1:]),
        "scored_cases": scored,
    }


def analyze_support_attribution(cases, control_rows, candidate_rows, gates):
    control = summarize_condition(cases, control_rows)
    candidate = summarize_condition(cases, candidate_rows)
    control_by_id = {
        row["id"]: row for row in control["scored_cases"]
    }
    candidate_by_id = {
        row["id"]: row for row in candidate["scored_cases"]
    }
    paired = []
    for case in cases:
        control_row = control_by_id[case["id"]]
        candidate_row = candidate_by_id[case["id"]]
        paired.append(
            {
                "id": case["id"],
                "language": case["language"],
                "support_mode": case["support_mode"],
                "control_exact": control_row["exact_set_match"],
                "candidate_exact": candidate_row["exact_set_match"],
                "newly_exact": (
                    candidate_row["exact_set_match"]
                    and not control_row["exact_set_match"]
                ),
                "regression": (
                    control_row["exact_set_match"]
                    and not candidate_row["exact_set_match"]
                ),
                "candidate_expected_indices": candidate_row[
                    "expected_indices"
                ],
                "candidate_predicted_indices": candidate_row[
                    "predicted_indices"
                ],
            }
        )
    observed = {
        "candidate_exact_set_match_count_min": candidate[
            "exact_set_match_count"
        ],
        "candidate_positive_complete_support_count_min": candidate[
            "positive_complete_support_count"
        ],
        "candidate_unsupported_empty_count_min": candidate[
            "unsupported_empty_count"
        ],
        "candidate_evidence_precision_min": candidate[
            "evidence_precision"
        ],
        "candidate_evidence_recall_min": candidate[
            "evidence_recall"
        ],
        "candidate_mean_case_f1_gain_min": round(
            candidate["mean_case_f1"] - control["mean_case_f1"],
            4,
        ),
        "candidate_false_source_count_max": candidate[
            "false_source_count"
        ],
        "candidate_missed_source_count_max": candidate[
            "missed_source_count"
        ],
        "candidate_parse_success_count_exact": candidate[
            "parse_success_count"
        ],
        "candidate_index_contract_success_count_exact": candidate[
            "index_contract_success_count"
        ],
        "candidate_transport_error_count_exact": candidate[
            "transport_error_count"
        ],
        "candidate_median_wall_seconds_max": candidate[
            "median_wall_seconds"
        ],
        "candidate_warm_p95_wall_seconds_max": candidate[
            "warm_p95_wall_seconds"
        ],
    }
    gate_results = {}
    for key, value in observed.items():
        required = gates[key]
        if key.endswith("_min"):
            passed = value >= required
            comparison = "minimum"
        elif key.endswith("_max"):
            passed = value <= required
            comparison = "maximum"
        else:
            passed = value == required
            comparison = "exact"
        gate_results[key] = {
            "required": required,
            "observed": value,
            "comparison": comparison,
            "passed": passed,
        }
    return {
        "control": control,
        "candidate": candidate,
        "paired": paired,
        "newly_exact_count": sum(row["newly_exact"] for row in paired),
        "regression_count": sum(row["regression"] for row in paired),
        "gates": gate_results,
        "all_success_gates_pass": all(
            row["passed"] for row in gate_results.values()
        ),
    }
