#!/usr/bin/env python3
"""Analyze the frozen V11 paired realization-obligation screen."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import analyze_public_persona_payload_format_v10 as v10_analysis
from run_public_persona_realization_obligation_v11 import CONDITIONS
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
PREREGISTRATION = ROOT / "configs/public_persona_realization_obligation_v11_preregistration.json"
DATASET = ROOT / "datasets/public_persona_contract_v3_development.json"
DEFAULT_RAW = ROOT / "reports/public_persona_realization_obligation_v11_raw.json"
DEFAULT_JSON = ROOT / "reports/public_persona_realization_obligation_v11_analysis.json"
DEFAULT_MD = ROOT / "reports/public_persona_realization_obligation_v11_analysis.md"
TARGET_CASE = "persona_v3_notice_01"
TARGET_ROLE = "entry_point"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def analyze(raw, dataset, preregistration):
    right_brain = RightBrain(load_model=False)
    cases = {case["case_id"]: case for case in dataset["cases"]}
    scores = [
        v10_analysis.score_row(right_brain, row, cases[row["case_id"]])
        for row in raw["rows"]
    ]
    by_condition = {
        condition: [row for row in scores if row["condition"] == condition]
        for condition in CONDITIONS
    }
    metrics = {
        condition: v10_analysis.aggregate(rows)
        for condition, rows in by_condition.items()
    }
    maps = {
        condition: {row["case_id"]: row for row in rows}
        for condition, rows in by_condition.items()
    }
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

    target_recovered = (
        not control[TARGET_CASE]["role_hits"][TARGET_ROLE]
        and treatment[TARGET_CASE]["role_hits"][TARGET_ROLE]
    )
    baseline_identity_count = sum(
        next(row for row in raw["rows"] if row["case_id"] == case_id and row["condition"] == CONDITIONS[0])["baseline_payload_sha256"]
        == next(row for row in raw["rows"] if row["case_id"] == case_id and row["condition"] == CONDITIONS[1])["baseline_payload_sha256"]
        for case_id in cases
    )
    content_identity_count = sum(
        next(row for row in raw["rows"] if row["case_id"] == case_id and row["condition"] == CONDITIONS[0])["content_units_sha256"]
        == next(row for row in raw["rows"] if row["case_id"] == case_id and row["condition"] == CONDITIONS[1])["content_units_sha256"]
        for case_id in cases
    )
    gates = preregistration["model_gates"]
    cm, tm = metrics[CONDITIONS[0]], metrics[CONDITIONS[1]]
    integrity = {
        "row_count": len(scores) == raw["expected_model_call_count"] == 40,
        "unique_pairs": len({(row["case_id"], row["condition"]) for row in scores}) == 40,
        "preflight": raw["preflight"]["passed"] is True,
        "hash_bindings": raw["preregistration_sha256"] == sha(PREREGISTRATION)
        and raw["dataset_sha256"] == sha(DATASET),
        "paired_payload_identity": baseline_identity_count == 20 and content_identity_count == 20,
        "no_semantic_or_evaluator_leakage": raw["gold_or_expected_reply_in_raw"] is False
        and raw["role_scorer_in_model_payload"] is False
        and raw["v4_scorer_in_model_payload"] is False
        and raw["specificity_scorer_in_model_payload"] is False
        and raw["treatment_added_semantic_content_count"] == 0
        and raw["treatment_metadata_ascii_only"] is True,
        "holdout_unseen": raw["v2_holdout_content_review_count"] == 0,
    }
    checks = {
        "role_hit_delta": tm["role_hit_count"] - cm["role_hit_count"] >= gates["treatment_role_hit_delta_min"],
        "new_role_complete_cases": comparison["new_role_complete_cases"] >= gates["new_role_complete_cases_min"],
        "target_entry_point_recovered": target_recovered is gates["target_entry_point_recovered_exact"],
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
        "schema": "uruha_public_persona_realization_obligation_analysis_v11",
        "experiment_id": preregistration["experiment_id"],
        "passed": passed,
        "decision": preregistration["decision_policy"]["pass" if passed else "fail"],
        "integrity": {"passed": all(integrity.values()), "checks": integrity},
        "model_gates": {"passed": all(checks.values()), "checks": checks},
        "metrics": metrics,
        "comparison": comparison,
        "target_entry_point_recovered": target_recovered,
        "target_pair": {
            CONDITIONS[0]: control[TARGET_CASE]["raw_reply"],
            CONDITIONS[1]: treatment[TARGET_CASE]["raw_reply"],
        },
        "scores": scores,
        "authorizations": {
            "source_disjoint_realization_obligation_holdout": passed,
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
        "# 公開人格 Realization Obligation V11 結果",
        "",
        f"- 決策：`{report['decision']}`",
        f"- 目標 entry-point 恢復：{report['target_entry_point_recovered']}",
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
    lines.extend(
        [
            "",
            "## 診斷案例",
            "",
            f"- 控制：{report['target_pair'][CONDITIONS[0]]}",
            f"- 處理：{report['target_pair'][CONDITIONS[1]]}",
            "",
            "## 配對退步",
            "",
            f"- 角色槽／完整題：{report['comparison']['role_slot_regressions']} / {report['comparison']['role_complete_case_regressions']}",
            f"- 語意／人格／表面／具體性：{report['comparison']['semantic_contract_regressions']} / {report['comparison']['v4_persona_regressions']} / {report['comparison']['surface_gate_regressions']} / {report['comparison']['specificity_intrusion_regressions']}",
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
    print(json.dumps({"passed": report["passed"], "decision": report["decision"], "metrics": report["metrics"], "comparison": report["comparison"], "target_entry_point_recovered": report["target_entry_point_recovered"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
