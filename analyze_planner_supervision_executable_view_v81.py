#!/usr/bin/env python3
"""Analyze V81 without publishing private packets, reasons or dialogue."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import planner_supervision_executable_view_v81 as v81
import planner_supervision_v76 as v76


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/planner_supervision_v81_executable_view_contract.json"
REPORT_PATH = ROOT / "reports/planner_supervision_v81_executable_view.json"
MARKDOWN_PATH = ROOT / "reports/planner_supervision_v81_executable_view.md"
RUNTIME_PATHS = (
    "uruha_brain_mac.py",
    "uruha_web_ui.py",
    "uruha_memory_runtime.py",
    "memory_consolidation.py",
)


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
    c0 = report["conditions"][v81.C0]
    t1 = report["conditions"][v81.T1]
    comparison = report["comparisons"]
    return "\n".join(
        [
            "# V81 可執行 Plan 視圖實驗",
            "",
            f"- 實驗完整性：{'通過' if report['integrity']['passed'] else '未通過'}",
            f"- 完整內部狀態評審一致率：{_percent(c0['original_interjudge_agreement'])}",
            f"- 可執行視圖評審一致率：{_percent(t1['original_interjudge_agreement'])}",
            f"- 一致率差值：{comparison['original_agreement_delta_t1_minus_c0'] * 100:.1f} percentage points",
            f"- 可執行視圖已知缺陷一致拒絕：{_percent(t1['mutation_unanimous_rejection_rate'])}",
            f"- 可執行視圖請求大小比例：{_percent(comparison['request_bytes_ratio_t1_vs_c0'])}",
            f"- 可執行視圖延遲比例：{_percent(comparison['mean_latency_ratio_t1_vs_c0'])}",
            f"- 成功門檻：{'通過' if report['success']['passed'] else '未通過'}",
            f"- 決策：`{report['decision']}`",
            "",
            "此結果只校準 AI 代理審查介面，不建立人類標籤，也不授權訓練或正式 runtime 修改。",
            "",
        ]
    )


def main():
    if REPORT_PATH.exists():
        existing = v76.load_json(REPORT_PATH)
        if existing.get("schema") == "uruha_planner_executable_view_abort_v81":
            raise SystemExit("V81 is closed; partial results are not analyzable")
    contract = v76.load_json(CONTRACT_PATH)
    paths = {key: ROOT / value for key, value in contract["local_paths"].items()}
    report = v81.analyze(
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
