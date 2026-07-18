#!/usr/bin/env python3
"""Analyze and render the frozen V65 model screen."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cognitive_plan_model_screen_v65_core import CANDIDATES, CONDITIONS, analyze


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/cognitive_plan_model_screen_v65_preregistration.json"
DATASET_PATH = ROOT / "datasets/cognitive_plan_model_screen_v65.json"
RAW_PATH = ROOT / "reports/cognitive_plan_model_screen_v65_raw.json"
ANALYSIS_PATH = ROOT / "reports/cognitive_plan_model_screen_v65_analysis.json"
MARKDOWN_PATH = ROOT / "reports/cognitive_plan_model_screen_v65_analysis.md"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def analyze_raw(raw, dataset, config):
    report = analyze(raw["rows"], dataset, config)
    invariants = config["run_invariants"]
    integrity = {
        "warmup_call_count_exact": raw["warmup_call_count"] == invariants["warmup_call_count_exact"],
        "scored_model_call_count_exact": raw["scored_model_call_count"] == invariants["scored_model_call_count_exact"],
        "transport_attempt_count_exact": raw["transport_attempt_count"] == invariants["transport_attempt_count_exact"],
        "transport_error_count_zero": raw["transport_error_count"] == 0,
        "gold_absent": raw["gold_in_raw"] is False,
        "production_unchanged": raw["production_runtime_changed"] is False and raw["production_memory_read_or_write"] is False,
        "per_condition_case_count_exact": all(report["metrics"][condition]["case_count"] == 12 for condition in CONDITIONS),
        "one_warmup_per_condition": sorted(row["condition"] for row in raw["warmup_calls"]) == sorted(CONDITIONS),
    }
    if not all(integrity.values()):
        report["selected_candidate"] = None
        report["decision"] = "invalidate_run_integrity_failure"
    report.update({"schema": "uruha_cognitive_plan_model_screen_analysis_v65", "experiment_id": config["experiment_id"], "run_integrity": {"passed": all(integrity.values()), "checks": integrity}, "evidence_boundary": config["causal_boundary"], "production_runtime_changed": False})
    return report


def _markdown(report):
    labels = {"qwen25_7b_control": "Qwen2.5 7B", "qwen35_4b_candidate": "Qwen3.5 4B", "qwen35_9b_candidate": "Qwen3.5 9B"}
    lines = ["# V65 本機左腦模型篩選結果", "", f"**決策：** `{report['decision']}`", "", "| 模型 | 完整計畫 | 欄位正確 | 工具解析 | 中位延遲 | P95 | 峰值 RSS |", "|---|---:|---:|---:|---:|---:|---:|"]
    for condition in CONDITIONS:
        metric = report["metrics"][condition]
        lines.append(f"| {labels[condition]} | {metric['exact_case_count']}/12 ({metric['exact_case_accuracy']:.1%}) | {metric['exact_field_hits']}/{metric['exact_field_count']} ({metric['exact_field_accuracy']:.1%}) | {metric['tool_parse_success_count']}/12 | {metric['latency_median_seconds']:.2f}s | {metric['latency_p95_seconds']:.2f}s | {metric['peak_ollama_rss_bytes'] / 1073741824:.2f} GiB |")
    lines.extend(["", "## 候選門檻", ""])
    for candidate in CANDIDATES:
        pair = report["pairwise"][candidate]
        failed = [name for name, passed in pair["checks"].items() if not passed]
        lines.append(f"- **{labels[candidate]}**：新增答對 {pair['newly_correct_vs_control']} 題、退步 {pair['regressions_vs_control']} 題；{'通過' if pair['eligible'] else '未通過'}。")
        if failed:
            lines.append("  - 未通過：" + ", ".join(failed))
    lines.extend(["", "這是精確 function-call 計畫選擇測試，不代表完整聊天、右腦自然度或廣義人類相似度。", ""])
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
    print(json.dumps({"decision": report["decision"], "selected_candidate": report["selected_candidate"], "run_integrity": report["run_integrity"], "metrics": report["metrics"], "pairwise": report["pairwise"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
