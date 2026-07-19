#!/usr/bin/env python3
"""Analyze the frozen V80 local proxy review without publishing private rows."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import planner_supervision_proxy_review_v80 as v80
import planner_supervision_v76 as v76


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/planner_supervision_v80_proxy_review_contract.json"
REPORT_PATH = ROOT / "reports/planner_supervision_v80_proxy_review.json"
MARKDOWN_PATH = ROOT / "reports/planner_supervision_v80_proxy_review.md"
QUARANTINE_REPORT_PATH = ROOT / "reports/planner_supervision_v80_self_review_quarantine.json"


def _runtime_files_changed(parent_commit):
    output = subprocess.check_output(
        ["git", "diff", "--name-only", parent_commit, "--", "uruha_brain_mac.py", "uruha_web_ui.py"],
        cwd=ROOT,
        text=True,
    )
    return len([line for line in output.splitlines() if line.strip()])


def strict_human_rows_created_for_formal_run(current_count, quarantine_report=None):
    """Preserve run-time contamination even after reversible quarantine."""
    if quarantine_report is None:
        return current_count
    if quarantine_report.get("schema") != "uruha_planner_self_review_quarantine_report_v80":
        raise ValueError("unexpected V80 quarantine report schema")
    if quarantine_report.get("v80_formal_integrity_reclassified_as_pass") is not False:
        raise ValueError("quarantine cannot reclassify V80 formal integrity")
    before = quarantine_report.get("strict_rows_before")
    quarantined = quarantine_report.get("pilot_self_review_rows_quarantined")
    if not isinstance(before, int) or not isinstance(quarantined, int) or before < quarantined:
        raise ValueError("invalid V80 quarantine counts")
    return before


def _markdown(report):
    integrity = report["integrity"]
    counts = report["consensus_counts"]
    return "\n".join(
        [
            "# V80 本機代理 Plan 審查",
            "",
            f"- 完整性：{'通過' if integrity['passed'] else '未通過'}",
            f"- 雙模型一致接受：{counts.get('accept', 0)}/12",
            f"- 雙模型一致拒絕：{counts.get('reject', 0)}/12",
            f"- 意見不一致：{counts.get('disagreement', 0)}/12",
            f"- 不確定或未解析：{counts.get('uncertain', 0) + counts.get('unparsed', 0) + counts.get('incomplete', 0)}/12",
            f"- 弱監督候選：{report['proxy_approved_weak_supervision_count']} 筆",
            f"- 人類訓練授權：{'有' if report['strict_human_training_authorized'] else '無'}",
            f"- 結論：{report['decision']}",
            "",
            "這是 AI 代理審查，不是人類標註；結果不會自動進入正式訓練資料。",
            "",
        ]
    )


def main():
    contract = v76.load_json(CONTRACT_PATH)
    paths = {key: ROOT / value for key, value in contract["local_paths"].items()}
    current_strict_count = len(v76.load_jsonl(paths["strict_human_annotations"]))
    quarantine_report = v76.load_json(QUARANTINE_REPORT_PATH) if QUARANTINE_REPORT_PATH.exists() else None
    strict_during_run = strict_human_rows_created_for_formal_run(current_strict_count, quarantine_report)
    report = v80.analyze(
        v76.load_jsonl(paths["packet_queue"]),
        v76.load_jsonl(paths["raw_results"]),
        contract,
        strict_human_rows_created=strict_during_run,
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
