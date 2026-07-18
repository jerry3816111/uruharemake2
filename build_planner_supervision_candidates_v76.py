#!/usr/bin/env python3
"""Build local pending planner-supervision candidates from existing Web logs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from planner_supervision_v76 import (
    CONTRACT_PATH,
    ROOT,
    WEB_LOG_PATH,
    build_candidates,
    load_json,
    load_jsonl,
    write_candidate_outputs,
)


TRACKED_REPORT_PATH = ROOT / "reports/planner_supervision_v76_collection_diagnostic.json"
TRACKED_MARKDOWN_PATH = ROOT / "reports/planner_supervision_v76_collection_diagnostic.md"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--web-log", type=Path, default=WEB_LOG_PATH)
    parser.add_argument("--candidate-output", type=Path)
    parser.add_argument("--local-report", type=Path)
    parser.add_argument("--tracked-report", action="store_true")
    args = parser.parse_args()

    contract = load_json(CONTRACT_PATH)
    local_paths = contract["local_paths"]
    candidate_output = args.candidate_output or ROOT / local_paths["candidate_queue"]
    local_report = args.local_report or ROOT / local_paths["candidate_report"]
    records = load_jsonl(args.web_log)
    report = build_candidates(records, contract=contract)
    write_candidate_outputs(report, candidate_output, local_report)

    if args.tracked_report:
        tracked = {
            "schema": "uruha_planner_supervision_collection_diagnostic_v76",
            "web_log_exists": args.web_log.exists(),
            "web_log_path": str(args.web_log.relative_to(ROOT)) if args.web_log.is_relative_to(ROOT) else str(args.web_log),
            "candidate_output_is_gitignored_local_state": True,
            "summary": report["summary"],
            "exclusion_reason_counts": report["exclusion_reason_counts"],
            "runtime_changed": False,
            "model_calls_made": 0,
            "decision": "collection_path_ready_no_real_candidates" if not report["candidates"] else "pending_candidates_require_human_review",
            "evidence_boundary": report["evidence_boundary"],
        }
        TRACKED_REPORT_PATH.write_text(json.dumps(tracked, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        TRACKED_MARKDOWN_PATH.write_text(
            "\n".join(
                [
                    "# V76 規劃器資料收集診斷",
                    "",
                    f"- Web log 存在：{'是' if tracked['web_log_exists'] else '否'}",
                    f"- 讀取回合：{report['summary']['source_record_count']}",
                    f"- pending 候選：{report['summary']['candidate_count']}",
                    f"- 額外模型呼叫：{report['summary']['additional_model_calls']}",
                    f"- 建立 train 資料：{report['summary']['training_rows_created']}",
                    "- runtime 修改：否",
                    "",
                    "目前乾淨 clone 沒有本機 Web log，因此沒有真實候選。管線是否正確由隔離 fixture 測試驗證；這不是對話能力提升證據。",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
