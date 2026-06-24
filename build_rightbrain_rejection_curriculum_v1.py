#!/usr/bin/env python3
"""Build a targeted RightBrain SFT supplement from rejected model candidates."""

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from eval_rightbrain_model_surface_holdout import _case_inputs
from project_paths import (
    RIGHTBRAIN_MODEL_SURFACE_HOLDOUT_REPORT_JSON_PATH,
    RIGHTBRAIN_REJECTION_CURRICULUM_V1_DATASET_PATH,
    RIGHTBRAIN_REJECTION_CURRICULUM_V1_REPORT_JSON_PATH,
    RIGHTBRAIN_REJECTION_CURRICULUM_V1_REPORT_MD_PATH,
)
from uruha_brain_mac import RIGHT_BRAIN_MODEL_SYSTEM_PROMPT, RightBrain


TZ = ZoneInfo("Asia/Tokyo")


def _payload_for_case(rightbrain, case):
    logic = case["logic"]
    max_chars = (logic.get("constraints") or {}).get("max_chars", 80)
    return rightbrain._build_model_surface_payload(
        logic,
        case.get("psyche") or {},
        max_chars,
        memory_data=case.get("memory_data") or {},
    )


def _report_rows_by_id(report):
    return {str(row.get("id")): row for row in report.get("cases") or []}


def build_curriculum(report, cases=None):
    cases = list(cases or _case_inputs())
    report_rows = _report_rows_by_id(report)
    rightbrain = RightBrain(load_model=False)
    rows = []
    reason_counts = Counter()
    category_counts = Counter()
    skipped = Counter()

    for case in cases:
        report_row = report_rows.get(case["id"])
        if not report_row:
            skipped["missing_report_row"] += 1
            continue
        reasons = list(dict.fromkeys(report_row.get("model_rejection_reasons") or []))
        if not reasons:
            skipped["no_rejection"] += 1
            continue
        if not report_row.get("deterministic_quality_pass"):
            skipped["deterministic_target_failed"] += 1
            continue
        target_reply = str(report_row.get("deterministic_reply") or "").strip()
        if not target_reply:
            skipped["empty_target_reply"] += 1
            continue

        payload = _payload_for_case(rightbrain, case)
        payload_obj = json.loads(payload)
        if not payload_obj.get("required_marker_groups"):
            skipped["missing_payload_contract"] += 1
            continue

        rejection_examples = [
            {
                "raw_candidate": item.get("raw_candidate", ""),
                "rejection_reasons": item.get("rejection_reasons") or [],
            }
            for item in report_row.get("model_rejected_candidates") or []
        ]
        row = {
            "id": f"rb_rejection_curriculum_v1_{len(rows) + 1:04d}",
            "source_case_id": case["id"],
            "category": case["category"],
            "training_role": "rightbrain_rejection_repair_contract_v1_sft",
            "failure_reasons": reasons,
            "rejected_candidate_examples": rejection_examples,
            "target_source": "deterministic_final_surface_pass",
            "messages": [
                {"role": "system", "content": RIGHT_BRAIN_MODEL_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload_obj, ensure_ascii=False, separators=(",", ":"))},
                {"role": "assistant", "content": target_reply},
            ],
        }
        rows.append(row)
        category_counts[case["category"]] += 1
        for reason in reasons:
            reason_counts[reason] += 1

    summary = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_rejection_curriculum_v1",
        "source_report": Path(RIGHTBRAIN_MODEL_SURFACE_HOLDOUT_REPORT_JSON_PATH).name,
        "case_count": len(cases),
        "curriculum_row_count": len(rows),
        "skipped_counts": dict(skipped),
        "failure_reason_counts": dict(reason_counts),
        "category_counts": dict(category_counts),
        "training_boundary": (
            "Rejected raw model candidates are metadata only. The assistant targets are deterministic "
            "final-surface replies that already passed the holdout gate, so the model learns the correct "
            "contract-preserving output instead of learning leaked ASCII, Chinese, or missing-slot replies."
        ),
    }
    return rows, summary


def write_markdown(summary, rows, path):
    lines = [
        "# RightBrain Rejection Curriculum v1",
        "",
        "這份資料把右腦模型在 holdout 中被 gate 拒絕的案例，轉成下一輪 LoRA 的補強樣本。",
        "",
        "## 一句話結論",
        "",
        (
            "被拒絕的 raw candidate 只作為錯誤 metadata；真正訓練目標使用已通過 final-surface "
            "gate 的 deterministic 合格答案。"
        ),
        "",
        "## 總表",
        "",
        "| 指標 | 數值 |",
        "|---|---:|",
        f"| source case count | {summary['case_count']} |",
        f"| curriculum row count | {summary['curriculum_row_count']} |",
        "",
        "## 失敗原因分布",
        "",
    ]
    for reason, count in sorted(summary["failure_reason_counts"].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {reason}: {count}")
    lines.extend(["", "## 補強樣本", "", "| case | category | reasons | target reply |", "|---|---|---|---|"])
    for row in rows:
        reasons = ", ".join(row["failure_reasons"])
        target = row["messages"][-1]["content"]
        lines.append(f"| {row['source_case_id']} | {row['category']} | {reasons} | {target} |")
    lines.extend(["", "## 研究邊界", "", f"- {summary['training_boundary']}", ""])
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-report", default=RIGHTBRAIN_MODEL_SURFACE_HOLDOUT_REPORT_JSON_PATH)
    parser.add_argument("--output", default=RIGHTBRAIN_REJECTION_CURRICULUM_V1_DATASET_PATH)
    parser.add_argument("--summary-json", default=RIGHTBRAIN_REJECTION_CURRICULUM_V1_REPORT_JSON_PATH)
    parser.add_argument("--summary-md", default=RIGHTBRAIN_REJECTION_CURRICULUM_V1_REPORT_MD_PATH)
    args = parser.parse_args()

    report = json.loads(Path(args.source_report).read_text(encoding="utf-8"))
    rows, summary = build_curriculum(report)
    if not rows:
        raise RuntimeError("No rejected model candidates were converted into curriculum rows.")

    Path(args.output).write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.summary_json).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(summary, rows, args.summary_md)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
