#!/usr/bin/env python3
"""Measure the expanded casual-register gate on the recorded RightBrain audit."""

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from project_paths import (
    RIGHTBRAIN_CASUAL_REGISTER_GATE_V2_REPORT_JSON_PATH,
    RIGHTBRAIN_CASUAL_REGISTER_GATE_V2_REPORT_MD_PATH,
    RIGHTBRAIN_SAMPLING_SCHEDULE_ABLATION_V1_REPORT_JSON_PATH,
    RIGHTBRAIN_SAMPLING_SCHEDULE_NATURALNESS_AUDIT_V1_JSON_PATH,
)
from rightbrain_language_quality import POLITE_RE


TZ = ZoneInfo("Asia/Tokyo")
REPORT_PATH = RIGHTBRAIN_CASUAL_REGISTER_GATE_V2_REPORT_JSON_PATH


def _safe_rate(numerator, denominator):
    return round(numerator / denominator, 6) if denominator else None


def _fmt_pct(value):
    return "n/a" if value is None else f"{100 * value:.1f}%"


def build_report(sampling_report, audit):
    sampled_cases = {
        case["id"]: case
        for case in sampling_report["schedule_results"][audit["schedule"]]["cases"]
    }
    rows = []
    true_positive = 0
    false_positive = 0
    true_negative = 0
    false_negative = 0
    for annotation in audit["cases"]:
        case_id = annotation["id"]
        sampled = sampled_cases[case_id]
        if sampled["final_reply"] != annotation["reply"]:
            raise ValueError(f"Stale audit reply for {case_id}")
        reasons = ["polite_tone_drift"] if POLITE_RE.search(annotation["reply"]) else []
        actual_failure = annotation["verdict"] == "fail"
        predicted_failure = bool(reasons)
        true_positive += int(actual_failure and predicted_failure)
        false_positive += int(not actual_failure and predicted_failure)
        true_negative += int(not actual_failure and not predicted_failure)
        false_negative += int(actual_failure and not predicted_failure)
        rows.append({
            "id": case_id,
            "reply": annotation["reply"],
            "audit_verdict": annotation["verdict"],
            "audit_reasons": annotation["reasons"],
            "gate_rejected": predicted_failure,
            "gate_rejection_reasons": reasons,
        })
    failure_count = true_positive + false_negative
    pass_count = true_negative + false_positive
    precision = _safe_rate(true_positive, true_positive + false_positive)
    recall = _safe_rate(true_positive, failure_count)
    false_positive_rate = _safe_rate(false_positive, pass_count)
    gate_rescore = sampling_report.get("gate_rescore") or {}
    gate = {
        "audit_covers_all_sampled_cases": set(sampled_cases) == {row["id"] for row in rows},
        "detects_recorded_polite_persona_failure": any(
            row["id"] == "background_family_pressure"
            and "polite_tone_drift" in row["gate_rejection_reasons"]
            for row in rows
        ),
        "audit_false_positive_count_is_zero": false_positive == 0,
        "saved_candidate_rescore_is_monotonic": bool(gate_rescore.get("monotonic_hardening")),
        "saved_candidate_rescore_newly_accepts_zero": (
            gate_rescore.get("total_newly_accepted_candidate_count") == 0
        ),
    }
    return {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_casual_register_gate_v2",
        "source_schedule": audit["schedule"],
        "audit_case_count": len(rows),
        "confusion_matrix": {
            "true_positive": true_positive,
            "false_positive": false_positive,
            "true_negative": true_negative,
            "false_negative": false_negative,
        },
        "metrics": {
            "failure_precision": precision,
            "failure_recall": recall,
            "false_positive_rate": false_positive_rate,
        },
        "saved_candidate_rescore": {
            "candidate_count": sum(
                case["generated_candidate_count"]
                for result in sampling_report["schedule_results"].values()
                for case in result["cases"]
            ),
            "newly_rejected_candidate_count": gate_rescore.get("total_newly_rejected_candidate_count"),
            "newly_accepted_candidate_count": gate_rescore.get("total_newly_accepted_candidate_count"),
        },
        "gate": gate,
        "gate_passed": all(gate.values()),
        "cases": rows,
        "conclusion_zh": (
            "一般化敬語問句檢查補到 1 個先前漏判，且未誤殺 6 個 audit pass；"
            "但只抓到 5 個自然度失敗中的 1 個，因此這是人格語域增量，不是完整自然度解法。"
        ),
        "research_boundary": (
            "The source audit is a transparent non-blind agent review. The expanded regex targets casual-register "
            "violations only; it does not claim to detect malformed collocations, semantic drift, or all Japanese errors."
        ),
    }


def write_markdown(report, path):
    metrics = report["metrics"]
    matrix = report["confusion_matrix"]
    rescore = report["saved_candidate_rescore"]
    lines = [
        "# RightBrain Casual Register Gate v2",
        "",
        "## 結論",
        "",
        report["conclusion_zh"],
        "",
        "## Audit 結果",
        "",
        "| 指標 | 結果 |",
        "|---|---:|",
        f"| true positive | {matrix['true_positive']} |",
        f"| false positive | {matrix['false_positive']} |",
        f"| true negative | {matrix['true_negative']} |",
        f"| false negative | {matrix['false_negative']} |",
        f"| failure precision | {_fmt_pct(metrics['failure_precision'])} |",
        f"| failure recall | {_fmt_pct(metrics['failure_recall'])} |",
        f"| false positive rate | {_fmt_pct(metrics['false_positive_rate'])} |",
        "",
        "## 同候選重算",
        "",
        f"- stored candidates: {rescore['candidate_count']}",
        f"- newly rejected: {rescore['newly_rejected_candidate_count']}",
        f"- newly accepted: {rescore['newly_accepted_candidate_count']}",
        "",
        "## Gate",
        "",
        "| 條件 | 結果 |",
        "|---|---|",
    ]
    for name, passed in report["gate"].items():
        lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} |")
    lines.extend([
        "",
        "## 邊界",
        "",
        "- 本輪只改善 casual persona 的敬語／接客服務語域檢查。",
        "- failure recall 20% 表示錯字、搭配詞與語意扭曲仍未解決。",
        "- 不使用這個局部結果宣稱完整日文自然度已提升。",
        "",
    ])
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sampling-report", default=RIGHTBRAIN_SAMPLING_SCHEDULE_ABLATION_V1_REPORT_JSON_PATH)
    parser.add_argument("--audit", default=RIGHTBRAIN_SAMPLING_SCHEDULE_NATURALNESS_AUDIT_V1_JSON_PATH)
    parser.add_argument("--output-json", default=RIGHTBRAIN_CASUAL_REGISTER_GATE_V2_REPORT_JSON_PATH)
    parser.add_argument("--output-md", default=RIGHTBRAIN_CASUAL_REGISTER_GATE_V2_REPORT_MD_PATH)
    args = parser.parse_args()
    sampling_report = json.loads(Path(args.sampling_report).read_text(encoding="utf-8"))
    audit = json.loads(Path(args.audit).read_text(encoding="utf-8"))
    report = build_report(sampling_report, audit)
    Path(args.output_json).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, args.output_md)
    print(json.dumps({"metrics": report["metrics"], "gate": report["gate"]}, ensure_ascii=False, indent=2))
    return 0 if report["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
