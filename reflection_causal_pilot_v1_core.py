#!/usr/bin/env python3
"""Pure scoring helpers for the preregistered reflection causal pilot."""

from __future__ import annotations

import re
from collections import Counter


POSITIVE_CATEGORIES = {
    "stable_user_fact",
    "interaction_strategy",
    "interaction_interpretation",
}
INTERACTION_CATEGORIES = {
    "interaction_strategy",
    "interaction_interpretation",
}


def normalize_text(value):
    return re.sub(r"\s+", "", str(value or "")).lower()


def contains_any(value, terms):
    normalized = normalize_text(value)
    return any(normalize_text(term) in normalized for term in terms or [])


def behavior_success(case, condition):
    reply = str(condition.get("future_reply") or "")
    required = case.get("behavior_required_any") or []
    forbidden = case.get("behavior_forbidden_any") or []
    required_ok = not required or contains_any(reply, required)
    forbidden_ok = not contains_any(reply, forbidden)
    question_ok = sum(reply.count(mark) for mark in ("?", "？")) <= int(
        case.get("behavior_max_question_marks", 999)
    )
    length_ok = len(reply.strip()) <= int(case.get("behavior_max_chars", 99999))
    return bool(required_ok and forbidden_ok and question_ok and length_ok)


def valid_rule(case, condition):
    documents = condition.get("reflection_documents") or []
    if not documents:
        return case.get("expected_rule_kind") == "none"
    combined = "\n".join(str(item) for item in documents)
    required = case.get("rule_required_any") or []
    forbidden = case.get("rule_forbidden_any") or []
    return bool(required and contains_any(combined, required) and not contains_any(combined, forbidden))


def score_rows(raw_rows):
    scored = []
    for row in raw_rows:
        case = row["case"]
        control = row["conditions"]["episodic_memory_only_control"]
        treatment = row["conditions"]["same_episodic_memory_plus_current_reflection_treatment"]
        expected_rule = case.get("expected_rule_kind") != "none"
        treatment_wrote = bool(treatment.get("reflection_documents"))
        control_success = behavior_success(case, control)
        treatment_success = behavior_success(case, treatment)
        treatment_rule_valid = valid_rule(case, treatment)
        scored.append(
            {
                "id": case["id"],
                "language": case["language"],
                "category": case["category"],
                "expected_rule_kind": case["expected_rule_kind"],
                "expected_rule": expected_rule,
                "treatment_wrote_rule": treatment_wrote,
                "treatment_rule_valid": treatment_rule_valid,
                "treatment_retrieved_reflection": bool(
                    treatment.get("retrieved_reflection")
                ),
                "control_behavior_success": control_success,
                "treatment_behavior_success": treatment_success,
                "paired_gain": bool(treatment_success and not control_success),
                "paired_regression": bool(control_success and not treatment_success),
                "reply_changed": normalize_text(control.get("future_reply"))
                != normalize_text(treatment.get("future_reply")),
                "control_reply": control.get("future_reply") or "",
                "treatment_reply": treatment.get("future_reply") or "",
                "reflection_documents": treatment.get("reflection_documents") or [],
                "treatment_working_memory": treatment.get("working_memory_items") or [],
            }
        )
    return scored


def _rate(rows, predicate):
    if not rows:
        return 0.0
    return round(sum(1 for row in rows if predicate(row)) / len(rows), 4)


def summarize(scored_rows, gates):
    positive = [row for row in scored_rows if row["expected_rule"]]
    negative = [row for row in scored_rows if not row["expected_rule"]]
    written = [row for row in scored_rows if row["treatment_wrote_rule"]]
    valid_written = [
        row
        for row in positive
        if row["treatment_wrote_rule"] and row["treatment_rule_valid"]
    ]
    gains = [row for row in positive if row["paired_gain"]]
    regressions = [row for row in scored_rows if row["paired_regression"]]
    interaction_gains = [
        row for row in gains if row["category"] in INTERACTION_CATEGORIES
    ]
    control_rate = _rate(positive, lambda row: row["control_behavior_success"])
    treatment_rate = _rate(positive, lambda row: row["treatment_behavior_success"])
    summary = {
        "case_count": len(scored_rows),
        "positive_case_count": len(positive),
        "negative_control_count": len(negative),
        "expected_rule_write_recall": _rate(
            positive, lambda row: row["treatment_wrote_rule"]
        ),
        "valid_rule_precision": _rate(
            written, lambda row: row["expected_rule"] and row["treatment_rule_valid"]
        ),
        "no_rule_specificity": _rate(
            negative, lambda row: not row["treatment_wrote_rule"]
        ),
        "valid_rule_retrieval_rate": _rate(
            valid_written, lambda row: row["treatment_retrieved_reflection"]
        ),
        "control_behavior_success_rate": control_rate,
        "treatment_behavior_success_rate": treatment_rate,
        "treatment_behavior_delta": round(treatment_rate - control_rate, 4),
        "paired_behavior_gains": len(gains),
        "paired_behavior_regressions": len(regressions),
        "paired_behavior_net_gain": len(gains) - len(regressions),
        "interaction_category_paired_gains": len(interaction_gains),
        "reply_changed_rate": _rate(scored_rows, lambda row: row["reply_changed"]),
        "rule_writes_by_category": dict(
            Counter(
                row["category"]
                for row in scored_rows
                if row["treatment_wrote_rule"]
            )
        ),
        "behavior_gains_by_category": dict(
            Counter(row["category"] for row in gains)
        ),
    }
    gate_checks = {
        "expected_rule_write_recall": summary["expected_rule_write_recall"]
        >= gates["expected_rule_write_recall_min"],
        "valid_rule_precision": summary["valid_rule_precision"]
        >= gates["valid_rule_precision_min"],
        "no_rule_specificity": summary["no_rule_specificity"]
        >= gates["no_rule_specificity_min"],
        "valid_rule_retrieval_rate": summary["valid_rule_retrieval_rate"]
        >= gates["valid_rule_retrieval_rate_min"],
        "treatment_behavior_delta": summary["treatment_behavior_delta"]
        >= gates["treatment_behavior_delta_min"],
        "paired_behavior_net_gain": summary["paired_behavior_net_gain"]
        >= gates["paired_behavior_net_gain_min"],
        "interaction_category_paired_gains": summary[
            "interaction_category_paired_gains"
        ]
        >= gates["interaction_category_paired_gains_min"],
        "paired_behavior_regressions": summary["paired_behavior_regressions"]
        <= gates["paired_behavior_regressions_max"],
    }
    summary["gate_checks"] = gate_checks
    summary["all_gates_pass"] = all(gate_checks.values())
    return summary
