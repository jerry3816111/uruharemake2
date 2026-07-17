#!/usr/bin/env python3
"""Pure parsing, compilation, and scoring for consolidation admission V1."""

from __future__ import annotations

import json
import math
import re
import statistics
from collections import Counter


TARGETS = ("wisdom", "procedural", "none")
OBSERVED_TARGETS = (*TARGETS, "multiple")
_KANA_RE = re.compile(r"[ぁ-ゖァ-ヺ]")


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else 0.0


def _p95(values):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return round(ordered[index], 4)


def _extract_jsonish_payload(text):
    text = str(text or "").strip()
    if not text:
        return None, "empty_response"
    candidates = [text]
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        candidates.append(fenced.group(1))
    embedded = re.search(r"(\{.*\})", text, re.DOTALL)
    if embedded:
        candidates.append(embedded.group(1))
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except (TypeError, ValueError):
            continue
        if isinstance(payload, dict):
            return payload, None
    return None, "no_valid_json_object"


def _response_content(response):
    message = response.get("message") or {}
    return str(message.get("content") or "")


def parse_control_response(response):
    content = _response_content(response)
    payload, error = _extract_jsonish_payload(content)
    if payload is None:
        return {
            "observed_target": "none",
            "parse_success": False,
            "parse_error": error,
            "payload": None,
            "raw_content": content,
        }
    wisdom = str(payload.get("wisdom_rule", "NO_RULE")).strip()
    procedural = str(payload.get("procedural_rule", "NO_RULE")).strip()
    has_wisdom = bool(wisdom) and wisdom != "NO_RULE"
    has_procedural = bool(procedural) and procedural != "NO_RULE"
    if has_wisdom and has_procedural:
        observed = "multiple"
    elif has_wisdom:
        observed = "wisdom"
    elif has_procedural:
        observed = "procedural"
    else:
        observed = "none"
    return {
        "observed_target": observed,
        "parse_success": True,
        "parse_error": None,
        "payload": payload,
        "raw_content": content,
    }


def _candidate_shape_error(payload, condition):
    if set(payload) != set(condition["required_keys"]):
        return "payload_keys"
    if not isinstance(payload["episodic_summary"], str):
        return "episodic_summary_type"
    if not payload["episodic_summary"].strip():
        return "episodic_summary_empty"
    for key in ("candidate_kind", "scope", "target"):
        if payload[key] not in condition["enums"][key]:
            return f"invalid_{key}"
    if not isinstance(payload["rule_jp"], str):
        return "rule_jp_type"
    evidence = payload["evidence_quotes"]
    if not isinstance(evidence, list) or any(
        not isinstance(quote, str) for quote in evidence
    ):
        return "evidence_quotes_type"
    confidence = payload["confidence"]
    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not math.isfinite(float(confidence))
        or not 0.0 <= float(confidence) <= 1.0
    ):
        return "confidence_range"
    return None


def _evidence_contract(payload, user_utterances):
    quotes = payload["evidence_quotes"]
    exact_unique_quotes = (
        all(bool(quote) and quote in user_utterances for quote in quotes)
        and len(quotes) == len(set(quotes))
    )
    if not exact_unique_quotes:
        return False
    if payload["candidate_kind"] in {"wisdom", "procedural"}:
        return len(quotes) >= 1
    return True


def _japanese_rule_contract(payload):
    if payload["candidate_kind"] == "none":
        return payload["rule_jp"] == "NO_RULE"
    return (
        payload["rule_jp"] != "NO_RULE"
        and bool(_KANA_RE.search(payload["rule_jp"]))
    )


def compile_candidate_target(
    payload,
    *,
    evidence_contract_success,
    japanese_rule_contract_success,
):
    if not evidence_contract_success or not japanese_rule_contract_success:
        return "none"
    kind = payload["candidate_kind"]
    scope = payload["scope"]
    target = payload["target"]
    evidence_count = len(payload["evidence_quotes"])
    if (
        kind == "wisdom"
        and target == "user"
        and scope in {"stable", "repeated"}
        and evidence_count >= (2 if scope == "repeated" else 1)
    ):
        return "wisdom"
    if (
        kind == "procedural"
        and target == "assistant"
        and scope == "recurring"
        and evidence_count >= 1
    ):
        return "procedural"
    return "none"


def parse_candidate_response(response, user_utterances, condition):
    content = _response_content(response)
    payload, error = _extract_jsonish_payload(content)
    if payload is None:
        return {
            "observed_target": "none",
            "parse_success": False,
            "evidence_contract_success": False,
            "japanese_rule_contract_success": False,
            "parse_error": error,
            "payload": None,
            "raw_content": content,
        }
    shape_error = _candidate_shape_error(payload, condition)
    if shape_error:
        return {
            "observed_target": "none",
            "parse_success": False,
            "evidence_contract_success": False,
            "japanese_rule_contract_success": False,
            "parse_error": shape_error,
            "payload": payload,
            "raw_content": content,
        }
    evidence_success = _evidence_contract(payload, user_utterances)
    japanese_success = _japanese_rule_contract(payload)
    observed = compile_candidate_target(
        payload,
        evidence_contract_success=evidence_success,
        japanese_rule_contract_success=japanese_success,
    )
    return {
        "observed_target": observed,
        "parse_success": True,
        "evidence_contract_success": evidence_success,
        "japanese_rule_contract_success": japanese_success,
        "parse_error": None,
        "payload": payload,
        "raw_content": content,
    }


def _condition_summary(rows):
    correct = sum(row["correct"] for row in rows)
    elapsed = [float(row["wall_seconds"]) for row in rows]
    return {
        "correct_count": correct,
        "accuracy": _rate(correct, len(rows)),
        "observed_target_counts": dict(
            sorted(Counter(row["observed_target"] for row in rows).items())
        ),
        "parse_success_count": sum(row["parse_success"] for row in rows),
        "parse_success_rate": _rate(
            sum(row["parse_success"] for row in rows), len(rows)
        ),
        "median_wall_seconds": (
            round(statistics.median(elapsed), 4) if elapsed else 0.0
        ),
        "warm_p95_wall_seconds": _p95(elapsed[1:]),
    }


def analyze_conditions(cases, control_rows, candidate_rows, gates):
    case_by_id = {case["id"]: case for case in cases}
    control_by_id = {row["id"]: row for row in control_rows}
    candidate_by_id = {row["id"]: row for row in candidate_rows}
    if len(case_by_id) != len(cases):
        raise ValueError("duplicate dataset case IDs")
    if len(control_by_id) != len(control_rows):
        raise ValueError("duplicate control case IDs")
    if len(candidate_by_id) != len(candidate_rows):
        raise ValueError("duplicate candidate case IDs")
    if set(control_by_id) != set(case_by_id):
        raise ValueError("control rows do not exactly match dataset cases")
    if set(candidate_by_id) != set(case_by_id):
        raise ValueError("candidate rows do not exactly match dataset cases")

    matched_rows = []
    for case in cases:
        expected = case["expected_long_term_target"]
        control = control_by_id[case["id"]]
        candidate = candidate_by_id[case["id"]]
        control_observed = control["observed_target"]
        candidate_observed = candidate["observed_target"]
        if control_observed not in OBSERVED_TARGETS:
            raise ValueError(f"invalid control target: {case['id']}")
        if candidate_observed not in TARGETS:
            raise ValueError(f"invalid candidate target: {case['id']}")
        matched_rows.append(
            {
                "id": case["id"],
                "language": case["language"],
                "expected_target": expected,
                "control_target": control_observed,
                "candidate_target": candidate_observed,
                "control_correct": control_observed == expected,
                "candidate_correct": candidate_observed == expected,
            }
        )

    normalized_control = [
        {
            **row,
            "correct": row["observed_target"]
            == case_by_id[row["id"]]["expected_long_term_target"],
        }
        for row in control_rows
    ]
    normalized_candidate = [
        {
            **row,
            "correct": row["observed_target"]
            == case_by_id[row["id"]]["expected_long_term_target"],
        }
        for row in candidate_rows
    ]
    control_summary = _condition_summary(normalized_control)
    candidate_summary = _condition_summary(normalized_candidate)

    class_metrics = {}
    for target in TARGETS:
        selected = [
            row for row in matched_rows if row["expected_target"] == target
        ]
        candidate_correct = sum(row["candidate_correct"] for row in selected)
        class_metrics[target] = {
            "total": len(selected),
            "candidate_correct": candidate_correct,
            "candidate_accuracy": _rate(candidate_correct, len(selected)),
        }

    newly_correct = [
        row["id"]
        for row in matched_rows
        if row["candidate_correct"] and not row["control_correct"]
    ]
    regressions = [
        row["id"]
        for row in matched_rows
        if row["control_correct"] and not row["candidate_correct"]
    ]
    false_writes = [
        row["id"]
        for row in matched_rows
        if row["expected_target"] == "none"
        and row["candidate_target"] in {"wisdom", "procedural"}
    ]
    missed_writes = [
        row["id"]
        for row in matched_rows
        if row["expected_target"] in {"wisdom", "procedural"}
        and row["candidate_target"] == "none"
    ]
    evidence_count = sum(
        row["evidence_contract_success"] for row in candidate_rows
    )
    japanese_count = sum(
        row["japanese_rule_contract_success"] for row in candidate_rows
    )
    candidate_parse_rate = candidate_summary["parse_success_rate"]
    evidence_rate = _rate(evidence_count, len(candidate_rows))
    japanese_rate = _rate(japanese_count, len(candidate_rows))
    net_gain = (
        candidate_summary["correct_count"] - control_summary["correct_count"]
    )
    total_model_calls = len(control_rows) + len(candidate_rows)

    checks = {
        "candidate_correct_count_min": candidate_summary["correct_count"]
        >= gates["candidate_correct_count_min"],
        "candidate_accuracy_min": candidate_summary["accuracy"]
        >= gates["candidate_accuracy_min"],
        "candidate_wisdom_correct_min": class_metrics["wisdom"][
            "candidate_correct"
        ]
        >= gates["candidate_wisdom_correct_min"],
        "candidate_procedural_correct_min": class_metrics["procedural"][
            "candidate_correct"
        ]
        >= gates["candidate_procedural_correct_min"],
        "candidate_none_correct_min": class_metrics["none"][
            "candidate_correct"
        ]
        >= gates["candidate_none_correct_min"],
        "newly_correct_vs_control_min": len(newly_correct)
        >= gates["newly_correct_vs_control_min"],
        "regression_vs_control_max": len(regressions)
        <= gates["regression_vs_control_max"],
        "net_correct_gain_vs_control_min": net_gain
        >= gates["net_correct_gain_vs_control_min"],
        "candidate_false_long_term_write_count_max": len(false_writes)
        <= gates["candidate_false_long_term_write_count_max"],
        "candidate_missed_long_term_write_count_max": len(missed_writes)
        <= gates["candidate_missed_long_term_write_count_max"],
        "candidate_parse_success_rate_min": candidate_parse_rate
        >= gates["candidate_parse_success_rate_min"],
        "candidate_evidence_contract_success_rate_min": evidence_rate
        >= gates["candidate_evidence_contract_success_rate_min"],
        "candidate_japanese_rule_contract_success_rate_min": japanese_rate
        >= gates["candidate_japanese_rule_contract_success_rate_min"],
        "model_call_count_exact": total_model_calls
        == gates["model_call_count_exact"],
        "control_median_wall_seconds_max": control_summary[
            "median_wall_seconds"
        ]
        <= gates["control_median_wall_seconds_max"],
        "candidate_median_wall_seconds_max": candidate_summary[
            "median_wall_seconds"
        ]
        <= gates["candidate_median_wall_seconds_max"],
        "control_warm_p95_wall_seconds_max": control_summary[
            "warm_p95_wall_seconds"
        ]
        <= gates["control_warm_p95_wall_seconds_max"],
        "candidate_warm_p95_wall_seconds_max": candidate_summary[
            "warm_p95_wall_seconds"
        ]
        <= gates["candidate_warm_p95_wall_seconds_max"],
    }
    return {
        "case_count": len(matched_rows),
        "model_call_count": total_model_calls,
        "control": control_summary,
        "candidate": {
            **candidate_summary,
            "evidence_contract_success_count": evidence_count,
            "evidence_contract_success_rate": evidence_rate,
            "japanese_rule_contract_success_count": japanese_count,
            "japanese_rule_contract_success_rate": japanese_rate,
        },
        "accuracy_delta_vs_control": round(
            candidate_summary["accuracy"] - control_summary["accuracy"], 4
        ),
        "net_correct_gain_vs_control": net_gain,
        "class_metrics": class_metrics,
        "newly_correct_count": len(newly_correct),
        "newly_correct_case_ids": newly_correct,
        "regression_count": len(regressions),
        "regression_case_ids": regressions,
        "candidate_false_long_term_write_count": len(false_writes),
        "candidate_false_long_term_write_case_ids": false_writes,
        "candidate_missed_long_term_write_count": len(missed_writes),
        "candidate_missed_long_term_write_case_ids": missed_writes,
        "gate_checks": checks,
        "all_gates_pass": all(checks.values()),
        "matched_rows": matched_rows,
    }
