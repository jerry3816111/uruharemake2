#!/usr/bin/env python3
"""Pure parsing and scoring for consolidation-admission cascade V1."""

from __future__ import annotations

import math
import statistics
from collections import Counter

from consolidation_admission_v3_role_separated_core import (
    TARGETS,
    derive_applies_to,
    evidence_grounded,
)


CONTROL = "direct_qwen35_9b_control"
CANDIDATE = "qwen35_4b_to_9b_cascade"
STAGE1_TOOL_NAME = "decide_memory_write"
STAGE1_TOOL_KEYS = {"admission_decision"}
STAGE1_DECISIONS = ("write", "none")


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else 0.0


def _p95(values):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return round(ordered[index], 4)


def _latency(values):
    elapsed = [float(value) for value in values]
    return {
        "mean_wall_seconds": (
            round(statistics.mean(elapsed), 4) if elapsed else 0.0
        ),
        "median_wall_seconds": (
            round(statistics.median(elapsed), 4) if elapsed else 0.0
        ),
        "warm_p95_wall_seconds": _p95(elapsed[1:]),
    }


def _empty_stage1_parse(error, *, raw_content="", raw_tool_calls=None):
    return {
        "admission_decision": "none",
        "parse_success": False,
        "parse_error": error,
        "payload": None,
        "raw_content": raw_content,
        "raw_tool_calls": raw_tool_calls or [],
    }


def parse_write_gate_tool_response(response):
    """Parse the binary gate and fail closed to ``none`` on any drift."""
    message = response.get("message") or {}
    content = str(message.get("content") or "")
    calls = message.get("tool_calls")
    if content.strip():
        return _empty_stage1_parse(
            "narrative_content",
            raw_content=content,
            raw_tool_calls=calls if isinstance(calls, list) else [],
        )
    if not isinstance(calls, list) or len(calls) != 1:
        return _empty_stage1_parse(
            "tool_call_count",
            raw_content=content,
            raw_tool_calls=calls if isinstance(calls, list) else [],
        )
    function = calls[0].get("function") if isinstance(calls[0], dict) else None
    if not isinstance(function, dict):
        return _empty_stage1_parse(
            "function_shape", raw_content=content, raw_tool_calls=calls
        )
    if function.get("name") != STAGE1_TOOL_NAME:
        return _empty_stage1_parse(
            "function_name", raw_content=content, raw_tool_calls=calls
        )
    arguments = function.get("arguments")
    if not isinstance(arguments, dict):
        return _empty_stage1_parse(
            "arguments_type", raw_content=content, raw_tool_calls=calls
        )
    if set(arguments) != STAGE1_TOOL_KEYS:
        return _empty_stage1_parse(
            "argument_keys", raw_content=content, raw_tool_calls=calls
        )
    decision = arguments["admission_decision"]
    if decision not in STAGE1_DECISIONS:
        return _empty_stage1_parse(
            "invalid_admission_decision",
            raw_content=content,
            raw_tool_calls=calls,
        )
    return {
        "admission_decision": decision,
        "parse_success": True,
        "parse_error": None,
        "payload": arguments,
        "raw_content": content,
        "raw_tool_calls": calls,
    }


def deterministic_none_final(case_id, stage1_wall_seconds):
    """Compile a closed gate into a valid final no-write frame."""
    return {
        "id": case_id,
        "condition": CANDIDATE,
        "final_source": "stage1_compiled_none",
        "observed_target": "none",
        "parse_success": True,
        "index_contract_success": True,
        "parse_error": None,
        "memory_kind": "none",
        "persistence_basis": "no_long_term_basis",
        "evidence_user_turns": [],
        "raw_applies_to": "none",
        "compiled_applies_to": "none",
        "payload": None,
        "raw_content": "",
        "raw_tool_calls": [],
        "wall_seconds": round(float(stage1_wall_seconds), 6),
        "transport_attempts": 1,
        "transport_error": None,
    }


def _candidate_rows(cases, stage1_rows, stage2_rows):
    case_ids = {case["id"] for case in cases}
    stage1_by_id = _rows_by_id(stage1_rows, case_ids, "stage1")
    stage2_by_id = _rows_by_id(
        stage2_rows, case_ids, "stage2", exact=False
    )
    write_ids = {
        case_id
        for case_id, row in stage1_by_id.items()
        if row.get("admission_decision") == "write"
    }
    if set(stage2_by_id) != write_ids:
        raise ValueError(
            "stage2 rows must exactly match compiled stage1 writes"
        )

    candidate_rows = []
    for case in cases:
        stage1 = stage1_by_id[case["id"]]
        if stage1["admission_decision"] == "none":
            final = deterministic_none_final(
                case["id"], stage1["wall_seconds"]
            )
        else:
            stage2 = stage2_by_id[case["id"]]
            final = {
                **stage2,
                "condition": CANDIDATE,
                "final_source": "stage2_qwen35_9b",
                "wall_seconds": round(
                    float(stage1["wall_seconds"])
                    + float(stage2["wall_seconds"]),
                    6,
                ),
                "transport_attempts": (
                    int(stage1["transport_attempts"])
                    + int(stage2["transport_attempts"])
                ),
            }
        candidate_rows.append(final)
    return candidate_rows


def _rows_by_id(rows, valid_ids, label, *, exact=True):
    by_id = {row.get("id"): row for row in rows}
    if len(by_id) != len(rows):
        raise ValueError(f"duplicate {label} case IDs")
    if not set(by_id) <= valid_ids:
        raise ValueError(f"{label} rows contain unknown case IDs")
    if exact and set(by_id) != valid_ids:
        raise ValueError(f"{label} rows do not exactly match dataset cases")
    return by_id


def _condition_summary(cases, rows):
    valid_ids = {case["id"] for case in cases}
    row_by_id = _rows_by_id(rows, valid_ids, "condition")
    normalized = []
    for case in cases:
        row = row_by_id[case["id"]]
        observed = row.get("observed_target")
        if observed not in TARGETS:
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
                "correct": observed == expected,
                "semantic_frame_exact": semantic_frame_exact,
                "evidence_grounded": evidence_grounded(case, row),
                "derived_applicability_success": (
                    row.get("compiled_applies_to")
                    == case["expected_applies_to"]
                ),
            }
        )

    class_metrics = {}
    for target in TARGETS:
        selected = [
            row for row in normalized if row["expected_target"] == target
        ]
        correct = sum(bool(row["correct"]) for row in selected)
        class_metrics[target] = {
            "total": len(selected),
            "correct_count": correct,
            "accuracy": _rate(correct, len(selected)),
        }
    correct = sum(bool(row["correct"]) for row in normalized)
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
    summary = {
        "correct_count": correct,
        "accuracy": _rate(correct, len(normalized)),
        "class_metrics": class_metrics,
        "observed_target_counts": dict(
            sorted(Counter(row["observed_target"] for row in normalized).items())
        ),
        "parse_success_count": sum(
            bool(row.get("parse_success")) for row in normalized
        ),
        "index_contract_success_count": sum(
            bool(row.get("index_contract_success")) for row in normalized
        ),
        "semantic_frame_exact_count": sum(
            bool(row["semantic_frame_exact"]) for row in normalized
        ),
        "evidence_grounded_count": sum(
            bool(row["evidence_grounded"]) for row in normalized
        ),
        "positive_evidence_grounded_count": sum(
            bool(row["evidence_grounded"])
            for row in normalized
            if row["expected_target"] != "none"
        ),
        "derived_applicability_success_count": sum(
            bool(row["derived_applicability_success"]) for row in normalized
        ),
        "false_long_term_write_count": len(false_writes),
        "false_long_term_write_case_ids": false_writes,
        "missed_long_term_write_count": len(missed_writes),
        "missed_long_term_write_case_ids": missed_writes,
        "rows": normalized,
        **_latency(row["wall_seconds"] for row in normalized),
    }
    denominator = len(normalized)
    summary.update(
        {
            "parse_success_rate": _rate(
                summary["parse_success_count"], denominator
            ),
            "index_contract_success_rate": _rate(
                summary["index_contract_success_count"], denominator
            ),
            "semantic_frame_exact_rate": _rate(
                summary["semantic_frame_exact_count"], denominator
            ),
            "evidence_grounded_rate": _rate(
                summary["evidence_grounded_count"], denominator
            ),
        }
    )
    return summary


def _stage1_summary(cases, rows):
    case_ids = {case["id"] for case in cases}
    row_by_id = _rows_by_id(rows, case_ids, "stage1")
    positive_ids = {
        case["id"]
        for case in cases
        if case["expected_memory_kind"] != "none"
    }
    negative_ids = case_ids - positive_ids
    write_ids = {
        case_id
        for case_id, row in row_by_id.items()
        if row.get("admission_decision") == "write"
    }
    return {
        "parse_success_count": sum(
            bool(row.get("parse_success")) for row in rows
        ),
        "write_count": len(write_ids),
        "write_case_ids": sorted(write_ids),
        "positive_write_count": len(write_ids & positive_ids),
        "false_write_count": len(write_ids & negative_ids),
        "false_write_case_ids": sorted(write_ids & negative_ids),
        "missed_positive_count": len(positive_ids - write_ids),
        "missed_positive_case_ids": sorted(positive_ids - write_ids),
        **_latency(row["wall_seconds"] for row in rows),
    }


def _stage2_summary(rows):
    parse_count = sum(bool(row.get("parse_success")) for row in rows)
    index_count = sum(
        bool(row.get("index_contract_success")) for row in rows
    )
    return {
        "call_count": len(rows),
        "parse_success_count": parse_count,
        "parse_success_rate": _rate(parse_count, len(rows)),
        "index_contract_success_count": index_count,
        "index_contract_success_rate": _rate(index_count, len(rows)),
        **_latency(row["wall_seconds"] for row in rows),
    }


def _paired(control, candidate):
    control_by_id = {row["id"]: row for row in control["rows"]}
    candidate_by_id = {row["id"]: row for row in candidate["rows"]}
    newly_correct = []
    regressions = []
    matched = []
    for case_id in control_by_id:
        control_row = control_by_id[case_id]
        candidate_row = candidate_by_id[case_id]
        if candidate_row["correct"] and not control_row["correct"]:
            newly_correct.append(case_id)
        if control_row["correct"] and not candidate_row["correct"]:
            regressions.append(case_id)
        matched.append(
            {
                "id": case_id,
                "expected_target": control_row["expected_target"],
                "control_target": control_row["observed_target"],
                "candidate_target": candidate_row["observed_target"],
                "control_correct": control_row["correct"],
                "candidate_correct": candidate_row["correct"],
                "candidate_final_source": candidate_row["final_source"],
                "candidate_semantic_frame_exact": candidate_row[
                    "semantic_frame_exact"
                ],
                "candidate_evidence_grounded": candidate_row[
                    "evidence_grounded"
                ],
            }
        )
    return {
        "accuracy_delta_vs_control": round(
            candidate["accuracy"] - control["accuracy"], 4
        ),
        "net_correct_gain_vs_control": (
            candidate["correct_count"] - control["correct_count"]
        ),
        "newly_correct_count": len(newly_correct),
        "newly_correct_case_ids": newly_correct,
        "regression_count": len(regressions),
        "regression_case_ids": regressions,
        "matched_rows": matched,
    }


def analyze_cascade(
    cases,
    control_rows,
    stage1_rows,
    stage2_rows,
    *,
    success_gates,
    run_invariants,
    model_calls,
    transport_attempts,
):
    """Recompute the complete matched-control cascade decision."""
    candidate_rows = _candidate_rows(cases, stage1_rows, stage2_rows)
    control = _condition_summary(cases, control_rows)
    candidate = _condition_summary(cases, candidate_rows)
    stage1 = _stage1_summary(cases, stage1_rows)
    stage2 = _stage2_summary(stage2_rows)
    paired = _paired(control, candidate)

    checks = {
        "candidate_correct_count_min": candidate["correct_count"]
        >= success_gates["candidate_correct_count_min"],
        "candidate_accuracy_min": candidate["accuracy"]
        >= success_gates["candidate_accuracy_min"],
        "candidate_wisdom_correct_min": candidate["class_metrics"]["wisdom"][
            "correct_count"
        ]
        >= success_gates["candidate_wisdom_correct_min"],
        "candidate_procedural_correct_min": candidate["class_metrics"][
            "procedural"
        ]["correct_count"]
        >= success_gates["candidate_procedural_correct_min"],
        "candidate_none_correct_exact": candidate["class_metrics"]["none"][
            "correct_count"
        ]
        == success_gates["candidate_none_correct_exact"],
        "stage1_parse_success_count_exact": stage1["parse_success_count"]
        == success_gates["stage1_parse_success_count_exact"],
        "stage1_positive_write_count_exact": stage1["positive_write_count"]
        == success_gates["stage1_positive_write_count_exact"],
        "stage1_false_write_count_max": stage1["false_write_count"]
        <= success_gates["stage1_false_write_count_max"],
        "stage2_parse_success_rate_min": stage2["parse_success_rate"]
        >= success_gates["stage2_parse_success_rate_min"],
        "stage2_index_contract_success_rate_min": stage2[
            "index_contract_success_rate"
        ]
        >= success_gates["stage2_index_contract_success_rate_min"],
        "candidate_semantic_frame_exact_count_min": candidate[
            "semantic_frame_exact_count"
        ]
        >= success_gates["candidate_semantic_frame_exact_count_min"],
        "candidate_evidence_grounded_count_min": candidate[
            "evidence_grounded_count"
        ]
        >= success_gates["candidate_evidence_grounded_count_min"],
        "candidate_positive_evidence_grounded_count_min": candidate[
            "positive_evidence_grounded_count"
        ]
        >= success_gates[
            "candidate_positive_evidence_grounded_count_min"
        ],
        "newly_correct_vs_control_min": paired["newly_correct_count"]
        >= success_gates["newly_correct_vs_control_min"],
        "regression_vs_control_max": paired["regression_count"]
        <= success_gates["regression_vs_control_max"],
        "net_correct_gain_vs_control_min": paired[
            "net_correct_gain_vs_control"
        ]
        >= success_gates["net_correct_gain_vs_control_min"],
        "candidate_false_long_term_write_count_exact": candidate[
            "false_long_term_write_count"
        ]
        == success_gates["candidate_false_long_term_write_count_exact"],
        "candidate_missed_long_term_write_count_max": candidate[
            "missed_long_term_write_count"
        ]
        <= success_gates["candidate_missed_long_term_write_count_max"],
        "stage2_call_count_max": stage2["call_count"]
        <= success_gates["stage2_call_count_max"],
        "stage1_median_wall_seconds_max": stage1["median_wall_seconds"]
        <= success_gates["stage1_median_wall_seconds_max"],
        "stage1_warm_p95_wall_seconds_max": stage1[
            "warm_p95_wall_seconds"
        ]
        <= success_gates["stage1_warm_p95_wall_seconds_max"],
        "stage2_median_wall_seconds_max": stage2["median_wall_seconds"]
        <= success_gates["stage2_median_wall_seconds_max"],
        "stage2_warm_p95_wall_seconds_max": stage2[
            "warm_p95_wall_seconds"
        ]
        <= success_gates["stage2_warm_p95_wall_seconds_max"],
        "candidate_mean_session_wall_seconds_max": candidate[
            "mean_wall_seconds"
        ]
        <= success_gates["candidate_mean_session_wall_seconds_max"],
        "candidate_median_session_wall_seconds_max": candidate[
            "median_wall_seconds"
        ]
        <= success_gates["candidate_median_session_wall_seconds_max"],
        "candidate_warm_p95_session_wall_seconds_max": candidate[
            "warm_p95_wall_seconds"
        ]
        <= success_gates[
            "candidate_warm_p95_session_wall_seconds_max"
        ],
        "control_median_wall_seconds_max": control["median_wall_seconds"]
        <= success_gates["control_median_wall_seconds_max"],
        "control_warm_p95_wall_seconds_max": control[
            "warm_p95_wall_seconds"
        ]
        <= success_gates["control_warm_p95_wall_seconds_max"],
    }
    expected_total = (
        run_invariants["control_calls_exact"]
        + run_invariants["stage1_calls_exact"]
        + stage2["call_count"]
    )
    run_checks = {
        "control_calls_exact": len(control_rows)
        == run_invariants["control_calls_exact"],
        "stage1_calls_exact": len(stage1_rows)
        == run_invariants["stage1_calls_exact"],
        "stage2_calls_equal_compiled_stage1_writes": (
            stage2["call_count"] == stage1["write_count"]
        ),
        "total_model_calls_equal": model_calls == expected_total,
        "total_model_calls_max": model_calls
        <= run_invariants["total_model_calls_max"],
        "transport_attempts_equal_model_calls": (
            transport_attempts == model_calls
        ),
    }
    passed = all(checks.values()) and all(run_checks.values())
    return {
        "case_count": len(cases),
        "model_call_count": model_calls,
        "transport_attempt_count": transport_attempts,
        "control": control,
        "candidate": candidate,
        "stage1": stage1,
        "stage2": stage2,
        "paired_vs_control": paired,
        "gate_checks": checks,
        "run_checks": run_checks,
        "all_gates_pass": passed,
        "decision": (
            "pass_authorize_separate_runtime_adapter_development"
            if passed
            else "fail_stop_qwen35_4b_to_9b_cascade"
        ),
    }
