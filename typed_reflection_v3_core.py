#!/usr/bin/env python3
"""Pure scoring helpers for the preregistered typed-reflection V3 pilot."""

from __future__ import annotations

import re
from collections import Counter


POSITIVE_CATEGORIES = {
    "semantic_user_fact",
    "procedural_interaction_rule",
    "interpretive_interaction_rule",
}
INTERACTION_CATEGORIES = {
    "procedural_interaction_rule",
    "interpretive_interaction_rule",
}


def normalize_text(value):
    return re.sub(r"\s+", "", str(value or "")).lower()


def contains_any(value, terms):
    normalized = normalize_text(value)
    return any(normalize_text(term) in normalized for term in terms or [])


def first_clause(value):
    return re.split(r"[。！？!?、,，；;:]", str(value or ""), maxsplit=1)[0]


def behavior_success(case, condition):
    reply = str(condition.get("future_reply") or "").strip()
    required = case.get("behavior_required_any") or []
    forbidden = case.get("behavior_forbidden_any") or []
    first_required = case.get("behavior_first_clause_required_any") or []
    return bool(
        reply
        and (not required or contains_any(reply, required))
        and not contains_any(reply, forbidden)
        and (not first_required or contains_any(first_clause(reply), first_required))
        and sum(reply.count(mark) for mark in ("?", "？"))
        <= int(case.get("behavior_max_question_marks", 999))
        and len(reply) <= int(case.get("behavior_max_chars", 99999))
    )


def valid_reflection(case, condition):
    records = condition.get("reflection_records") or []
    if not records:
        return case.get("expected_reflection_type") == "none"
    combined = "\n".join(str(record.get("document") or "") for record in records)
    return bool(
        case.get("expected_reflection_type") != "none"
        and condition.get("reflection_type_observed")
        == case.get("expected_reflection_type")
        and contains_any(combined, case.get("rule_required_any") or [])
    )


def score_rows(raw_rows, control_name, treatment_name):
    scored = []
    for row in raw_rows:
        case = row["case"]
        control = row["conditions"][control_name]
        treatment = row["conditions"][treatment_name]
        expected_type = case["expected_reflection_type"]
        expected_write = expected_type != "none"
        records = treatment.get("reflection_records") or []
        wrote = bool(records)
        valid = valid_reflection(case, treatment)
        control_success = behavior_success(case, control)
        treatment_success = behavior_success(case, treatment)
        observed_collections = sorted(
            {
                str(record.get("collection") or "")
                for record in records
                if record.get("collection")
            }
        )
        collection_correct = bool(
            expected_write
            and observed_collections == [case["expected_collection"]]
        )
        scored.append(
            {
                "id": case["id"],
                "language": case["language"],
                "category": case["category"],
                "expected_reflection_type": expected_type,
                "reflection_type_observed": treatment.get("reflection_type_observed", "none"),
                "reflection_type_correct": treatment.get("reflection_type_observed", "none")
                == expected_type,
                "expected_write": expected_write,
                "treatment_wrote": wrote,
                "treatment_reflection_valid": valid,
                "collection_correct": collection_correct,
                "source_provenance_valid": bool(
                    wrote and treatment.get("source_provenance_valid")
                ),
                "treatment_retrieved_reflection": bool(
                    treatment.get("retrieved_typed_reflection")
                ),
                "control_behavior_success": control_success,
                "treatment_behavior_success": treatment_success,
                "paired_gain": bool(treatment_success and not control_success),
                "paired_regression": bool(control_success and not treatment_success),
                "reply_changed": normalize_text(control.get("future_reply"))
                != normalize_text(treatment.get("future_reply")),
                "control_reply": control.get("future_reply") or "",
                "treatment_reply": treatment.get("future_reply") or "",
                "reflection_records": records,
                "treatment_working_memory": treatment.get("working_memory_items") or [],
            }
        )
    return scored


def _rate(rows, predicate):
    if not rows:
        return 0.0
    return round(sum(1 for row in rows if predicate(row)) / len(rows), 4)


def summarize(scored_rows, gates):
    positive = [row for row in scored_rows if row["expected_write"]]
    negative = [row for row in scored_rows if not row["expected_write"]]
    written = [row for row in scored_rows if row["treatment_wrote"]]
    valid_written = [
        row
        for row in positive
        if row["treatment_wrote"] and row["treatment_reflection_valid"]
    ]
    gains = [row for row in positive if row["paired_gain"]]
    regressions = [row for row in scored_rows if row["paired_regression"]]
    interaction_gains = [row for row in gains if row["category"] in INTERACTION_CATEGORIES]
    control_rate = _rate(positive, lambda row: row["control_behavior_success"])
    treatment_rate = _rate(positive, lambda row: row["treatment_behavior_success"])
    summary = {
        "case_count": len(scored_rows),
        "positive_case_count": len(positive),
        "negative_control_count": len(negative),
        "reflection_type_accuracy": _rate(
            scored_rows, lambda row: row["reflection_type_correct"]
        ),
        "valid_rule_precision": _rate(
            written,
            lambda row: row["expected_write"] and row["treatment_reflection_valid"],
        ),
        "expected_rule_write_recall": _rate(
            positive, lambda row: row["treatment_wrote"]
        ),
        "no_rule_specificity": _rate(
            negative, lambda row: not row["treatment_wrote"]
        ),
        "collection_routing_accuracy": _rate(
            valid_written, lambda row: row["collection_correct"]
        ),
        "source_provenance_rate": _rate(
            valid_written, lambda row: row["source_provenance_valid"]
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
        "writes_by_type": dict(
            Counter(row["reflection_type_observed"] for row in written)
        ),
        "behavior_gains_by_category": dict(Counter(row["category"] for row in gains)),
    }
    checks = {
        "reflection_type_accuracy": summary["reflection_type_accuracy"]
        >= gates["reflection_type_accuracy_min"],
        "valid_rule_precision": summary["valid_rule_precision"]
        >= gates["valid_rule_precision_min"],
        "expected_rule_write_recall": summary["expected_rule_write_recall"]
        >= gates["expected_rule_write_recall_min"],
        "no_rule_specificity": summary["no_rule_specificity"]
        >= gates["no_rule_specificity_min"],
        "collection_routing_accuracy": summary["collection_routing_accuracy"]
        >= gates["collection_routing_accuracy_min"],
        "source_provenance_rate": summary["source_provenance_rate"]
        >= gates["source_provenance_rate_min"],
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
    summary["gate_checks"] = checks
    summary["all_gates_pass"] = all(checks.values())
    return summary


def decision_for(summary, decision_rule):
    if summary["all_gates_pass"]:
        return decision_rule["all_gates_pass"]
    safety_precision = (
        "reflection_type_accuracy",
        "valid_rule_precision",
        "no_rule_specificity",
        "collection_routing_accuracy",
        "source_provenance_rate",
    )
    if any(not summary["gate_checks"][key] for key in safety_precision):
        return decision_rule["any_safety_or_precision_gate_fails"]
    return decision_rule["extraction_passes_behavior_fails"]
