#!/usr/bin/env python3
"""Analyze the frozen V10 payload-format screen."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path

import public_persona_missing_role_v8 as role_schema
import public_persona_scorer_contract_v4 as v4
import public_persona_specificity_scorer_v7 as specificity
from run_public_persona_payload_format_v10 import CONDITIONS
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
PREREGISTRATION = ROOT / "configs/public_persona_payload_format_v10_preregistration.json"
DATASET = ROOT / "datasets/public_persona_contract_v3_development.json"
DEFAULT_RAW = ROOT / "reports/public_persona_payload_format_v10_raw.json"
DEFAULT_JSON = ROOT / "reports/public_persona_payload_format_v10_analysis.json"
DEFAULT_MD = ROOT / "reports/public_persona_payload_format_v10_analysis.md"


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


def role_hits(reply, context):
    if context not in role_schema.ROLE_SCHEMAS:
        return {}
    return {
        item["role"]: any(marker in reply for marker in item["evidence_markers"])
        for item in role_schema.ROLE_SCHEMAS[context]
    }


def score_row(right_brain, raw_row, case):
    reply = raw_row["raw_reply"]
    semantic_hits = [
        marker_group_hit(right_brain, reply, group)
        for group in case["logic"]["required_marker_groups"]
    ]
    persona = v4.score_reply(reply, v4.compile_scorer_contract(case["context"]))
    specificity_result = specificity.score_specificity(reply, case)
    gate_reasons = right_brain._model_candidate_rejection_reasons(
        reply, case["logic"], case["persona_evaluation"]["maximum_characters"]
    )
    roles = role_hits(reply, case["context"])
    return {
        "case_id": case["case_id"],
        "context": case["context"],
        "condition": raw_row["condition"],
        "role_hits": roles,
        "role_complete": bool(roles) and all(roles.values()),
        "semantic_contract_pass": bool(semantic_hits) and all(semantic_hits),
        "v4_persona_scored": persona["scored"],
        "v4_persona_pass": persona["passed"],
        "v4_persona_reasons": persona["reasons"],
        "surface_gate_pass": not gate_reasons,
        "surface_gate_reasons": gate_reasons,
        "specificity_scored": specificity_result["scored"],
        "specificity_pass": specificity_result["passed"],
        "unsupported_concrete_markers": specificity_result["unsupported_concrete_markers"],
        "representation_integrity_pass": raw_row["representation_metadata"][
            "representation_integrity_pass"
        ],
        "canonical_payload_sha256": raw_row["canonical_payload_sha256"],
        "transport_error": raw_row["transport_error"],
        "unexpected_tool_call": bool(raw_row["tool_calls"]),
        "elapsed_seconds": raw_row["elapsed_seconds"],
        "peak_ollama_rss_bytes": raw_row["peak_ollama_rss_bytes"] or 0,
        "raw_reply": reply,
    }


def aggregate(rows):
    role_rows = [row for row in rows if row["role_hits"]]
    persona_rows = [row for row in rows if row["v4_persona_scored"]]
    specificity_rows = [row for row in rows if row["specificity_scored"]]
    return {
        "row_count": len(rows),
        "role_case_count": len(role_rows),
        "role_slot_count": sum(len(row["role_hits"]) for row in role_rows),
        "role_hit_count": sum(sum(row["role_hits"].values()) for row in role_rows),
        "role_complete_case_count": sum(row["role_complete"] for row in role_rows),
        "semantic_pass_count": sum(row["semantic_contract_pass"] for row in rows),
        "semantic_pass_rate": sum(row["semantic_contract_pass"] for row in rows) / len(rows),
        "v4_persona_case_count": len(persona_rows),
        "v4_persona_pass_count": sum(row["v4_persona_pass"] is True for row in persona_rows),
        "surface_gate_pass_count": sum(row["surface_gate_pass"] for row in rows),
        "specificity_case_count": len(specificity_rows),
        "specificity_pass_count": sum(row["specificity_pass"] for row in specificity_rows),
        "representation_integrity_count": sum(row["representation_integrity_pass"] for row in rows),
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
    maps = {condition: {row["case_id"]: row for row in rows} for condition, rows in by_condition.items()}
    control, treatment = maps[CONDITIONS[0]], maps[CONDITIONS[1]]
    comparison = {
        "new_role_complete_cases": 0,
        "role_complete_case_regressions": 0,
        "role_slot_wins": 0,
        "role_slot_regressions": 0,
        "semantic_contract_regressions": 0,
        "v4_persona_regressions": 0,
        "surface_gate_regressions": 0,
        "specificity_intrusion_regressions": 0,
    }
    for case_id in control:
        c, t = control[case_id], treatment[case_id]
        comparison["new_role_complete_cases"] += t["role_complete"] and not c["role_complete"]
        comparison["role_complete_case_regressions"] += c["role_complete"] and not t["role_complete"]
        for role in c["role_hits"]:
            comparison["role_slot_wins"] += t["role_hits"][role] and not c["role_hits"][role]
            comparison["role_slot_regressions"] += c["role_hits"][role] and not t["role_hits"][role]
        comparison["semantic_contract_regressions"] += c["semantic_contract_pass"] and not t["semantic_contract_pass"]
        comparison["v4_persona_regressions"] += c["v4_persona_pass"] is True and t["v4_persona_pass"] is not True
        comparison["surface_gate_regressions"] += c["surface_gate_pass"] and not t["surface_gate_pass"]
        comparison["specificity_intrusion_regressions"] += c["specificity_pass"] and not t["specificity_pass"]
    canonical_identity = sum(
        next(row for row in raw["rows"] if row["case_id"] == case_id and row["condition"] == CONDITIONS[0])["canonical_payload_sha256"]
        == next(row for row in raw["rows"] if row["case_id"] == case_id and row["condition"] == CONDITIONS[1])["canonical_payload_sha256"]
        for case_id in cases
    )
    gates = preregistration["model_gates"]
    cm, tm = metrics[CONDITIONS[0]], metrics[CONDITIONS[1]]
    integrity = {
        "row_count": len(scores) == raw["expected_model_call_count"] == 40,
        "unique_pairs": len({(row["case_id"], row["condition"]) for row in scores}) == 40,
        "preflight": raw["preflight"]["passed"] is True,
        "hash_bindings": raw["preregistration_sha256"] == sha(PREREGISTRATION) and raw["dataset_sha256"] == sha(DATASET),
        "no_gold_or_scorer_payload": raw["gold_or_expected_reply_in_raw"] is False
        and raw["role_scorer_in_model_payload"] is False
        and raw["v4_scorer_in_model_payload"] is False
        and raw["specificity_scorer_in_model_payload"] is False,
        "holdout_unseen": raw["v2_holdout_content_review_count"] == 0,
    }
    checks = {
        "canonical_identity": canonical_identity == gates["canonical_payload_identity_count_exact"],
        "representation_integrity": sum(m["representation_integrity_count"] for m in metrics.values()) == gates["representation_integrity_count_exact"],
        "role_hit_delta": tm["role_hit_count"] - cm["role_hit_count"] >= gates["treatment_role_hit_delta_min"],
        "new_role_complete_cases": comparison["new_role_complete_cases"] >= gates["new_role_complete_cases_min"],
        "role_slot_regressions": comparison["role_slot_regressions"] <= gates["role_slot_regressions_max"],
        "role_complete_regressions": comparison["role_complete_case_regressions"] <= gates["role_complete_case_regressions_max"],
        "treatment_semantics": tm["semantic_pass_rate"] >= gates["treatment_semantic_pass_rate_min"],
        "semantic_regressions": comparison["semantic_contract_regressions"] <= gates["semantic_contract_regressions_max"],
        "persona_regressions": comparison["v4_persona_regressions"] <= gates["v4_persona_regressions_max"],
        "surface_regressions": comparison["surface_gate_regressions"] <= gates["surface_gate_regressions_max"],
        "specificity_regressions": comparison["specificity_intrusion_regressions"] <= gates["specificity_intrusion_regressions_max"],
        "transport": sum(m["transport_error_count"] for m in metrics.values()) <= gates["transport_error_count_max"],
        "unexpected_tools": sum(m["unexpected_tool_call_count"] for m in metrics.values()) <= gates["unexpected_tool_call_count_max"],
        "production_memory": raw["production_memory_write_count"] <= gates["production_memory_write_count_max"],
        "physical_action": raw["physical_vrm_action_count"] <= gates["physical_vrm_action_count_max"],
        "median_latency": tm["median_latency_seconds"] <= gates["median_latency_seconds_max"],
        "p95_latency": tm["p95_latency_seconds"] <= gates["p95_latency_seconds_max"],
        "peak_rss": tm["peak_ollama_rss_bytes"] <= gates["peak_ollama_rss_bytes_max"],
    }
    passed = all(integrity.values()) and all(checks.values())
    return {
        "schema": "uruha_public_persona_payload_format_analysis_v10",
        "experiment_id": preregistration["experiment_id"],
        "passed": passed,
        "decision": preregistration["decision_policy"]["pass" if passed else "fail"],
        "integrity": {"passed": all(integrity.values()), "checks": integrity},
        "model_gates": {"passed": all(checks.values()), "checks": checks},
        "metrics": metrics,
        "comparison": comparison,
        "canonical_payload_identity_count": canonical_identity,
        "scores": scores,
        "authorizations": {
            "source_disjoint_payload_format_holdout": passed,
            "runtime_default_enable": False,
            "model_change": False,
            "scorer_change": False,
            "training": False,
            "v2_holdout_unsealing": False,
            "persona_fidelity_claim": False,
        },
        "evidence_boundary": preregistration["evidence_boundary"],
    }


def markdown(report):
    lines = [
        "# 公開人格 Payload Format V10 結果",
        "",
        f"- 決策：`{report['decision']}`",
        "",
        "| 條件 | 角色槽命中 | 角色完整題 | 原語意 | V4 人格 | 表面 gate | 中位延遲 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for condition in CONDITIONS:
        metric = report["metrics"][condition]
        lines.append(
            f"| {condition} | {metric['role_hit_count']}/{metric['role_slot_count']} | "
            f"{metric['role_complete_case_count']}/{metric['role_case_count']} | "
            f"{metric['semantic_pass_count']}/{metric['row_count']} | "
            f"{metric['v4_persona_pass_count']}/{metric['v4_persona_case_count']} | "
            f"{metric['surface_gate_pass_count']}/{metric['row_count']} | "
            f"{metric['median_latency_seconds']:.3f}s |"
        )
    comparison = report["comparison"]
    lines.extend(
        [
            "",
            "## 配對差異",
            "",
            f"- 新增角色完整題：{comparison['new_role_complete_cases']}",
            f"- 角色完整題退步：{comparison['role_complete_case_regressions']}",
            f"- 角色槽新增／退步：{comparison['role_slot_wins']} / {comparison['role_slot_regressions']}",
            f"- 語意／人格／表面／具體性退步：{comparison['semantic_contract_regressions']} / {comparison['v4_persona_regressions']} / {comparison['surface_gate_regressions']} / {comparison['specificity_intrusion_regressions']}",
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
        args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        args.output_md.write_text(markdown(report) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "decision": report["decision"], "metrics": report["metrics"], "comparison": report["comparison"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
