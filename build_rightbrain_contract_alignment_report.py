#!/usr/bin/env python3
"""Compare isolated RightBrain model-gate runs before and after contract alignment."""

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from project_paths import (
    RIGHTBRAIN_CONTRACT_ALIGNMENT_REPORT_JSON_PATH,
    RIGHTBRAIN_CONTRACT_ALIGNMENT_REPORT_MD_PATH,
)


TZ = ZoneInfo("Asia/Tokyo")
RAW_ACCEPTANCE_TARGET = 0.60
MODEL_SELECTION_TARGET = 0.20
FINAL_CONTRACT_TARGET = 0.99


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_specs(specs):
    reports = {}
    for spec in specs:
        if "=" not in spec:
            raise ValueError(f"Expected LABEL=PATH, got: {spec}")
        label, path = spec.split("=", 1)
        label = label.strip()
        source = Path(path).expanduser()
        if not label or not source.is_file():
            raise ValueError(f"Invalid report spec: {spec}")
        if label in reports:
            raise ValueError(f"Duplicate report label: {label}")
        payload = json.loads(source.read_text(encoding="utf-8"))
        reports[label] = {
            "path": source,
            "sha256": _sha256(source),
            "payload": payload,
        }
    return reports


def _metric_row(label, source):
    report = source["payload"]
    summary = report.get("summary") or {}
    return {
        "label": label,
        "adapter_ref": report.get("adapter_ref"),
        "runtime_contract_version": report.get("runtime_contract_version") or "legacy_runtime_payload",
        "dataset_sha256": report.get("dataset_sha256"),
        "seed": report.get("seed"),
        "case_state_reset": report.get("case_state_reset"),
        "candidate_count_per_enabled_case": report.get("candidate_count_per_enabled_case"),
        "generated_candidate_count": summary.get("generated_candidate_count"),
        "raw_candidate_acceptance_rate": summary.get("raw_candidate_acceptance_rate"),
        "model_selected_case_rate": summary.get("model_selected_case_rate"),
        "final_contract_pass_rate": summary.get("final_contract_pass_rate"),
        "final_language_clean_rate": summary.get("final_language_clean_rate"),
        "fallback_protection_rate": summary.get("fallback_protection_rate"),
        "rejection_reason_counts": summary.get("rejection_reason_counts") or {},
        "source_report_ref": source["path"].name,
        "source_report_sha256": source["sha256"],
    }


def _validate_matched(rows):
    fields = (
        "dataset_sha256",
        "seed",
        "case_state_reset",
        "candidate_count_per_enabled_case",
        "generated_candidate_count",
    )
    mismatches = {}
    for field in fields:
        values = {json.dumps(row.get(field), sort_keys=True) for row in rows}
        if len(values) != 1:
            mismatches[field] = sorted(values)
    if mismatches:
        raise ValueError(f"Reports are not matched trials: {mismatches}")


def build_report(before_sources, after_sources):
    if set(before_sources) != set(after_sources):
        raise ValueError("Before/after labels must match exactly")
    labels = sorted(before_sources)
    before_rows = [_metric_row(label, before_sources[label]) for label in labels]
    after_rows = [_metric_row(label, after_sources[label]) for label in labels]
    _validate_matched(before_rows + after_rows)

    before_by_label = {row["label"]: row for row in before_rows}
    after_by_label = {row["label"]: row for row in after_rows}
    comparisons = []
    for label in labels:
        before = before_by_label[label]
        after = after_by_label[label]
        comparisons.append(
            {
                "label": label,
                "adapter_ref": after["adapter_ref"],
                "raw_acceptance_before": before["raw_candidate_acceptance_rate"],
                "raw_acceptance_after": after["raw_candidate_acceptance_rate"],
                "raw_acceptance_delta": round(
                    after["raw_candidate_acceptance_rate"] - before["raw_candidate_acceptance_rate"], 4
                ),
                "model_selection_before": before["model_selected_case_rate"],
                "model_selection_after": after["model_selected_case_rate"],
                "model_selection_delta": round(
                    after["model_selected_case_rate"] - before["model_selected_case_rate"], 4
                ),
                "final_contract_after": after["final_contract_pass_rate"],
                "final_language_clean_after": after["final_language_clean_rate"],
            }
        )

    best = max(
        after_rows,
        key=lambda row: (
            row["raw_candidate_acceptance_rate"],
            row["model_selected_case_rate"],
            row["final_contract_pass_rate"],
        ),
    )
    qualified = [
        row
        for row in after_rows
        if row["raw_candidate_acceptance_rate"] >= RAW_ACCEPTANCE_TARGET
        and row["model_selected_case_rate"] >= MODEL_SELECTION_TARGET
        and row["final_contract_pass_rate"] >= FINAL_CONTRACT_TARGET
    ]
    return {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "matched_rightbrain_runtime_contract_alignment_development_comparison",
        "research_boundary": (
            "This is a small developer-visible set with six model-enabled cases and eighteen candidates per adapter. "
            "It supports debugging and adapter selection hypotheses, not human-naturalness or benchmark claims."
        ),
        "controlled_variables": {
            "dataset_sha256": after_rows[0]["dataset_sha256"],
            "seed": after_rows[0]["seed"],
            "case_state_reset": after_rows[0]["case_state_reset"],
            "candidate_count_per_enabled_case": after_rows[0]["candidate_count_per_enabled_case"],
            "generated_candidate_count_per_adapter": after_rows[0]["generated_candidate_count"],
            "gate_policy": "unchanged_strict_model_candidate_gate",
        },
        "targets": {
            "raw_candidate_acceptance_rate": RAW_ACCEPTANCE_TARGET,
            "model_selected_case_rate": MODEL_SELECTION_TARGET,
            "final_contract_pass_rate": FINAL_CONTRACT_TARGET,
        },
        "before": before_rows,
        "after": after_rows,
        "comparisons": comparisons,
        "best_observed_after": {
            "label": best["label"],
            "adapter_ref": best["adapter_ref"],
            "raw_candidate_acceptance_rate": best["raw_candidate_acceptance_rate"],
            "model_selected_case_rate": best["model_selected_case_rate"],
        },
        "qualified_default_adapters": [row["label"] for row in qualified],
        "default_adapter_change_recommended": bool(qualified),
        "conclusion_zh": (
            "canonical speech-plan 契約能改善部分模型的語意合格率，但目前沒有 adapter 同時達到 raw 合格率、實際接管率與最終安全門檻；"
            "因此不應只因小型開發集排名就切換預設模型，下一步必須用完全相同的 v1 契約重新訓練並在未見 holdout 驗證。"
        ),
    }


def _format_pct(value):
    return f"{100 * value:.2f}%"


def write_markdown(report, path):
    lines = [
        "# 右腦 Runtime 契約對齊比較",
        "",
        "> 這是小型開發集診斷，不是自然度盲測，也不是正式 benchmark。",
        "",
        "## 控制條件",
        "",
        f"- 每個 adapter 生成候選數：{report['controlled_variables']['generated_candidate_count_per_adapter']}",
        f"- seed：{report['controlled_variables']['seed']}",
        f"- 每題重置狀態：{report['controlled_variables']['case_state_reset']}",
        "- gate：前後完全相同，只替換 runtime payload 契約",
        "",
        "## 前後結果",
        "",
        "| Adapter | raw 合格率（前） | raw 合格率（後） | 差值 | 接管率（前） | 接管率（後） | 最終契約（後） |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["comparisons"]:
        lines.append(
            "| {label} | {raw_before} | {raw_after} | {delta:+.2f} pp | {sel_before} | {sel_after} | {final} |".format(
                label=row["label"],
                raw_before=_format_pct(row["raw_acceptance_before"]),
                raw_after=_format_pct(row["raw_acceptance_after"]),
                delta=100 * row["raw_acceptance_delta"],
                sel_before=_format_pct(row["model_selection_before"]),
                sel_after=_format_pct(row["model_selection_after"]),
                final=_format_pct(row["final_contract_after"]),
            )
        )
    lines.extend(
        [
            "",
            "## 判定",
            "",
            f"- 開發集最佳 raw adapter：{report['best_observed_after']['label']} "
            f"({_format_pct(report['best_observed_after']['raw_candidate_acceptance_rate'])})",
            f"- 達到預設切換門檻：{report['qualified_default_adapters'] or '無'}",
            f"- 是否建議切換預設 adapter：{report['default_adapter_change_recommended']}",
            "",
            report["conclusion_zh"],
            "",
        ]
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", action="append", required=True, help="LABEL=report.json")
    parser.add_argument("--after", action="append", required=True, help="LABEL=report.json")
    parser.add_argument("--output-json", default=RIGHTBRAIN_CONTRACT_ALIGNMENT_REPORT_JSON_PATH)
    parser.add_argument("--output-md", default=RIGHTBRAIN_CONTRACT_ALIGNMENT_REPORT_MD_PATH)
    args = parser.parse_args()

    report = build_report(_parse_specs(args.before), _parse_specs(args.after))
    Path(args.output_json).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, args.output_md)
    print(json.dumps(report["comparisons"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
