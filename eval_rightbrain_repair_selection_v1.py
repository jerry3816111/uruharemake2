#!/usr/bin/env python3
"""Evaluate deterministic RightBrain repair candidate selection."""

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from build_rightbrain_repair_curriculum_v1 import _target_errors
from project_paths import (
    RIGHTBRAIN_REPAIR_SELECTION_EVAL_V1_REPORT_JSON_PATH,
    RIGHTBRAIN_REPAIR_SELECTION_EVAL_V1_REPORT_MD_PATH,
    RIGHTBRAIN_REPAIR_SELECTION_V1_DATASET_PATH,
)


TZ = ZoneInfo("Asia/Tokyo")


def _safe_rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else None


def _fmt_pct(value):
    return "n/a" if value is None else f"{100 * value:.1f}%"


def _required_group_hit_count(reply, payload):
    count = 0
    for group in payload.get("required_marker_groups") or []:
        if any(str(marker) and str(marker) in reply for marker in group):
            count += 1
    return count


def _candidate_errors(candidate, payload):
    annotated = [str(error) for error in candidate.get("detected_errors") or [] if str(error)]
    return annotated or _target_errors(str(candidate.get("text") or ""), payload)


def _candidate_score(candidate, payload):
    reply = str(candidate.get("text") or "")
    errors = _candidate_errors(candidate, payload)
    max_chars = int((payload.get("context") or {}).get("max_chars") or 80)
    required_hits = _required_group_hit_count(reply, payload)
    length_penalty = abs(len(reply) - min(max_chars, 42))
    return (
        1 if not errors else 0,
        -len(errors),
        required_hits,
        -length_penalty,
        -len(reply),
    )


def select_candidate(row):
    payload = row["contract_payload"]
    scored = []
    for index, candidate in enumerate(row["candidates"]):
        score = _candidate_score(candidate, payload)
        scored.append((score, -index, candidate))
    scored.sort(reverse=True)
    return scored[0][2]


def evaluate_selection_dataset(rows):
    results = []
    selected_error_counts = Counter()
    all_invalid_error_counts = Counter()
    selected_source_counts = Counter()
    invalid_selected_count = 0
    gold_selected_count = 0
    valid_selected_count = 0
    invalid_candidate_count = 0
    invalid_candidates_with_detected_errors = 0

    for row in rows:
        payload = row["contract_payload"]
        selected = select_candidate(row)
        selected_errors = _candidate_errors(selected, payload)
        selected_source_counts[selected["source"]] += 1
        selected_error_counts.update(selected_errors)
        if selected_errors:
            invalid_selected_count += 1
        else:
            valid_selected_count += 1
        if selected["candidate_id"] == row["gold_candidate_id"]:
            gold_selected_count += 1
        for candidate in row["candidates"]:
            if candidate["candidate_id"] == row["gold_candidate_id"]:
                continue
            invalid_candidate_count += 1
            errors = _candidate_errors(candidate, payload)
            if errors:
                invalid_candidates_with_detected_errors += 1
                all_invalid_error_counts.update(errors)
        results.append(
            {
                "id": row["id"],
                "category": row.get("category"),
                "source_repair_reason_family": row.get("source_repair_reason_family"),
                "candidate_count": len(row["candidates"]),
                "gold_candidate_id": row["gold_candidate_id"],
                "selected_candidate_id": selected["candidate_id"],
                "selected_source": selected["source"],
                "selected_is_gold": selected["candidate_id"] == row["gold_candidate_id"],
                "selected_errors": selected_errors,
                "selected_text": selected["text"],
            }
        )

    summary = {
        "case_count": len(rows),
        "candidate_count": sum(len(row["candidates"]) for row in rows),
        "invalid_candidate_count": invalid_candidate_count,
        "invalid_candidates_with_detected_errors": invalid_candidates_with_detected_errors,
        "invalid_candidate_error_detection_rate": _safe_rate(
            invalid_candidates_with_detected_errors,
            invalid_candidate_count,
        ),
        "gold_selection_count": gold_selected_count,
        "gold_selection_rate": _safe_rate(gold_selected_count, len(rows)),
        "valid_selection_count": valid_selected_count,
        "valid_selection_rate": _safe_rate(valid_selected_count, len(rows)),
        "invalid_selection_count": invalid_selected_count,
        "invalid_selection_rate": _safe_rate(invalid_selected_count, len(rows)),
        "selected_source_counts": dict(sorted(selected_source_counts.items())),
        "selected_error_counts": dict(sorted(selected_error_counts.items())),
        "invalid_candidate_error_counts": dict(sorted(all_invalid_error_counts.items())),
    }
    return summary, results


def build_report(rows):
    summary, results = evaluate_selection_dataset(rows)
    return {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_repair_selection_eval_v1",
        "research_boundary": (
            "This evaluates deterministic contract-based candidate selection, not a trained model. "
            "It proves the repair-selection dataset is machine-checkable and can support a future "
            "learned selector/verifier without exposing benchmark answers."
        ),
        "summary": summary,
        "cases": results,
        "conclusion_zh": (
            "右腦直接修復 LoRA 連續沒有淨增益後，下一步改成候選選擇問題："
            "先確定同一套合約規則能穩定分辨乾淨回答與錯誤回答，再把這個任務交給後續 selector/verifier 學習。"
        ),
    }


def write_markdown(report, path):
    summary = report["summary"]
    lines = [
        "# RightBrain Repair Selection Eval v1",
        "",
        "## 一句話結論",
        "",
        report["conclusion_zh"],
        "",
        "## 分數總表",
        "",
        "| 指標 | 結果 | 意義 |",
        "|---|---:|---|",
        f"| case_count | {summary['case_count']} | 選擇題數 |",
        f"| candidate_count | {summary['candidate_count']} | 候選總數 |",
        f"| invalid_candidate_error_detection_rate | {_fmt_pct(summary['invalid_candidate_error_detection_rate'])} | 錯誤候選可被規則檢出的比例 |",
        f"| gold_selection_rate | {_fmt_pct(summary['gold_selection_rate'])} | selector 選到乾淨候選的比例 |",
        f"| valid_selection_rate | {_fmt_pct(summary['valid_selection_rate'])} | selector 選到合約有效候選的比例 |",
        f"| invalid_selection_rate | {_fmt_pct(summary['invalid_selection_rate'])} | selector 錯選壞候選的比例；越低越好 |",
        "",
        "## 這對右腦的意義",
        "",
        "- F 右腦補強不是讓 ToMBench 推理變強，而是避免左腦已經想好的答案在最後表達層消失。",
        "- 直接讓小模型重生一句話效果不穩，所以這次把問題改成更可控的「多候選選擇」。",
        "- 這個 harness 先證明：錯誤候選能被合約規則穩定標出，後續才值得訓練 selector 或 verifier。",
        "",
        "## 被檢出的錯誤候選",
        "",
        "| 錯誤 | 數量 |",
        "|---|---:|",
    ]
    for error, count in sorted(summary["invalid_candidate_error_counts"].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {error} | {count} |")
    lines.extend(["", "## 抽樣個案", "", "| case | selected | gold | errors | text |", "|---|---|---|---|---|"])
    for row in report["cases"][:12]:
        errors = ",".join(row["selected_errors"]) if row["selected_errors"] else "none"
        lines.append(
            f"| {row['id']} | {row['selected_candidate_id']} | {row['gold_candidate_id']} | {errors} | {row['selected_text']} |"
        )
    lines.append("")
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=RIGHTBRAIN_REPAIR_SELECTION_V1_DATASET_PATH)
    parser.add_argument("--output-json", default=RIGHTBRAIN_REPAIR_SELECTION_EVAL_V1_REPORT_JSON_PATH)
    parser.add_argument("--output-md", default=RIGHTBRAIN_REPAIR_SELECTION_EVAL_V1_REPORT_MD_PATH)
    args = parser.parse_args()

    rows = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    report = build_report(rows)
    Path(args.output_json).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, args.output_md)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    success = (
        report["summary"]["invalid_candidate_error_detection_rate"] == 1.0
        and report["summary"]["gold_selection_rate"] == 1.0
        and report["summary"]["valid_selection_rate"] == 1.0
        and report["summary"]["invalid_selection_rate"] == 0.0
    )
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
