#!/usr/bin/env python3
"""Analyze the V3 matched static-vs-conditional development model screen."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path

from project_paths import (
    PUBLIC_PERSONA_CONTRACT_V3_ANALYSIS_JSON_PATH,
    PUBLIC_PERSONA_CONTRACT_V3_ANALYSIS_MD_PATH,
    PUBLIC_PERSONA_CONTRACT_V3_DATASET_PATH,
    PUBLIC_PERSONA_CONTRACT_V3_RAW_PATH,
)
from run_public_persona_contract_v3_development import CONDITIONS
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
PREREGISTRATION = ROOT / "configs/public_persona_contract_v3_preregistration.json"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def percentile(values, probability):
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, max(0, int(len(ordered) * probability + 0.999999) - 1))
    return ordered[index]


def marker_group_hit(right_brain, reply, group):
    return any(right_brain._semantic_marker_hit(reply, marker) for marker in group)


def score_row(right_brain, raw_row, case):
    reply = raw_row["raw_reply"]
    semantic_groups = case["logic"]["required_marker_groups"]
    semantic_hits = [marker_group_hit(right_brain, reply, group) for group in semantic_groups]
    persona = case["persona_evaluation"]
    persona_groups = persona["marker_groups"]
    persona_hits = [marker_group_hit(right_brain, reply, group) for group in persona_groups]
    forbidden_hits = [term for term in persona["forbidden_substrings"] if term in reply]
    ordering = persona.get("ordering_pair")
    ordering_pass = True
    if ordering:
        first = reply.find(ordering[0])
        second = reply.find(ordering[1])
        ordering_pass = first >= 0 and second >= 0 and first < second
    persona_active = bool(persona_groups)
    persona_pass = (
        all(persona_hits)
        and not forbidden_hits
        and len(reply) <= int(persona["maximum_characters"]) + 2
        and ordering_pass
        if persona_active
        else None
    )
    gate_reasons = right_brain._model_candidate_rejection_reasons(
        reply,
        case["logic"],
        persona["maximum_characters"],
    )
    return {
        "case_id": case["case_id"],
        "context": case["context"],
        "condition": raw_row["condition"],
        "contract_active": raw_row["contract_active"],
        "semantic_group_hit_count": sum(semantic_hits),
        "semantic_group_count": len(semantic_hits),
        "semantic_contract_pass": bool(semantic_hits) and all(semantic_hits),
        "persona_policy_scored": persona_active,
        "persona_marker_hit_count": sum(persona_hits),
        "persona_marker_count": len(persona_hits),
        "persona_policy_pass": persona_pass,
        "persona_forbidden_hits": forbidden_hits,
        "ordering_pass": ordering_pass,
        "surface_gate_reasons": gate_reasons,
        "surface_gate_pass": not gate_reasons,
        "transport_error": raw_row["transport_error"],
        "unexpected_tool_call": bool(raw_row["tool_calls"]),
        "elapsed_seconds": raw_row["elapsed_seconds"],
        "peak_ollama_rss_bytes": raw_row["peak_ollama_rss_bytes"] or 0,
        "raw_reply": reply,
        "raw_reply_sha256": raw_row["raw_reply_sha256"],
    }


def aggregate(rows):
    persona_rows = [row for row in rows if row["persona_policy_scored"]]
    return {
        "row_count": len(rows),
        "semantic_contract_pass_count": sum(row["semantic_contract_pass"] for row in rows),
        "semantic_contract_pass_rate": sum(row["semantic_contract_pass"] for row in rows) / len(rows),
        "surface_gate_pass_count": sum(row["surface_gate_pass"] for row in rows),
        "persona_policy_case_count": len(persona_rows),
        "persona_policy_pass_count": sum(row["persona_policy_pass"] is True for row in persona_rows),
        "persona_policy_pass_rate": (
            sum(row["persona_policy_pass"] is True for row in persona_rows) / len(persona_rows)
            if persona_rows
            else None
        ),
        "persona_forbidden_case_count": sum(bool(row["persona_forbidden_hits"]) for row in rows),
        "transport_error_count": sum(bool(row["transport_error"]) for row in rows),
        "unexpected_tool_call_count": sum(row["unexpected_tool_call"] for row in rows),
        "median_latency_seconds": statistics.median(row["elapsed_seconds"] for row in rows),
        "p95_latency_seconds": percentile([row["elapsed_seconds"] for row in rows], 0.95),
        "peak_ollama_rss_bytes": max(row["peak_ollama_rss_bytes"] for row in rows),
    }


def analyze(raw, dataset, preregistration):
    right_brain = RightBrain(load_model=False)
    cases = {row["case_id"]: row for row in dataset["cases"]}
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
    newly_passed = sum(
        treatment[case_id]["persona_policy_pass"] is True
        and control[case_id]["persona_policy_pass"] is not True
        for case_id in active_ids
    )
    regressions = sum(
        control[case_id]["persona_policy_pass"] is True
        and treatment[case_id]["persona_policy_pass"] is not True
        for case_id in active_ids
    )
    inactive_identity = sum(
        control[case_id]["raw_reply_sha256"] == treatment[case_id]["raw_reply_sha256"]
        for case_id in inactive_ids
    )
    treatment_metrics = metrics[CONDITIONS[1]]
    control_metrics = metrics[CONDITIONS[0]]
    gates = preregistration["development_model_gates"]
    integrity = {
        "row_count": len(scores) == raw["expected_model_call_count"] == 40,
        "unique_pairs": len({(row["case_id"], row["condition"]) for row in scores}) == 40,
        "preflight": raw["preflight"]["passed"] is True,
        "hash_bindings": raw["preregistration_sha256"] == sha(PREREGISTRATION)
        and raw["dataset_sha256"] == sha(PUBLIC_PERSONA_CONTRACT_V3_DATASET_PATH),
        "no_gold_in_raw": raw["gold_or_expected_reply_in_raw"] is False,
        "holdout_unseen": raw["v2_holdout_content_review_count"] == 0,
    }
    checks = {
        "treatment_semantics": treatment_metrics["semantic_contract_pass_rate"]
        >= gates["treatment_semantic_contract_pass_rate_min"],
        "semantic_noninferiority": treatment_metrics["semantic_contract_pass_rate"]
        - control_metrics["semantic_contract_pass_rate"]
        >= gates["semantic_contract_pass_rate_delta_vs_control_min"],
        "treatment_persona": treatment_metrics["persona_policy_pass_rate"]
        >= gates["treatment_persona_policy_pass_rate_min"],
        "new_persona_passes": newly_passed
        >= gates["newly_persona_policy_passed_vs_control_min"],
        "persona_regressions": regressions
        <= gates["persona_policy_regressions_vs_control_max"],
        "inactive_identity": inactive_identity / len(inactive_ids)
        >= gates["inactive_raw_reply_identity_rate_min"],
        "private_or_forbidden": treatment_metrics["persona_forbidden_case_count"]
        <= gates["private_or_forbidden_intrusion_count_max"],
        "unexpected_tools": sum(metric["unexpected_tool_call_count"] for metric in metrics.values())
        <= gates["unexpected_tool_call_count_max"],
        "production_memory": raw["production_memory_write_count"]
        <= gates["production_memory_write_count_max"],
        "physical_action": raw["physical_vrm_action_count"]
        <= gates["physical_vrm_action_count_max"],
        "transport": sum(metric["transport_error_count"] for metric in metrics.values())
        <= gates["transport_error_count_max"],
        "median_latency": treatment_metrics["median_latency_seconds"]
        <= gates["median_latency_seconds_max"],
        "p95_latency": treatment_metrics["p95_latency_seconds"]
        <= gates["p95_latency_seconds_max"],
        "peak_rss": treatment_metrics["peak_ollama_rss_bytes"]
        <= gates["peak_ollama_rss_bytes_max"],
    }
    integrity_passed = all(integrity.values())
    passed = integrity_passed and all(checks.values())
    return {
        "schema": "uruha_public_persona_contract_development_analysis_v3",
        "experiment_id": preregistration["experiment_id"],
        "passed": passed,
        "decision": (
            "authorize_explicit_context_perception_development_only"
            if passed
            else "freeze_v3_negative_result_and_reassess_carrier_model_or_scorer"
        ),
        "integrity": {"passed": integrity_passed, "checks": integrity},
        "model_gates": {"passed": all(checks.values()), "checks": checks},
        "metrics": metrics,
        "paired": {
            "newly_persona_policy_passed_vs_control": newly_passed,
            "persona_policy_regressions_vs_control": regressions,
            "inactive_raw_reply_identity_count": inactive_identity,
            "inactive_case_count": len(inactive_ids),
        },
        "scores": scores,
        "authorizations": {
            "context_perception_development": passed,
            "holdout_unsealing": False,
            "runtime_default_enable": False,
            "training": False,
            "persona_fidelity_claim": False,
        },
        "evidence_boundary": preregistration["evidence_boundary"],
    }


def markdown(report):
    lines = [
        "# 公開人格條件契約 V3 本機模型結果",
        "",
        f"- 決策：`{report['decision']}`",
        "- 只比較固定人格 brief 與條件式 surface brief；其他輸入相同。",
        "",
        "| 條件 | 語意通過 | 人格策略通過 | 表面 gate | 中位延遲 |",
        "|---|---:|---:|---:|---:|",
    ]
    for condition in CONDITIONS:
        metric = report["metrics"][condition]
        lines.append(
            f"| {condition} | {metric['semantic_contract_pass_count']}/{metric['row_count']} | "
            f"{metric['persona_policy_pass_count']}/{metric['persona_policy_case_count']} | "
            f"{metric['surface_gate_pass_count']}/{metric['row_count']} | "
            f"{metric['median_latency_seconds']:.3f}s |"
        )
    paired = report["paired"]
    lines.extend(
        [
            "",
            f"- 新增人格策略通過：{paired['newly_persona_policy_passed_vs_control']} cases",
            f"- 人格策略退步：{paired['persona_policy_regressions_vs_control']} cases",
            f"- 非適用情境輸出完全一致：{paired['inactive_raw_reply_identity_count']}/{paired['inactive_case_count']}",
            "",
            "## 證據邊界",
            "",
            report["evidence_boundary"],
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=PUBLIC_PERSONA_CONTRACT_V3_RAW_PATH)
    parser.add_argument("--output-json", type=Path, default=PUBLIC_PERSONA_CONTRACT_V3_ANALYSIS_JSON_PATH)
    parser.add_argument("--output-md", type=Path, default=PUBLIC_PERSONA_CONTRACT_V3_ANALYSIS_MD_PATH)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    report = analyze(load(args.raw), load(PUBLIC_PERSONA_CONTRACT_V3_DATASET_PATH), load(PREREGISTRATION))
    if args.write:
        args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        args.output_md.write_text(markdown(report) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "decision": report["decision"], "metrics": report["metrics"], "paired": report["paired"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
