#!/usr/bin/env python3
"""Build the private V79 pilot queue and aggregate readiness report."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import planner_supervision_pilot_review_v79 as v79
import planner_supervision_v76 as v76


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/planner_supervision_v79_pilot_review_contract.json"
TRACKED_REPORT_PATH = ROOT / "reports/planner_supervision_v79_pilot_review.json"
TRACKED_MARKDOWN_PATH = ROOT / "reports/planner_supervision_v79_pilot_review.md"


def _runtime_files_changed(parent_commit):
    output = subprocess.check_output(
        ["git", "diff", "--name-only", parent_commit, "--", "uruha_brain_mac.py", "uruha_web_ui.py"],
        cwd=ROOT,
        text=True,
    )
    return len([line for line in output.splitlines() if line.strip()])


def _markdown(report):
    return "\n".join(
        [
            "# V79 Planner Pilot Review",
            "",
            f"- 已認證候選：{report['certified_candidate_count']} 筆",
            f"- Pilot：{report['pilot_candidate_count']} 筆",
            f"- 能力類別覆蓋：{report['covered_scenario_family_count']}/{report['available_scenario_family_count']}",
            f"- Session 覆蓋：{report['covered_session_count']}/{report['available_session_count']}",
            f"- 已審：{report['reviewed_count']} 筆",
            f"- 接受：{report['accepted_count']} 筆",
            f"- 拒絕：{report['rejected_count']} 筆",
            f"- 待審：{report['pending_count']} 筆",
            f"- 訓練資料：{report['training_rows_created']} 筆",
            f"- 建構門檻：{'通過' if report['construction_gates']['passed'] else '未通過'}",
            "",
            "Pilot 只降低第一輪人工審查成本；未審候選仍不得進入訓練資料。",
            "",
        ]
    )


def build_report(contract):
    paths = {key: ROOT / value for key, value in contract["local_paths"].items()}
    candidates = v76.load_jsonl(paths["candidate_queue"])
    manifest = v76.load_jsonl(paths["session_manifest"])
    reviews = v76.load_jsonl(paths["review_log"])
    strict = v76.load_jsonl(paths["strict_annotations"])
    selection = contract["selection"]
    eligible, units = v79.select_pilot(
        candidates,
        manifest,
        budget=int(selection["budget"]),
        seed=selection["seed"],
    )
    v76.write_jsonl(paths["pilot_queue"], units)
    report = v79.build_aggregate_report(candidates, eligible, units, reviews, strict, contract)
    observed = {
        key: report[key]
        for key in contract["success_gates"]
        if key not in {"runtime_files_changed"}
    }
    observed["runtime_files_changed"] = _runtime_files_changed(contract["parent_commit"])
    expected = contract["success_gates"]
    checks = {key: observed[key] == expected[key] for key in expected}
    report["runtime_files_changed"] = observed["runtime_files_changed"]
    report["construction_gates"] = {"passed": all(checks.values()), "checks": checks}
    v76.atomic_write(paths["pilot_report"], json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tracked-report", action="store_true")
    args = parser.parse_args()
    contract = v76.load_json(CONTRACT_PATH)
    report = build_report(contract)
    if args.tracked_report:
        v76.atomic_write(TRACKED_REPORT_PATH, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        v76.atomic_write(TRACKED_MARKDOWN_PATH, _markdown(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["construction_gates"]["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
