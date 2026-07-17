#!/usr/bin/env python3
"""Pure parsing and scoring for the V6 reflection-admission pilot."""

from __future__ import annotations

import math
import statistics
from collections import Counter


ADMISSIONS = ("admit", "reject")
REASON_CODES = {
    "explicit_future_instruction",
    "explicit_recurring_signal_instruction",
    "speaker_intention_or_promise",
    "question",
    "wish_or_farewell",
    "fragment",
    "third_party_or_event",
    "one_time_non_durable",
    "insufficient_evidence",
}


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else 0.0


def _p95(values):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return round(ordered[index], 4)


def parse_admission_tool_response(response, utterance):
    message = response.get("message") or {}
    raw_content = str(message.get("content") or "")
    raw_tool_calls = message.get("tool_calls")
    if not isinstance(raw_tool_calls, list):
        return None, False, False, raw_content, raw_tool_calls, "missing_tool_calls"
    if len(raw_tool_calls) != 1:
        return None, False, False, raw_content, raw_tool_calls, "tool_call_count"
    function = raw_tool_calls[0].get("function") or {}
    if function.get("name") != "verify_reflection_admission":
        return None, False, False, raw_content, raw_tool_calls, "tool_name"
    arguments = function.get("arguments")
    if not isinstance(arguments, dict):
        return None, False, False, raw_content, raw_tool_calls, "arguments_type"
    expected_keys = {"admission", "evidence_span", "reason_code"}
    if set(arguments) != expected_keys:
        return None, False, False, raw_content, raw_tool_calls, "argument_keys"
    if arguments["admission"] not in ADMISSIONS:
        return None, False, False, raw_content, raw_tool_calls, "invalid_admission"
    if not isinstance(arguments["evidence_span"], str):
        return None, False, False, raw_content, raw_tool_calls, "evidence_span_type"
    if arguments["reason_code"] not in REASON_CODES:
        return None, False, False, raw_content, raw_tool_calls, "invalid_reason_code"
    evidence_span = arguments["evidence_span"]
    if arguments["admission"] == "admit":
        evidence_contract = bool(evidence_span) and evidence_span in utterance
    else:
        evidence_contract = evidence_span == ""
    return (
        dict(arguments),
        True,
        evidence_contract,
        raw_content,
        raw_tool_calls,
        None,
    )


def analyze_admission_condition(cases, candidate_rows, gates):
    case_by_id = {case["id"]: case for case in cases}
    candidate_by_id = {row["id"]: row for row in candidate_rows}
    if len(case_by_id) != len(cases):
        raise ValueError("duplicate dataset case IDs")
    if len(candidate_by_id) != len(candidate_rows):
        raise ValueError("duplicate candidate case IDs")
    if set(candidate_by_id) != set(case_by_id):
        raise ValueError("candidate rows do not exactly match dataset cases")

    rows = []
    for case in cases:
        candidate = candidate_by_id[case["id"]]
        control = "admit"
        observed = candidate["observed_admission"]
        if observed not in ADMISSIONS:
            raise ValueError(f"invalid observed admission: {case['id']}")
        expected = case["expected_admission"]
        rows.append(
            {
                "id": case["id"],
                "language": case["language"],
                "expected_admission": expected,
                "control_admission": control,
                "candidate_admission": observed,
                "control_correct": control == expected,
                "candidate_correct": observed == expected,
                "parse_success": candidate["parse_success"],
                "evidence_contract_success": candidate[
                    "evidence_contract_success"
                ],
            }
        )

    class_metrics = {}
    for admission in ADMISSIONS:
        selected = [
            row for row in rows if row["expected_admission"] == admission
        ]
        correct = sum(row["candidate_correct"] for row in selected)
        class_metrics[admission] = {
            "total": len(selected),
            "correct": correct,
            "accuracy": _rate(correct, len(selected)),
        }
    control_correct = sum(row["control_correct"] for row in rows)
    candidate_correct = sum(row["candidate_correct"] for row in rows)
    newly_correct = [
        row["id"]
        for row in rows
        if row["candidate_correct"] and not row["control_correct"]
    ]
    regressions = [
        row["id"]
        for row in rows
        if row["control_correct"] and not row["candidate_correct"]
    ]
    false_admits = [
        row["id"]
        for row in rows
        if row["expected_admission"] == "reject"
        and row["candidate_admission"] == "admit"
    ]
    false_rejects = [
        row["id"]
        for row in rows
        if row["expected_admission"] == "admit"
        and row["candidate_admission"] == "reject"
    ]
    parse_success_count = sum(row["parse_success"] for row in candidate_rows)
    evidence_success_count = sum(
        row["evidence_contract_success"] for row in candidate_rows
    )
    parse_rate = _rate(parse_success_count, len(candidate_rows))
    evidence_rate = _rate(evidence_success_count, len(candidate_rows))
    elapsed = [float(row["wall_seconds"]) for row in candidate_rows]
    median_wall = round(statistics.median(elapsed), 4) if elapsed else 0.0
    warm_p95 = _p95(elapsed[1:])
    net_gain = candidate_correct - control_correct

    checks = {
        "control_correct_count_exact": control_correct
        == gates["control_correct_count_exact"],
        "candidate_correct_count_min": candidate_correct
        >= gates["candidate_correct_count_min"],
        "candidate_accuracy_min": _rate(candidate_correct, len(rows))
        >= gates["candidate_accuracy_min"],
        "candidate_admit_correct_min": class_metrics["admit"]["correct"]
        >= gates["candidate_admit_correct_min"],
        "candidate_reject_correct_min": class_metrics["reject"]["correct"]
        >= gates["candidate_reject_correct_min"],
        "newly_correct_vs_control_min": len(newly_correct)
        >= gates["newly_correct_vs_control_min"],
        "regression_vs_control_max": len(regressions)
        <= gates["regression_vs_control_max"],
        "net_gain_vs_control_min": net_gain >= gates["net_gain_vs_control_min"],
        "false_admit_count_max": len(false_admits)
        <= gates["false_admit_count_max"],
        "false_reject_count_max": len(false_rejects)
        <= gates["false_reject_count_max"],
        "parse_success_rate_min": parse_rate >= gates["parse_success_rate_min"],
        "evidence_contract_success_rate_min": evidence_rate
        >= gates["evidence_contract_success_rate_min"],
        "model_call_count_exact": len(candidate_rows)
        == gates["model_call_count_exact"],
        "median_wall_seconds_max": median_wall
        <= gates["median_wall_seconds_max"],
        "warm_p95_wall_seconds_max": warm_p95
        <= gates["warm_p95_wall_seconds_max"],
    }
    return {
        "case_count": len(rows),
        "control_correct_count": control_correct,
        "control_accuracy": _rate(control_correct, len(rows)),
        "candidate_correct_count": candidate_correct,
        "candidate_accuracy": _rate(candidate_correct, len(rows)),
        "accuracy_delta_vs_control": round(
            _rate(candidate_correct, len(rows))
            - _rate(control_correct, len(rows)),
            4,
        ),
        "net_correct_gain_vs_control": net_gain,
        "class_metrics": class_metrics,
        "observed_admission_counts": dict(
            sorted(Counter(row["candidate_admission"] for row in rows).items())
        ),
        "newly_correct_count": len(newly_correct),
        "newly_correct_case_ids": newly_correct,
        "regression_count": len(regressions),
        "regression_case_ids": regressions,
        "false_admit_count": len(false_admits),
        "false_admit_case_ids": false_admits,
        "false_reject_count": len(false_rejects),
        "false_reject_case_ids": false_rejects,
        "model_call_count": len(candidate_rows),
        "parse_success_count": parse_success_count,
        "parse_success_rate": parse_rate,
        "evidence_contract_success_count": evidence_success_count,
        "evidence_contract_success_rate": evidence_rate,
        "median_wall_seconds": median_wall,
        "warm_p95_wall_seconds": warm_p95,
        "gate_checks": checks,
        "all_gates_pass": all(checks.values()),
        "rows": rows,
    }
