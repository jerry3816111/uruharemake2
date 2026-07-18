#!/usr/bin/env python3
"""Analyze and render the frozen V66 decomposition pilot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cognitive_plan_decomposition_v66_core import CONDITIONS, MATCHED_CONTROL, ONE_CALL, TREATMENT, analyze


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/cognitive_plan_decomposition_v66_preregistration.json"
DATASET_PATH = ROOT / "datasets/cognitive_plan_decomposition_v66.json"
RAW_PATH = ROOT / "reports/cognitive_plan_decomposition_v66_raw.json"
ANALYSIS_PATH = ROOT / "reports/cognitive_plan_decomposition_v66_analysis.json"
MARKDOWN_PATH = ROOT / "reports/cognitive_plan_decomposition_v66_analysis.md"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def analyze_raw(raw, dataset, config):
    report = analyze(raw["rows"], dataset, config)
    invariants = config["run_invariants"]
    metrics = report["metrics"]
    integrity = {
        "warmup_transport_attempt_count_exact": raw["warmup_transport_attempt_count"] == invariants["warmup_transport_attempt_count_exact"],
        "scored_case_count_exact": raw["scored_case_count"] == 36,
        "scored_transport_attempt_count_exact": raw["scored_transport_attempt_count"] == invariants["scored_transport_attempt_count_exact"],
        "transport_attempt_count_exact": raw["transport_attempt_count"] == invariants["transport_attempt_count_exact"],
        "transport_error_count_zero": raw["transport_error_count"] == 0,
        "gold_absent": raw["gold_in_raw"] is False,
        "production_unchanged": raw["production_runtime_changed"] is False and raw["production_memory_read_or_write"] is False,
        "per_condition_case_count_exact": all(metrics[condition]["case_count"] == 12 for condition in CONDITIONS),
        "per_condition_transport_attempts_exact": (
            metrics[ONE_CALL]["transport_attempt_count"] == 12
            and metrics[MATCHED_CONTROL]["transport_attempt_count"] == 24
            and metrics[TREATMENT]["transport_attempt_count"] == 24
        ),
        "warmup_condition_count_exact": sorted(row["condition"] for row in raw["warmup_calls"]) == sorted(CONDITIONS),
    }
    if not all(integrity.values()):
        report["decision"] = "invalidate_run_integrity_failure"
        report["pairwise"]["treatment_vs_matched_control"]["eligible"] = False
    report.update({
        "schema": "uruha_cognitive_plan_decomposition_analysis_v66",
        "experiment_id": config["experiment_id"],
        "run_integrity": {"passed": all(integrity.values()), "checks": integrity},
        "evidence_boundary": config["causal_boundary"],
        "production_runtime_changed": False,
    })
    return report


def _markdown(report):
    labels = {
        ONE_CALL: "一階段完整計畫（參考）",
        MATCHED_CONTROL: "兩次完整計畫（配對控制）",
        TREATMENT: "選擇→決策（責任分解）",
    }
    lines = [
        "# V66 認知責任分解結果",
        "",
        f"**決策：** `{report['decision']}`",
        "",
        "| 條件 | 完整計畫 | 欄位正確 | 選擇子步驟 | 決策子步驟 | 工具解析 | 中位延遲 | P95 | 峰值 RSS |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for condition in CONDITIONS:
        metric = report["metrics"][condition]
        lines.append(
            f"| {labels[condition]} | {metric['exact_case_count']}/12 ({metric['exact_case_accuracy']:.1%}) "
            f"| {metric['exact_field_hits']}/{metric['exact_field_count']} ({metric['exact_field_accuracy']:.1%}) "
            f"| {metric['selection_stage_exact_count']}/12 | {metric['decision_stage_exact_count']}/12 "
            f"| {metric['all_required_tools_parse_count']}/12 "
            f"| {metric['latency_median_seconds_per_case']:.2f}s "
            f"| {metric['latency_p95_seconds_per_case']:.2f}s "
            f"| {metric['peak_ollama_rss_bytes'] / 1073741824:.2f} GiB |"
        )
    pair = report["pairwise"]["treatment_vs_matched_control"]
    failed = [name for name, passed in pair["checks"].items() if not passed]
    lines.extend([
        "",
        "## 主要因果比較",
        "",
        f"責任分解相對兩次完整重做：新增答對 {pair['newly_correct']} 題，退步 {pair['regressions']} 題。",
        f"預註冊門檻：{'全部通過' if pair['eligible'] else '未通過'}。",
    ])
    if failed:
        lines.append("未通過：" + ", ".join(failed))
    lines.extend([
        "",
        "一階段組使用較少模型呼叫，只作成本與絕對表現參考，不用來主張責任分解的因果效果。",
        "這是 planning packet 之後的精確計畫測試，不代表完整聊天、右腦自然度或廣義人類相似度。",
        "",
    ])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=RAW_PATH)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    report = analyze_raw(_load(args.raw), _load(DATASET_PATH), _load(PREREG_PATH))
    if args.write:
        ANALYSIS_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        MARKDOWN_PATH.write_text(_markdown(report), encoding="utf-8")
    print(json.dumps({
        "decision": report["decision"],
        "run_integrity": report["run_integrity"],
        "metrics": report["metrics"],
        "pairwise": report["pairwise"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
