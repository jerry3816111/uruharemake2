#!/usr/bin/env python3
"""Analyze the known-fixture development comparison for recall V1."""

from __future__ import annotations

import json
import statistics
from pathlib import Path

import memory_item_causal_intervention_v1 as mici


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/high_confidence_memory_recall_v1_preregistration.json"
BASELINE_RAW = ROOT / "analysis/local_memory_item_causal_intervention_v1/raw.jsonl"
CANDIDATE_RAW = ROOT / "analysis/local_high_confidence_memory_recall_v1_development/raw.jsonl"
REPORT_JSON = ROOT / "reports/high_confidence_memory_recall_v1_development.json"
REPORT_MD = ROOT / "reports/high_confidence_memory_recall_v1_development.md"


def load_jsonl(path):
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def rate(rows, predicate):
    return sum(bool(predicate(row)) for row in rows) / len(rows) if rows else 0.0


def percentile(values, quantile):
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    index = (len(ordered) - 1) * float(quantile)
    lower = int(index)
    upper = min(len(ordered) - 1, lower + 1)
    fraction = index - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def summarize(rows):
    by_condition = {
        condition: [row for row in rows if row.get("condition") == condition]
        for condition in mici.CONDITIONS
    }
    elapsed = [float(row.get("elapsed_seconds") or 0.0) for row in rows]
    calls = sum(int(row.get("leftbrain_call_count") or 0) for row in rows)
    return {
        "row_count": len(rows),
        "leftbrain_model_call_count": calls,
        "leftbrain_model_path_rate": calls / len(rows) if rows else 0.0,
        "zero_model_call_rate": rate(rows, lambda row: int(row.get("leftbrain_call_count") or 0) == 0),
        "fast_path_count": sum(
            row.get("planner_path") == "high_confidence_memory_recall_v1"
            for row in rows
        ),
        "latency_seconds": {
            "median": round(statistics.median(elapsed), 6) if elapsed else 0.0,
            "p95": round(percentile(elapsed, 0.95), 6),
            "maximum": round(max(elapsed), 6) if elapsed else 0.0,
            "total": round(sum(elapsed), 6),
        },
        "conditions": {
            mici.C0: {
                "target_anchor_rate": rate(by_condition[mici.C0], lambda row: row.get("target_anchor")),
                "target_plan_marker_rate": rate(by_condition[mici.C0], lambda row: row.get("target_marker_in_plan")),
                "target_reply_marker_rate": rate(by_condition[mici.C0], lambda row: row.get("target_marker_in_reply")),
            },
            mici.T1: {
                "target_anchor_rate": rate(by_condition[mici.T1], lambda row: row.get("target_anchor")),
                "target_plan_marker_rate": rate(by_condition[mici.T1], lambda row: row.get("target_marker_in_plan")),
                "target_reply_marker_rate": rate(by_condition[mici.T1], lambda row: row.get("target_marker_in_reply")),
            },
            mici.T2: {
                "replacement_anchor_rate": rate(by_condition[mici.T2], lambda row: row.get("replacement_anchor")),
                "replacement_plan_marker_rate": rate(by_condition[mici.T2], lambda row: row.get("replacement_marker_in_plan")),
                "replacement_reply_marker_rate": rate(by_condition[mici.T2], lambda row: row.get("replacement_marker_in_reply")),
            },
            mici.N1: {
                "target_anchor_rate": rate(by_condition[mici.N1], lambda row: row.get("target_anchor")),
                "target_plan_marker_rate": rate(by_condition[mici.N1], lambda row: row.get("target_marker_in_plan")),
                "target_reply_marker_rate": rate(by_condition[mici.N1], lambda row: row.get("target_marker_in_reply")),
            },
        },
    }


def build_report(baseline_rows, candidate_rows, prereg, preflight=None, run_metadata=None):
    baseline = summarize(baseline_rows)
    candidate = summarize(candidate_rows)
    checks = prereg["development_checks"]
    conditions = candidate["conditions"]
    gates = {
        "complete_32_rows": candidate["row_count"] == checks["expected_decision_run_count"],
        "intact_target_plan_preserved": conditions[mici.C0]["target_plan_marker_rate"] >= checks["target_or_replacement_plan_marker_rate_min"],
        "removed_target_does_not_leak": conditions[mici.T1]["target_plan_marker_rate"] <= checks["remove_target_plan_marker_rate_max"],
        "replacement_steers_plan": conditions[mici.T2]["replacement_plan_marker_rate"] >= checks["target_or_replacement_plan_marker_rate_min"],
        "irrelevant_removal_preserves_target": conditions[mici.N1]["target_plan_marker_rate"] >= checks["irrelevant_removal_target_plan_marker_rate_min"],
        "model_call_budget": candidate["leftbrain_model_call_count"] <= checks["leftbrain_model_call_count_max"],
        "boundary_preflight": bool((preflight or {}).get("passed")),
        "no_transport_errors": not any(int(row.get("transport_error_count") or 0) for row in candidate_rows),
        "no_production_writes": not any(int(row.get("production_memory_write_count") or 0) for row in candidate_rows),
        "no_vrm_actions": not any(int(row.get("physical_vrm_action_count") or 0) for row in candidate_rows),
    }
    call_reduction = baseline["leftbrain_model_call_count"] - candidate["leftbrain_model_call_count"]
    total_reduction = baseline["latency_seconds"]["total"] - candidate["latency_seconds"]["total"]
    removed_rows = [row for row in candidate_rows if row.get("condition") == mici.T1]
    removed_fast_rows = [
        row
        for row in removed_rows
        if row.get("planner_path") == "high_confidence_memory_recall_v1"
    ]
    valid_fast_rows = [
        row
        for row in candidate_rows
        if row.get("condition") in {mici.C0, mici.T2, mici.N1}
        and row.get("planner_path") == "high_confidence_memory_recall_v1"
    ]
    return {
        "schema": "uruha_high_confidence_memory_recall_development_result_v1",
        "decision": "development_pass_requires_fresh_holdout" if all(gates.values()) else "development_reject_or_inconclusive",
        "evidence_scope": "known eight-case mechanism fixture only",
        "baseline": baseline,
        "candidate": candidate,
        "delta": {
            "leftbrain_model_calls": -call_reduction,
            "leftbrain_model_call_reduction_rate": round(call_reduction / baseline["leftbrain_model_call_count"], 6) if baseline["leftbrain_model_call_count"] else 0.0,
            "total_latency_seconds": round(-total_reduction, 6),
            "total_latency_reduction_rate": round(total_reduction / baseline["latency_seconds"]["total"], 6) if baseline["latency_seconds"]["total"] else 0.0,
        },
        "gates": gates,
        "posthoc_diagnostics_not_preregistered_gates": {
            "target_removed_fast_path_activation_count": len(removed_fast_rows),
            "target_removed_fast_path_activation_rate": rate(
                removed_rows,
                lambda row: row.get("planner_path") == "high_confidence_memory_recall_v1",
            ),
            "target_removed_irrelevant_reply_count": sum(
                bool(row.get("reply"))
                and not row.get("target_marker_in_reply")
                and not row.get("replacement_marker_in_reply")
                for row in removed_fast_rows
            ),
            "valid_condition_fast_path_count": len(valid_fast_rows),
            "diagnosis": "Ranking confidence and top-runner-up margin do not prove query-memory semantic support; after exact-target removal the sole irrelevant record can still appear high-confidence.",
        },
        "preflight": preflight or {},
        "run_metadata": run_metadata or {},
        "authorization": {
            "fresh_holdout": all(gates.values()),
            "production_default_enablement": False,
            "benchmark_claim": False,
            "persona_similarity_claim": False,
        },
    }


def markdown(report):
    base = report["baseline"]
    cand = report["candidate"]
    lines = [
        "# High-confidence memory recall V1 development result",
        "",
        f"- Decision: `{report['decision']}`",
        "- Scope: known eight-case mechanism fixture; this is not fresh generalization evidence.",
        f"- LeftBrain model calls: {base['leftbrain_model_call_count']} -> {cand['leftbrain_model_call_count']}",
        f"- Zero-model-call rate: {base['zero_model_call_rate']:.1%} -> {cand['zero_model_call_rate']:.1%}",
        f"- Median latency: {base['latency_seconds']['median']:.3f}s -> {cand['latency_seconds']['median']:.3f}s",
        f"- Total latency: {base['latency_seconds']['total']:.3f}s -> {cand['latency_seconds']['total']:.3f}s",
        f"- Post-hoc target-removed false fast paths: {report['posthoc_diagnostics_not_preregistered_gates']['target_removed_fast_path_activation_count']}/8",
        "",
        "## Causal conditions",
        "",
        "| Condition | Baseline plan rate | Candidate plan rate |",
        "|---|---:|---:|",
        f"| intact target | {base['conditions'][mici.C0]['target_plan_marker_rate']:.1%} | {cand['conditions'][mici.C0]['target_plan_marker_rate']:.1%} |",
        f"| target removed | {base['conditions'][mici.T1]['target_plan_marker_rate']:.1%} | {cand['conditions'][mici.T1]['target_plan_marker_rate']:.1%} |",
        f"| target replaced | {base['conditions'][mici.T2]['replacement_plan_marker_rate']:.1%} | {cand['conditions'][mici.T2]['replacement_plan_marker_rate']:.1%} |",
        f"| irrelevant removed | {base['conditions'][mici.N1]['target_plan_marker_rate']:.1%} | {cand['conditions'][mici.N1]['target_plan_marker_rate']:.1%} |",
        "",
        "## Gates",
        "",
    ]
    lines.extend(f"- {name}: {'PASS' if passed else 'FAIL'}" for name, passed in report["gates"].items())
    lines.extend(
        [
            "",
            "## Evidence boundary",
            "",
            "A pass authorizes only a disjoint fresh holdout. It does not authorize production, benchmark, human-memory, or persona-similarity claims.",
        ]
    )
    return "\n".join(lines) + "\n"


def main():
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    candidate_rows = load_jsonl(CANDIDATE_RAW)
    metadata_path = CANDIDATE_RAW.parent / "run_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
    report = build_report(
        load_jsonl(BASELINE_RAW),
        candidate_rows,
        prereg,
        preflight=metadata.get("preflight"),
        run_metadata=metadata,
    )
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT_MD.write_text(markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
