#!/usr/bin/env python3
"""Analyze the frozen V7 incremental planner-obligation screen."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path

import public_persona_scorer_contract_v4 as v4
import public_persona_specificity_scorer_v7 as specificity
from run_public_persona_incremental_planner_v7 import CONDITIONS
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
PREREGISTRATION = ROOT / "configs/public_persona_incremental_planner_v7_preregistration.json"
DATASET = ROOT / "datasets/public_persona_contract_v3_development.json"
DEFAULT_RAW = ROOT / "reports/public_persona_incremental_planner_v7_raw.json"
DEFAULT_JSON = ROOT / "reports/public_persona_incremental_planner_v7_analysis.json"
DEFAULT_MD = ROOT / "reports/public_persona_incremental_planner_v7_analysis.md"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def percentile(values, probability):
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(len(ordered) * probability + 0.999999) - 1))
    return ordered[index]


def marker_group_hit(right_brain, reply, group):
    return any(right_brain._semantic_marker_hit(reply, marker) for marker in group)


def score_row(right_brain, raw_row, case):
    reply = raw_row["raw_reply"]
    semantic_hits = [
        marker_group_hit(right_brain, reply, group)
        for group in case["logic"]["required_marker_groups"]
    ]
    persona = v4.score_reply(reply, v4.compile_scorer_contract(case["context"]))
    specificity_result = specificity.score_specificity(reply, case)
    gate_reasons = right_brain._model_candidate_rejection_reasons(
        reply,
        case["logic"],
        case["persona_evaluation"]["maximum_characters"],
    )
    return {
        "case_id": case["case_id"],
        "context": case["context"],
        "condition": raw_row["condition"],
        "contract_active": raw_row["contract_active"],
        "semantic_contract_pass": bool(semantic_hits) and all(semantic_hits),
        "v4_persona_scored": persona["scored"],
        "v4_persona_pass": persona["passed"],
        "v4_persona_reasons": persona["reasons"],
        "surface_gate_pass": not gate_reasons,
        "surface_gate_reasons": gate_reasons,
        "specificity_scored": specificity_result["scored"],
        "specificity_pass": specificity_result["passed"],
        "unsupported_concrete_markers": specificity_result["unsupported_concrete_markers"],
        "transport_error": raw_row["transport_error"],
        "unexpected_tool_call": bool(raw_row["tool_calls"]),
        "elapsed_seconds": raw_row["elapsed_seconds"],
        "peak_ollama_rss_bytes": raw_row["peak_ollama_rss_bytes"] or 0,
        "raw_reply": reply,
        "raw_reply_sha256": raw_row["raw_reply_sha256"],
    }


def aggregate(rows):
    persona_rows = [row for row in rows if row["v4_persona_scored"]]
    specificity_rows = [row for row in rows if row["specificity_scored"]]
    return {
        "row_count": len(rows),
        "semantic_pass_count": sum(row["semantic_contract_pass"] for row in rows),
        "semantic_pass_rate": sum(row["semantic_contract_pass"] for row in rows) / len(rows),
        "v4_persona_case_count": len(persona_rows),
        "v4_persona_pass_count": sum(row["v4_persona_pass"] is True for row in persona_rows),
        "v4_persona_pass_rate": sum(row["v4_persona_pass"] is True for row in persona_rows)
        / len(persona_rows),
        "surface_gate_pass_count": sum(row["surface_gate_pass"] for row in rows),
        "specificity_case_count": len(specificity_rows),
        "specificity_pass_count": sum(row["specificity_pass"] for row in specificity_rows),
        "specificity_intrusion_count": sum(
            len(row["unsupported_concrete_markers"]) for row in specificity_rows
        ),
        "transport_error_count": sum(bool(row["transport_error"]) for row in rows),
        "unexpected_tool_call_count": sum(row["unexpected_tool_call"] for row in rows),
        "median_latency_seconds": statistics.median(row["elapsed_seconds"] for row in rows),
        "p95_latency_seconds": percentile([row["elapsed_seconds"] for row in rows], 0.95),
        "peak_ollama_rss_bytes": max(row["peak_ollama_rss_bytes"] for row in rows),
    }


def analyze(raw, dataset, preregistration):
    right_brain = RightBrain(load_model=False)
    cases = {case["case_id"]: case for case in dataset["cases"]}
    scores = [score_row(right_brain, row, cases[row["case_id"]]) for row in raw["rows"]]
    by_condition = {
        condition: [row for row in scores if row["condition"] == condition]
        for condition in CONDITIONS
    }
    metrics = {condition: aggregate(rows) for condition, rows in by_condition.items()}
    maps = {
        condition: {row["case_id"]: row for row in rows}
        for condition, rows in by_condition.items()
    }
    control = maps[CONDITIONS[0]]
    treatment = maps[CONDITIONS[1]]
    active_ids = [case_id for case_id, row in treatment.items() if row["contract_active"]]
    inactive_ids = [case_id for case_id, row in treatment.items() if not row["contract_active"]]
    comparison = {
        "new_v4_persona_passes": sum(
            treatment[case_id]["v4_persona_pass"] is True
            and control[case_id]["v4_persona_pass"] is not True
            for case_id in active_ids
        ),
        "v4_persona_regressions": sum(
            control[case_id]["v4_persona_pass"] is True
            and treatment[case_id]["v4_persona_pass"] is not True
            for case_id in active_ids
        ),
        "semantic_contract_regressions": sum(
            control[case_id]["semantic_contract_pass"]
            and not treatment[case_id]["semantic_contract_pass"]
            for case_id in treatment
        ),
        "surface_gate_regressions": sum(
            control[case_id]["surface_gate_pass"]
            and not treatment[case_id]["surface_gate_pass"]
            for case_id in treatment
        ),
        "specificity_intrusion_regressions": sum(
            control[case_id]["specificity_pass"]
            and not treatment[case_id]["specificity_pass"]
            for case_id in treatment
        ),
    }
    inactive_identity = sum(
        control[case_id]["raw_reply_sha256"] == treatment[case_id]["raw_reply_sha256"]
        for case_id in inactive_ids
    )
    gates = preregistration["model_gates"]
    control_metrics = metrics[CONDITIONS[0]]
    treatment_metrics = metrics[CONDITIONS[1]]
    integrity = {
        "row_count": len(scores) == raw["expected_model_call_count"] == 40,
        "unique_pairs": len({(row["case_id"], row["condition"]) for row in scores}) == 40,
        "preflight": raw["preflight"]["passed"] is True,
        "hash_bindings": raw["preregistration_sha256"] == sha(PREREGISTRATION)
        and raw["dataset_sha256"] == sha(DATASET),
        "no_gold": raw["gold_or_expected_reply_in_raw"] is False,
        "scorers_not_in_payload": raw["v4_scorer_in_model_payload"] is False
        and raw["specificity_scorer_in_model_payload"] is False,
        "holdout_unseen": raw["v2_holdout_content_review_count"] == 0,
    }
    checks = {
        "treatment_semantics": treatment_metrics["semantic_pass_rate"]
        >= gates["treatment_semantic_pass_rate_min"],
        "semantic_noninferiority": treatment_metrics["semantic_pass_rate"]
        - control_metrics["semantic_pass_rate"]
        >= gates["semantic_delta_vs_control_min"],
        "semantic_regressions": comparison["semantic_contract_regressions"]
        <= gates["semantic_contract_regressions_max"],
        "treatment_persona": treatment_metrics["v4_persona_pass_count"]
        >= gates["treatment_v4_persona_pass_count_min"],
        "new_persona_passes": comparison["new_v4_persona_passes"]
        >= gates["new_v4_persona_passes_min"],
        "persona_regressions": comparison["v4_persona_regressions"]
        <= gates["v4_persona_regressions_max"],
        "surface_regressions": comparison["surface_gate_regressions"]
        <= gates["surface_gate_regressions_max"],
        "specificity_regressions": comparison["specificity_intrusion_regressions"]
        <= gates["specificity_intrusion_regressions_max"],
        "inactive_identity": inactive_identity == gates["inactive_identity_count_exact"],
        "transport": sum(metric["transport_error_count"] for metric in metrics.values())
        <= gates["transport_error_count_max"],
        "unexpected_tools": sum(metric["unexpected_tool_call_count"] for metric in metrics.values())
        <= gates["unexpected_tool_call_count_max"],
        "production_memory": raw["production_memory_write_count"]
        <= gates["production_memory_write_count_max"],
        "physical_action": raw["physical_vrm_action_count"]
        <= gates["physical_vrm_action_count_max"],
        "median_latency": treatment_metrics["median_latency_seconds"]
        <= gates["median_latency_seconds_max"],
        "p95_latency": treatment_metrics["p95_latency_seconds"]
        <= gates["p95_latency_seconds_max"],
        "peak_rss": treatment_metrics["peak_ollama_rss_bytes"]
        <= gates["peak_ollama_rss_bytes_max"],
    }
    passed = all(integrity.values()) and all(checks.values())
    return {
        "schema": "uruha_public_persona_incremental_planner_analysis_v7",
        "experiment_id": preregistration["experiment_id"],
        "passed": passed,
        "decision": preregistration["decision_policy"]["pass" if passed else "fail"],
        "integrity": {"passed": all(integrity.values()), "checks": integrity},
        "model_gates": {"passed": all(checks.values()), "checks": checks},
        "metrics": metrics,
        "comparison": comparison,
        "inactive_identity_count": inactive_identity,
        "inactive_case_count": len(inactive_ids),
        "scores": scores,
        "authorizations": {
            "source_disjoint_incremental_planner_holdout": passed,
            "runtime_default_enable": False,
            "model_change": False,
            "training": False,
            "v2_holdout_unsealing": False,
            "persona_fidelity_claim": False,
        },
        "evidence_boundary": preregistration["evidence_boundary"],
    }


def markdown(report):
    lines = [
        "# 公開人格 Incremental Planner V7 結果",
        "",
        f"- 決策：`{report['decision']}`",
        "",
        "| 條件 | 原核心語意 | V4 人格 | 表面 gate | 具體性 | 中位延遲 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for condition in CONDITIONS:
        metric = report["metrics"][condition]
        lines.append(
            f"| {condition} | {metric['semantic_pass_count']}/{metric['row_count']} | "
            f"{metric['v4_persona_pass_count']}/{metric['v4_persona_case_count']} | "
            f"{metric['surface_gate_pass_count']}/{metric['row_count']} | "
            f"{metric['specificity_pass_count']}/{metric['specificity_case_count']} | "
            f"{metric['median_latency_seconds']:.3f}s |"
        )
    comparison = report["comparison"]
    lines.extend(
        [
            "",
            "## 配對差異",
            "",
            f"- 新增人格通過：{comparison['new_v4_persona_passes']}",
            f"- 人格退步：{comparison['v4_persona_regressions']}",
            f"- 原核心語意退步：{comparison['semantic_contract_regressions']}",
            f"- 表面 gate 退步：{comparison['surface_gate_regressions']}",
            f"- 具體資訊侵入退步：{comparison['specificity_intrusion_regressions']}",
            "",
            "## 證據邊界",
            "",
            report["evidence_boundary"],
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MD)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    report = analyze(load(args.raw), load(DATASET), load(PREREGISTRATION))
    if args.write:
        args.output_json.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        args.output_md.write_text(markdown(report) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "decision": report["decision"],
                "metrics": report["metrics"],
                "comparison": report["comparison"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
