#!/usr/bin/env python3
"""Analyze exact-record memory intervention outcomes."""

from __future__ import annotations

import json
import random
import statistics
from pathlib import Path

import memory_item_causal_intervention_v1 as experiment
import run_memory_item_causal_intervention_v1 as runner


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/memory_item_causal_intervention_v1_preregistration.json"
REPORT_JSON = ROOT / "reports/memory_item_causal_intervention_v1.json"
REPORT_MD = ROOT / "reports/memory_item_causal_intervention_v1.md"


def rate(rows, key):
    return sum(bool(row.get(key)) for row in rows) / len(rows) if rows else 0.0


def bootstrap_delta(rows, positive_condition, negative_condition, key, seed=2026080502, samples=10000):
    by_case = {}
    for row in rows:
        by_case.setdefault(row["case_id"], {})[row["condition"]] = float(bool(row.get(key)))
    deltas = [
        conditions[positive_condition] - conditions[negative_condition]
        for conditions in by_case.values()
    ]
    rng = random.Random(seed)
    draws = []
    for _ in range(samples):
        sample = [deltas[rng.randrange(len(deltas))] for _ in deltas]
        draws.append(sum(sample) / len(sample))
    draws.sort()
    return {
        "pair_count": len(deltas),
        "mean_delta": sum(deltas) / len(deltas),
        "bootstrap_95_ci": [draws[int(samples * 0.025)], draws[int(samples * 0.975)]],
    }


def build_report(rows, prereg):
    expected = int(prereg["scope"]["expected_decision_run_count"])
    conditions = {
        condition: [row for row in rows if row["condition"] == condition]
        for condition in experiment.CONDITIONS
    }
    case_shapes = {}
    for row in rows:
        case_shapes.setdefault(row["case_id"], set()).add(row["condition"])
    integrity = {
        "expected_row_count": len(rows) == expected,
        "all_cases_have_all_conditions": bool(case_shapes)
        and all(values == set(experiment.CONDITIONS) for values in case_shapes.values()),
        "retrieval_schema_present": all(
            row["retrieval_audit"].get("schema") == "uruha_memory_provenance_trace_v1"
            for row in rows
        ),
        "target_selected_and_passed": all(
            row["retrieval_audit"]["target_selected"]
            and row["retrieval_audit"]["target_passed"]
            for row in rows
        ),
        "irrelevant_selected_and_passed": all(
            row["retrieval_audit"]["irrelevant_selected"]
            and row["retrieval_audit"]["irrelevant_passed"]
            for row in rows
        ),
        "decision_view_intervention_clean": all(
            row["decision_view_target_absent_when_required"]
            and row["decision_view_irrelevant_absent_when_required"]
            for row in rows
        ),
        "no_production_writes": sum(row["production_memory_write_count"] for row in rows) == 0,
        "no_vrm_actions": sum(row["physical_vrm_action_count"] for row in rows) == 0,
        "no_transport_errors": sum(row["transport_error_count"] for row in rows)
        <= prereg["advance_gates"]["transport_error_count_max"],
        "condition_deadline_respected": all(
            float(row["elapsed_seconds"])
            <= float(prereg["generation"]["maximum_condition_seconds"])
            for row in rows
        ),
    }
    summaries = {}
    for condition, condition_rows in conditions.items():
        latencies = [float(row["elapsed_seconds"]) for row in condition_rows]
        summaries[condition] = {
            "row_count": len(condition_rows),
            "target_anchor_rate": rate(condition_rows, "target_anchor"),
            "replacement_anchor_rate": rate(condition_rows, "replacement_anchor"),
            "target_marker_in_plan_rate": rate(condition_rows, "target_marker_in_plan"),
            "replacement_marker_in_plan_rate": rate(condition_rows, "replacement_marker_in_plan"),
            "target_marker_in_reply_rate": rate(condition_rows, "target_marker_in_reply"),
            "replacement_marker_in_reply_rate": rate(condition_rows, "replacement_marker_in_reply"),
            "mean_latency_seconds": statistics.mean(latencies) if latencies else 0.0,
            "leftbrain_call_count": sum(row["leftbrain_call_count"] for row in condition_rows),
            "transport_error_count": sum(row["transport_error_count"] for row in condition_rows),
        }

    removal = bootstrap_delta(rows, experiment.C0, experiment.T1, "target_marker_in_plan")
    irrelevant_preservation_delta = (
        summaries[experiment.N1]["target_marker_in_plan_rate"]
        - summaries[experiment.C0]["target_marker_in_plan_rate"]
    )
    gates = prereg["advance_gates"]
    checks = {
        "integrity": all(integrity.values()),
        "intact_target_anchor": summaries[experiment.C0]["target_anchor_rate"]
        >= gates["intact_target_anchor_rate_min"],
        "removed_target_anchor": summaries[experiment.T1]["target_anchor_rate"]
        <= gates["remove_target_anchor_rate_max"],
        "replacement_anchor": summaries[experiment.T2]["replacement_anchor_rate"]
        >= gates["replacement_anchor_rate_min"],
        "irrelevant_removed_target_anchor": summaries[experiment.N1]["target_anchor_rate"]
        >= gates["irrelevant_removed_target_anchor_rate_min"],
        "intact_target_plan": summaries[experiment.C0]["target_marker_in_plan_rate"]
        >= gates["intact_target_plan_marker_rate_min"],
        "removed_target_plan": summaries[experiment.T1]["target_marker_in_plan_rate"]
        <= gates["remove_target_plan_marker_rate_max"],
        "replacement_plan": summaries[experiment.T2]["replacement_marker_in_plan_rate"]
        >= gates["replacement_plan_marker_rate_min"],
        "irrelevant_removed_target_plan": summaries[experiment.N1]["target_marker_in_plan_rate"]
        >= gates["irrelevant_removed_target_plan_marker_rate_min"],
        "paired_target_removal": removal["mean_delta"]
        >= gates["target_removal_paired_plan_delta_min"],
        "irrelevant_removal_preservation": abs(irrelevant_preservation_delta)
        <= gates["irrelevant_removal_target_preservation_delta_max_abs"],
    }
    decision = (
        "exact_memory_record_causally_supported_bounded"
        if all(checks.values())
        else "exact_memory_record_causality_not_supported_or_inconclusive"
    )
    return {
        "schema": "uruha_memory_item_causal_analysis_v1",
        "experiment_id": prereg["experiment_id"],
        "decision": decision,
        "integrity": integrity,
        "gate_checks": checks,
        "condition_summaries": summaries,
        "paired_effects": {
            "target_removal_plan_marker": removal,
            "irrelevant_removal_target_preservation_delta": irrelevant_preservation_delta,
        },
        "resource_summary": {
            "total_leftbrain_calls": sum(row["leftbrain_call_count"] for row in rows),
            "transport_error_count": sum(row["transport_error_count"] for row in rows),
            "maximum_condition_seconds": max(float(row["elapsed_seconds"]) for row in rows),
        },
        "evidence_boundary": prereg["evidence_boundary"],
    }


def render_markdown(report):
    summaries = report["condition_summaries"]
    labels = {
        experiment.C0: "完整目標＋無關記憶",
        experiment.T1: "只移除目標記憶",
        experiment.T2: "只替換目標記憶",
        experiment.N1: "只移除無關記憶",
    }
    lines = [
        "# 逐筆記憶因果干預 V1",
        "",
        f"**判定：{report['decision']}**",
        "",
        "| 條件 | 目標記憶成為錨點 | 替換記憶成為錨點 | 計畫含目標內容 | 計畫含替換內容 | 最終語句含目標內容 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for condition in experiment.CONDITIONS:
        row = summaries[condition]
        lines.append(
            f"| {labels[condition]} | {row['target_anchor_rate']:.1%} | "
            f"{row['replacement_anchor_rate']:.1%} | {row['target_marker_in_plan_rate']:.1%} | "
            f"{row['replacement_marker_in_plan_rate']:.1%} | {row['target_marker_in_reply_rate']:.1%} |"
        )
    pair = report["paired_effects"]["target_removal_plan_marker"]
    lines.extend(
        [
            "",
            "## 配對效果",
            "",
            f"- 只移除確切目標記憶後，目標內容在計畫中的配對差異：{pair['mean_delta']:+.1%}。",
            f"- case bootstrap 95% CI：[{pair['bootstrap_95_ci'][0]:+.1%}, {pair['bootstrap_95_ci'][1]:+.1%}]。",
            f"- 只移除無關記憶的目標保留差異：{report['paired_effects']['irrelevant_removal_target_preservation_delta']:+.1%}。",
            "",
            "## 證據邊界",
            "",
            report["evidence_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def main():
    prereg = runner.load_json(PREREG_PATH)
    rows = runner.load_jsonl(runner.RAW_PATH)
    report = build_report(rows, prereg)
    REPORT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    REPORT_MD.write_text(render_markdown(report), encoding="utf-8")
    (runner.LOCAL_DIR / "analysis.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"decision": report["decision"], "integrity": report["integrity"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
