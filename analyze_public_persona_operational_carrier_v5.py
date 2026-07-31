#!/usr/bin/env python3
"""Analyze the frozen V5 three-level carrier mechanism screen."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path

import public_persona_scorer_contract_v4 as v4
from run_public_persona_operational_carrier_v5 import CONDITIONS
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
PREREGISTRATION = ROOT / "configs/public_persona_operational_carrier_v5_preregistration.json"
DATASET = ROOT / "datasets/public_persona_contract_v3_development.json"
DEFAULT_RAW = ROOT / "reports/public_persona_operational_carrier_v5_raw.json"
DEFAULT_JSON = ROOT / "reports/public_persona_operational_carrier_v5_analysis.json"
DEFAULT_MD = ROOT / "reports/public_persona_operational_carrier_v5_analysis.md"


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
        "transport_error": raw_row["transport_error"],
        "unexpected_tool_call": bool(raw_row["tool_calls"]),
        "elapsed_seconds": raw_row["elapsed_seconds"],
        "peak_ollama_rss_bytes": raw_row["peak_ollama_rss_bytes"] or 0,
        "raw_reply": reply,
        "raw_reply_sha256": raw_row["raw_reply_sha256"],
    }


def aggregate(rows):
    persona_rows = [row for row in rows if row["v4_persona_scored"]]
    return {
        "row_count": len(rows),
        "semantic_pass_count": sum(row["semantic_contract_pass"] for row in rows),
        "semantic_pass_rate": sum(row["semantic_contract_pass"] for row in rows) / len(rows),
        "v4_persona_case_count": len(persona_rows),
        "v4_persona_pass_count": sum(row["v4_persona_pass"] is True for row in persona_rows),
        "v4_persona_pass_rate": sum(row["v4_persona_pass"] is True for row in persona_rows)
        / len(persona_rows),
        "surface_gate_pass_count": sum(row["surface_gate_pass"] for row in rows),
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
    treatment = maps[CONDITIONS[2]]
    active_ids = [case_id for case_id, row in treatment.items() if row["contract_active"]]
    inactive_ids = [case_id for case_id, row in treatment.items() if not row["contract_active"]]
    comparisons = {}
    for control_name in CONDITIONS[:2]:
        control = maps[control_name]
        comparisons[control_name] = {
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
            "surface_gate_regressions": sum(
                control[case_id]["surface_gate_pass"]
                and not treatment[case_id]["surface_gate_pass"]
                for case_id in treatment
            ),
        }
    inactive_identity = sum(
        len({maps[condition][case_id]["raw_reply_sha256"] for condition in CONDITIONS}) == 1
        for case_id in inactive_ids
    )
    gates = preregistration["model_gates"]
    treatment_metrics = metrics[CONDITIONS[2]]
    integrity = {
        "row_count": len(scores) == raw["expected_model_call_count"] == 60,
        "unique_pairs": len({(row["case_id"], row["condition"]) for row in scores}) == 60,
        "preflight": raw["preflight"]["passed"] is True,
        "hash_bindings": raw["preregistration_sha256"] == sha(PREREGISTRATION)
        and raw["dataset_sha256"] == sha(DATASET),
        "no_gold": raw["gold_or_expected_reply_in_raw"] is False,
        "scorer_not_in_payload": raw["v4_scorer_in_model_payload"] is False,
        "holdout_unseen": raw["v2_holdout_content_review_count"] == 0,
    }
    checks = {
        "treatment_semantics": treatment_metrics["semantic_pass_rate"]
        >= gates["treatment_semantic_pass_rate_min"],
        "semantic_noninferiority": all(
            treatment_metrics["semantic_pass_rate"] - metrics[name]["semantic_pass_rate"]
            >= gates["treatment_semantic_delta_vs_each_control_min"]
            for name in CONDITIONS[:2]
        ),
        "treatment_persona": treatment_metrics["v4_persona_pass_count"]
        >= gates["treatment_v4_persona_pass_count_min"],
        "new_persona_passes": all(
            comparison["new_v4_persona_passes"]
            >= gates["new_v4_persona_passes_vs_each_control_min"]
            for comparison in comparisons.values()
        ),
        "persona_regressions": all(
            comparison["v4_persona_regressions"]
            <= gates["v4_persona_regressions_vs_each_control_max"]
            for comparison in comparisons.values()
        ),
        "treatment_surface": treatment_metrics["surface_gate_pass_count"]
        >= gates["treatment_surface_gate_pass_count_min"],
        "surface_regressions": all(
            comparison["surface_gate_regressions"]
            <= gates["surface_gate_regressions_vs_each_control_max"]
            for comparison in comparisons.values()
        ),
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
        "schema": "uruha_public_persona_operational_carrier_analysis_v5",
        "experiment_id": preregistration["experiment_id"],
        "passed": passed,
        "decision": preregistration["decision_policy"]["pass" if passed else "fail"],
        "integrity": {"passed": all(integrity.values()), "checks": integrity},
        "model_gates": {"passed": all(checks.values()), "checks": checks},
        "metrics": metrics,
        "comparisons": comparisons,
        "inactive_identity_count": inactive_identity,
        "inactive_case_count": len(inactive_ids),
        "scores": scores,
        "authorizations": {
            "source_disjoint_operational_carrier_holdout": passed,
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
        "# 公開人格 Operational Carrier V5 結果",
        "",
        f"- 決策：`{report['decision']}`",
        "",
        "| 條件 | 語意 | V4 人格 | 表面 gate | 中位延遲 |",
        "|---|---:|---:|---:|---:|",
    ]
    for condition in CONDITIONS:
        metric = report["metrics"][condition]
        lines.append(
            f"| {condition} | {metric['semantic_pass_count']}/{metric['row_count']} | "
            f"{metric['v4_persona_pass_count']}/{metric['v4_persona_case_count']} | "
            f"{metric['surface_gate_pass_count']}/{metric['row_count']} | "
            f"{metric['median_latency_seconds']:.3f}s |"
        )
    lines.extend(["", "## 配對差異", ""])
    for control, comparison in report["comparisons"].items():
        lines.append(
            f"- vs `{control}`：新增人格通過 {comparison['new_v4_persona_passes']}、"
            f"人格退步 {comparison['v4_persona_regressions']}、"
            f"表面退步 {comparison['surface_gate_regressions']}。"
        )
    lines.extend(["", "## 證據邊界", "", report["evidence_boundary"]])
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
        args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        args.output_md.write_text(markdown(report) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "decision": report["decision"], "metrics": report["metrics"], "comparisons": report["comparisons"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
