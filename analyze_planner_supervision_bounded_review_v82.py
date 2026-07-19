#!/usr/bin/env python3
"""Analyze V82 and publish aggregate-only evidence."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import planner_supervision_bounded_review_v82 as v82
import planner_supervision_v76 as v76


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/planner_supervision_v82_bounded_review_contract.json"
REPORT_PATH = ROOT / "reports/planner_supervision_v82_bounded_review.json"
MARKDOWN_PATH = ROOT / "reports/planner_supervision_v82_bounded_review.md"
RUNTIME_PATHS = ("uruha_brain_mac.py", "uruha_web_ui.py", "uruha_memory_runtime.py", "memory_consolidation.py")


def _runtime_files_changed(parent_commit):
    output = subprocess.check_output(
        ["git", "diff", "--name-only", parent_commit, "--", *RUNTIME_PATHS],
        cwd=ROOT,
        text=True,
    )
    return len([line for line in output.splitlines() if line.strip()])


def _percent(value):
    return "n/a" if value is None else f"{value * 100:.1f}%"


def _markdown(report):
    c0 = report["conditions"][v82.C0]
    t1 = report["conditions"][v82.T1]
    comparison = report["comparisons"]
    lines = [
            "# V82 有界代理 Plan 審查",
            "",
            f"- 完整性：{'通過' if report['integrity']['passed'] else '未通過'}",
            f"- 場景分布：{report['scenario_family_counts']}",
            f"- Transport failure：{report['integrity']['observed']['transport_failure_count']}",
            f"- Parse failure：{report['integrity']['observed']['parse_failure_count']}",
            f"- 失敗分布：{report['failure_distribution']}",
            f"- 正式比較指標授權：{'有' if report['comparative_metrics_authorized'] else '無'}",
    ]
    if report["comparative_metrics_authorized"]:
        lines.extend(
            [
            f"- 完整狀態評審一致率：{_percent(c0['original_interjudge_agreement'])}",
            f"- 可執行視圖評審一致率：{_percent(t1['original_interjudge_agreement'])}",
            f"- 一致率差值：{comparison['original_agreement_delta_t1_minus_c0'] * 100:.1f} percentage points",
            f"- 可執行視圖已知缺陷一致拒絕：{_percent(t1['mutation_unanimous_rejection_rate'])}",
            f"- 可執行視圖預期缺陷碼命中：{_percent(t1['mutation_expected_code_rate'])}",
            f"- 請求大小比例：{_percent(comparison['request_bytes_ratio_t1_vs_c0'])}",
            f"- 延遲比例：{_percent(comparison['mean_latency_ratio_t1_vs_c0'])}",
            ]
        )
    else:
        lines.extend(
            [
                f"- 部分資料診斷：精簡視圖已知缺陷一致拒絕 {_percent(t1['mutation_unanimous_rejection_rate'])}",
                f"- 部分資料診斷：預期缺陷碼命中 {_percent(t1['mutation_expected_code_rate'])}",
                "- 原始一致率、大小與延遲比較因完整性失敗，不作正式效果主張",
            ]
        )
    lines.extend(
        [
            f"- 成功門檻：{'通過' if report['success']['passed'] else '未通過'}",
            f"- 決策：`{report['decision']}`",
            "",
            "這只校準本機 AI 代理審查，不建立人類標籤，也不授權訓練或正式 runtime 修改。",
            "",
        ]
    )
    return "\n".join(lines)


def main():
    contract = v76.load_json(CONTRACT_PATH)
    paths = {key: ROOT / value for key, value in contract["local_paths"].items()}
    report = v82.analyze(
        v76.load_jsonl(paths["packet_queue"]),
        v76.load_jsonl(paths["raw_results"]),
        contract,
        production_runtime_files_changed=_runtime_files_changed(contract["parent_commit"]),
    )
    v76.atomic_write(paths["local_analysis"], json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    v76.atomic_write(REPORT_PATH, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    v76.atomic_write(MARKDOWN_PATH, _markdown(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["integrity"]["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
