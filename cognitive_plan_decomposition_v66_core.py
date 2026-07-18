"""Pure parsing, exact scoring, and frozen V66 decision logic."""

from __future__ import annotations

import json
import math
import statistics
from collections import Counter, defaultdict


ONE_CALL = "one_call_full_plan_reference"
MATCHED_CONTROL = "two_pass_full_plan_control"
TREATMENT = "two_stage_responsibility_decomposition"
CONDITIONS = (TREATMENT, ONE_CALL, MATCHED_CONTROL)

SELECTION_FIELDS = (
    "primary_actor_id",
    "selected_evidence_ids",
    "active_memory_ids",
    "suppressed_memory_ids",
    "nonliteral",
)
DECISION_FIELDS = (
    "response_act",
    "epistemic_policy",
    "decision_target_id",
)
SCALAR_FIELDS = (
    "response_act",
    "epistemic_policy",
    "primary_actor_id",
    "decision_target_id",
    "nonliteral",
)
SET_FIELDS = (
    "selected_evidence_ids",
    "active_memory_ids",
    "suppressed_memory_ids",
)
ALL_FIELDS = (*SCALAR_FIELDS, *SET_FIELDS)


def parse_tool_response(response, expected_tool_name, expected_fields):
    message = (response or {}).get("message") or {}
    calls = message.get("tool_calls") or []
    if len(calls) != 1:
        return {"tool_parse_success": False, "values": {}, "parse_error": f"tool_call_count:{len(calls)}"}
    function = calls[0].get("function") or {}
    if function.get("name") != expected_tool_name:
        return {"tool_parse_success": False, "values": {}, "parse_error": "wrong_tool_name"}
    arguments = function.get("arguments")
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            return {"tool_parse_success": False, "values": {}, "parse_error": "arguments_not_json"}
    if not isinstance(arguments, dict) or set(arguments) != set(expected_fields):
        return {
            "tool_parse_success": False,
            "values": arguments if isinstance(arguments, dict) else {},
            "parse_error": "argument_fields",
        }
    if "nonliteral" in expected_fields and not isinstance(arguments.get("nonliteral"), bool):
        return {"tool_parse_success": False, "values": arguments, "parse_error": "nonliteral_type"}
    scalar_fields = set(expected_fields) - set(SET_FIELDS) - {"nonliteral"}
    if not all(isinstance(arguments.get(field), str) for field in scalar_fields):
        return {"tool_parse_success": False, "values": arguments, "parse_error": "scalar_types"}
    set_fields = set(expected_fields).intersection(SET_FIELDS)
    if not all(
        isinstance(arguments.get(field), list)
        and all(isinstance(item, str) for item in arguments[field])
        for field in set_fields
    ):
        return {"tool_parse_success": False, "values": arguments, "parse_error": "set_types"}
    return {"tool_parse_success": True, "values": arguments, "parse_error": None}


def assemble_plan(selection, decision):
    return {
        "response_act": decision.get("response_act"),
        "epistemic_policy": decision.get("epistemic_policy"),
        "primary_actor_id": selection.get("primary_actor_id"),
        "decision_target_id": decision.get("decision_target_id"),
        "selected_evidence_ids": selection.get("selected_evidence_ids", []),
        "active_memory_ids": selection.get("active_memory_ids", []),
        "suppressed_memory_ids": selection.get("suppressed_memory_ids", []),
        "nonliteral": selection.get("nonliteral"),
    }


def referentially_valid(plan, packet, config):
    if not isinstance(plan, dict):
        return False
    actor_ids = {row["id"] for row in packet["actors"]}
    target_ids = {row["id"] for row in packet["decision_targets"]}
    evidence_ids = {row["id"] for row in packet["evidence"]}
    memory_ids = {row["id"] for row in packet["memory_records"]}
    active = set(plan.get("active_memory_ids") or [])
    suppressed = set(plan.get("suppressed_memory_ids") or [])
    return bool(
        plan.get("response_act") in config["plan_contract"]["response_act_enum"]
        and plan.get("epistemic_policy") in config["plan_contract"]["epistemic_policy_enum"]
        and plan.get("primary_actor_id") in actor_ids
        and plan.get("decision_target_id") in target_ids
        and set(plan.get("selected_evidence_ids") or []).issubset(evidence_ids)
        and active.union(suppressed) == memory_ids
        and not active.intersection(suppressed)
    )


def score_plan(plan, expected, parse_success, reference_valid):
    field_hits = {}
    for field in SCALAR_FIELDS:
        field_hits[field] = plan.get(field) == expected[field]
    for field in SET_FIELDS:
        field_hits[field] = set(plan.get(field) or []) == set(expected[field])
    selection_exact = all(field_hits[field] for field in SELECTION_FIELDS)
    decision_exact = all(field_hits[field] for field in DECISION_FIELDS)
    valid = bool(parse_success and reference_valid)
    return {
        "all_required_tools_parse": bool(parse_success),
        "referentially_valid": bool(reference_valid),
        "field_hits": field_hits,
        "field_hit_count": sum(field_hits.values()),
        "field_count": len(ALL_FIELDS),
        "selection_stage_exact": bool(valid and selection_exact),
        "decision_stage_exact": bool(valid and decision_exact),
        "exact_case": bool(valid and selection_exact and decision_exact),
    }


def _percentile(values, quantile):
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * quantile
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def _condition_metrics(rows, family_by_id):
    family_exact = Counter()
    family_total = Counter()
    for row in rows:
        family = family_by_id[row["case_id"]]
        family_total[family] += 1
        family_exact[family] += int(row["score"]["exact_case"])
    latencies = [row["wall_seconds"] for row in rows]
    rss_values = [row["ollama_rss_bytes"] for row in rows if row.get("ollama_rss_bytes") is not None]
    field_hits = sum(row["score"]["field_hit_count"] for row in rows)
    count = len(rows)
    return {
        "case_count": count,
        "exact_case_count": sum(row["score"]["exact_case"] for row in rows),
        "exact_case_accuracy": sum(row["score"]["exact_case"] for row in rows) / count,
        "exact_field_hits": field_hits,
        "exact_field_count": count * len(ALL_FIELDS),
        "exact_field_accuracy": field_hits / (count * len(ALL_FIELDS)),
        "selection_stage_exact_count": sum(row["score"]["selection_stage_exact"] for row in rows),
        "decision_stage_exact_count": sum(row["score"]["decision_stage_exact"] for row in rows),
        "all_required_tools_parse_count": sum(row["score"]["all_required_tools_parse"] for row in rows),
        "referentially_valid_count": sum(row["score"]["referentially_valid"] for row in rows),
        "family_exact_counts": {
            family: {"correct": family_exact[family], "total": family_total[family]}
            for family in sorted(family_total)
        },
        "latency_median_seconds_per_case": statistics.median(latencies),
        "latency_p95_seconds_per_case": _percentile(latencies, 0.95),
        "peak_ollama_rss_bytes": max(rss_values) if rss_values else None,
        "transport_attempt_count": sum(row["transport_attempts"] for row in rows),
    }


def analyze(rows, dataset, config):
    cases = {case["id"]: case for case in dataset["cases"]}
    by_condition = defaultdict(list)
    by_case = defaultdict(dict)
    scored = []
    for row in rows:
        case = cases[row["case_id"]]
        score = score_plan(
            row.get("plan") or {},
            case["expected"],
            row.get("all_required_tools_parse"),
            row.get("referentially_valid"),
        )
        item = {**row, "score": score}
        scored.append(item)
        by_condition[row["condition"]].append(item)
        by_case[row["case_id"]][row["condition"]] = item

    family_by_id = {case["id"]: case["scenario_family"] for case in dataset["cases"]}
    metrics = {
        condition: _condition_metrics(by_condition[condition], family_by_id)
        for condition in CONDITIONS
    }
    newly = sum(
        by_case[case_id][TREATMENT]["score"]["exact_case"]
        and not by_case[case_id][MATCHED_CONTROL]["score"]["exact_case"]
        for case_id in by_case
    )
    regressions = sum(
        by_case[case_id][MATCHED_CONTROL]["score"]["exact_case"]
        and not by_case[case_id][TREATMENT]["score"]["exact_case"]
        for case_id in by_case
    )
    gates = config["treatment_success_gates"]
    treatment = metrics[TREATMENT]
    checks = {
        "exact_case_count": treatment["exact_case_count"] >= gates["exact_case_count_min"],
        "exact_case_accuracy": treatment["exact_case_accuracy"] >= gates["exact_case_accuracy_min"],
        "exact_field_accuracy": treatment["exact_field_accuracy"] >= gates["exact_field_accuracy_min"],
        "selection_stage_exact": treatment["selection_stage_exact_count"] >= gates["selection_stage_exact_count_min"],
        "decision_stage_exact": treatment["decision_stage_exact_count"] >= gates["decision_stage_exact_count_min"],
        "newly_correct": newly >= gates["newly_correct_vs_matched_control_min"],
        "regressions": regressions <= gates["regressions_vs_matched_control_max"],
        "tool_parse": treatment["all_required_tools_parse_count"] == gates["both_treatment_tools_parse_count"],
        "median_latency": treatment["latency_median_seconds_per_case"] <= gates["median_wall_seconds_per_case_max"],
        "p95_latency": treatment["latency_p95_seconds_per_case"] <= gates["p95_wall_seconds_per_case_max"],
        "peak_rss": treatment["peak_ollama_rss_bytes"] <= gates["peak_rss_bytes_max"],
    }
    passed = all(checks.values())
    return {
        "metrics": metrics,
        "pairwise": {
            "treatment_vs_matched_control": {
                "newly_correct": newly,
                "regressions": regressions,
                "checks": checks,
                "eligible": passed,
            }
        },
        "decision": (
            "authorize_fresh_production_packet_shadow_pilot"
            if passed
            else "freeze_result_and_stop_fixed_two_stage_decomposition_as_sufficient_solution"
        ),
        "scored_rows": scored,
    }
