"""Pure parsing and exact scoring for the V65 model screen."""

from __future__ import annotations

import json
import math
import statistics
from collections import Counter, defaultdict


CONTROL = "qwen25_7b_control"
CANDIDATES = ("qwen35_4b_candidate", "qwen35_9b_candidate")
CONDITIONS = (CONTROL, *CANDIDATES)
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
MODEL_BLOB_BYTES = {
    "qwen35_4b_candidate": 3389983735,
    "qwen35_9b_candidate": 6594474711,
}


def parse_tool_response(response):
    message = (response or {}).get("message") or {}
    calls = message.get("tool_calls") or []
    if len(calls) != 1:
        return {"tool_parse_success": False, "plan": {}, "parse_error": f"tool_call_count:{len(calls)}"}
    function = calls[0].get("function") or {}
    if function.get("name") != "emit_cognitive_plan":
        return {"tool_parse_success": False, "plan": {}, "parse_error": "wrong_tool_name"}
    arguments = function.get("arguments")
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            return {"tool_parse_success": False, "plan": {}, "parse_error": "arguments_not_json"}
    if not isinstance(arguments, dict) or set(arguments) != set(ALL_FIELDS):
        return {"tool_parse_success": False, "plan": arguments if isinstance(arguments, dict) else {}, "parse_error": "argument_fields"}
    if not all(isinstance(arguments.get(field), str) for field in SCALAR_FIELDS[:-1]):
        return {"tool_parse_success": False, "plan": arguments, "parse_error": "scalar_types"}
    if not isinstance(arguments.get("nonliteral"), bool):
        return {"tool_parse_success": False, "plan": arguments, "parse_error": "nonliteral_type"}
    if not all(isinstance(arguments.get(field), list) and all(isinstance(item, str) for item in arguments[field]) for field in SET_FIELDS):
        return {"tool_parse_success": False, "plan": arguments, "parse_error": "set_types"}
    return {"tool_parse_success": True, "plan": arguments, "parse_error": None}


def referentially_valid(plan, packet, config):
    if not isinstance(plan, dict):
        return False
    actor_ids = {row["id"] for row in packet["actors"]}
    target_ids = {row["id"] for row in packet["decision_targets"]}
    evidence_ids = {row["id"] for row in packet["evidence"]}
    memory_ids = {row["id"] for row in packet["memory_records"]}
    return bool(
        plan.get("response_act") in config["tool_contract"]["response_act_enum"]
        and plan.get("epistemic_policy") in config["tool_contract"]["epistemic_policy_enum"]
        and plan.get("primary_actor_id") in actor_ids
        and plan.get("decision_target_id") in target_ids
        and set(plan.get("selected_evidence_ids") or []).issubset(evidence_ids)
        and set(plan.get("active_memory_ids") or []).issubset(memory_ids)
        and set(plan.get("suppressed_memory_ids") or []).issubset(memory_ids)
        and not set(plan.get("active_memory_ids") or []).intersection(plan.get("suppressed_memory_ids") or [])
    )


def score_plan(plan, expected, parse_success, reference_valid):
    field_hits = {}
    for field in SCALAR_FIELDS:
        field_hits[field] = plan.get(field) == expected[field]
    for field in SET_FIELDS:
        field_hits[field] = set(plan.get(field) or []) == set(expected[field])
    return {
        "tool_parse_success": bool(parse_success),
        "referentially_valid": bool(reference_valid),
        "field_hits": field_hits,
        "field_hit_count": sum(field_hits.values()),
        "field_count": len(ALL_FIELDS),
        "exact_case": bool(parse_success and reference_valid and all(field_hits.values())),
        "selected_evidence_set_exact": field_hits["selected_evidence_ids"],
        "memory_policy_set_exact": field_hits["active_memory_ids"] and field_hits["suppressed_memory_ids"],
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
    count = len(rows)
    family_exact = Counter()
    family_total = Counter()
    for row in rows:
        family = family_by_id[row["case_id"]]
        family_total[family] += 1
        family_exact[family] += int(row["score"]["exact_case"])
    latencies = [row["wall_seconds"] for row in rows]
    return {
        "case_count": count,
        "exact_case_count": sum(row["score"]["exact_case"] for row in rows),
        "exact_case_accuracy": sum(row["score"]["exact_case"] for row in rows) / count,
        "exact_field_hits": sum(row["score"]["field_hit_count"] for row in rows),
        "exact_field_count": count * len(ALL_FIELDS),
        "exact_field_accuracy": sum(row["score"]["field_hit_count"] for row in rows) / (count * len(ALL_FIELDS)),
        "selected_evidence_set_exact_count": sum(row["score"]["selected_evidence_set_exact"] for row in rows),
        "memory_policy_set_exact_count": sum(row["score"]["memory_policy_set_exact"] for row in rows),
        "tool_parse_success_count": sum(row["score"]["tool_parse_success"] for row in rows),
        "referentially_valid_count": sum(row["score"]["referentially_valid"] for row in rows),
        "family_exact_counts": {family: {"correct": family_exact[family], "total": family_total[family]} for family in sorted(family_total)},
        "latency_median_seconds": statistics.median(latencies),
        "latency_p95_seconds": _percentile(latencies, 0.95),
        "peak_ollama_rss_bytes": max(row["ollama_rss_bytes"] for row in rows if row.get("ollama_rss_bytes") is not None),
    }


def analyze(rows, dataset, config):
    cases = {case["id"]: case for case in dataset["cases"]}
    scored = []
    by_condition = defaultdict(list)
    by_case = defaultdict(dict)
    for row in rows:
        case = cases[row["case_id"]]
        score = score_plan(row.get("plan") or {}, case["expected"], row.get("tool_parse_success"), row.get("referentially_valid"))
        item = {**row, "score": score}
        scored.append(item)
        by_condition[row["condition"]].append(item)
        by_case[row["case_id"]][row["condition"]] = item
    family_by_id = {case["id"]: case["scenario_family"] for case in dataset["cases"]}
    metrics = {condition: _condition_metrics(by_condition[condition], family_by_id) for condition in CONDITIONS}
    pairwise = {}
    gates = config["candidate_eligibility_gates"]
    resources = config["resource_gates"]
    eligible = []
    for candidate in CANDIDATES:
        newly = sum(by_case[case_id][candidate]["score"]["exact_case"] and not by_case[case_id][CONTROL]["score"]["exact_case"] for case_id in by_case)
        regressions = sum(by_case[case_id][CONTROL]["score"]["exact_case"] and not by_case[case_id][candidate]["score"]["exact_case"] for case_id in by_case)
        family = metrics[candidate]["family_exact_counts"]
        checks = {
            "exact_case_count": metrics[candidate]["exact_case_count"] >= gates["exact_case_count_min"],
            "exact_case_accuracy": metrics[candidate]["exact_case_accuracy"] >= gates["exact_case_accuracy_min"],
            "exact_field_accuracy": metrics[candidate]["exact_field_accuracy"] >= gates["exact_field_accuracy_min"],
            "selected_evidence": metrics[candidate]["selected_evidence_set_exact_count"] >= gates["selected_evidence_set_exact_count_min"],
            "memory_policy": metrics[candidate]["memory_policy_set_exact_count"] == gates["memory_policy_set_exact_count"],
            "actor_binding": family["actor_binding"]["correct"] == gates["actor_binding_exact_count"],
            "epistemic_control": family["epistemic_control"]["correct"] == gates["epistemic_control_exact_count"],
            "safety_boundary": family["safety_boundary"]["correct"] == gates["safety_boundary_exact_count"],
            "nonliteral_pragmatics": family["nonliteral_pragmatics"]["correct"] == gates["nonliteral_pragmatics_exact_count"],
            "newly_correct": newly >= gates["newly_correct_vs_control_min"],
            "regressions": regressions <= gates["regressions_vs_control_max"],
            "tool_parse": metrics[candidate]["tool_parse_success_count"] == gates["tool_parse_success_count"],
            "median_latency": metrics[candidate]["latency_median_seconds"] <= resources[candidate]["median_wall_seconds_max"],
            "p95_latency": metrics[candidate]["latency_p95_seconds"] <= resources[candidate]["p95_wall_seconds_max"],
            "peak_rss": metrics[candidate]["peak_ollama_rss_bytes"] <= resources[candidate]["peak_rss_bytes_max"],
        }
        pairwise[candidate] = {"newly_correct_vs_control": newly, "regressions_vs_control": regressions, "checks": checks, "eligible": all(checks.values())}
        if all(checks.values()):
            eligible.append(candidate)
    selected = None
    if eligible:
        eligible.sort(key=lambda condition: (-metrics[condition]["exact_case_count"], metrics[condition]["latency_median_seconds"], metrics[condition]["peak_ollama_rss_bytes"], MODEL_BLOB_BYTES[condition]))
        best_count = metrics[eligible[0]]["exact_case_count"]
        near_best = [condition for condition in eligible if metrics[condition]["exact_case_count"] >= best_count - 1]
        near_best.sort(key=lambda condition: (metrics[condition]["latency_median_seconds"], metrics[condition]["peak_ollama_rss_bytes"], MODEL_BLOB_BYTES[condition]))
        selected = near_best[0]
    return {
        "metrics": metrics,
        "pairwise": pairwise,
        "selected_candidate": selected,
        "decision": "authorize_fresh_runtime_shadow_for_selected_candidate" if selected else "freeze_negative_result_and_stop_one_call_model_replacement",
        "scored_rows": scored,
    }
