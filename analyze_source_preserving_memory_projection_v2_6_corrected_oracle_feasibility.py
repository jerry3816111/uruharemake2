#!/usr/bin/env python3
"""Lock V2.6 corrected-oracle construction infeasibility without model calls."""

from __future__ import annotations

import json
from pathlib import Path

import build_source_preserving_memory_projection_v2_5_locomo_cases as v25
import build_source_preserving_memory_projection_v2_6_corrected_oracle_cases as v26


ROOT = Path(__file__).resolve().parent
REPORT_JSON = ROOT / "reports/source_preserving_memory_projection_v2_6_corrected_oracle_feasibility.json"
REPORT_MD = ROOT / "reports/source_preserving_memory_projection_v2_6_corrected_oracle_feasibility.md"
LOCK = ROOT / "configs/source_preserving_memory_projection_v2_6_corrected_oracle_feasibility_lock.json"


def summarize(data, prereg):
    by_id = {str(row["sample_id"]): row for row in data}
    counts = {}
    selected_indices = {}
    for sample_id in prereg["controlled_variables"]["exposed_sample_ids"]:
        eligible = v26.eligible_cases_for_sample(by_id[sample_id], prereg)
        counts[sample_id] = len(eligible)
        selected_indices[sample_id] = [row["qa_index"] for row in eligible]
    required_per = prereg["controlled_variables"]["cases_per_conversation"]
    required_total = prereg["controlled_variables"]["question_count"]
    actual_total = sum(counts.values())
    feasible = actual_total >= required_total and all(
        count >= required_per for count in counts.values()
    )
    return {
        "schema": "uruha_source_preserving_memory_projection_corrected_oracle_feasibility_v2_6",
        "experiment_id": prereg["experiment_id"],
        "decision": (
            "construction_feasible_build_once"
            if feasible
            else "construction_infeasible_do_not_build_cases"
        ),
        "evidence_scope": "exposed_locomo_development_construction_only",
        "metrics": {
            "required_question_count": required_total,
            "eligible_question_count": actual_total,
            "required_cases_per_conversation": required_per,
            "eligible_count_by_conversation": counts,
            "eligible_qa_indices_by_conversation": selected_indices,
            "case_manifest_written": v26.OUTPUT.exists(),
            "model_calls": 0,
            "reserve_sample_access_count": 0,
        },
        "gates": {
            "total_question_count_reachable": actual_total >= required_total,
            "per_conversation_allocation_reachable": all(
                count >= required_per for count in counts.values()
            ),
            "case_manifest_absent_after_failure": not v26.OUTPUT.exists(),
            "model_calls_equal_zero": True,
            "reserve_sample_access_count_equals_zero": True,
        },
        "root_cause": "The corrected turn-text-only oracle leaves ten eligible questions across the four exposed conversations. conv-48 has two and conv-30 has one, so the frozen requirement of three per conversation and twelve total is unreachable.",
        "authorization": {
            "build_v2_6_cases": feasible,
            "new_preregistration_changing_only_development_count_and_allocation": not feasible,
            "change_projection_algorithm": False,
            "model_generation": False,
            "use_reserve_conversations": False,
            "runtime_change": False,
            "runtime_shadow": False,
            "production_enablement": False,
        },
        "evidence_boundary": "This result tests corrected case-construction feasibility only. It does not evaluate the projection algorithm or any LLM.",
    }


def markdown(report):
    metrics = report["metrics"]
    return "\n".join(
        [
            "# V2.6 Corrected Oracle 建構可行性",
            "",
            f"**決策：`{report['decision']}`**",
            "",
            "修正後只在原始對話正文內確認答案。固定規格需要每段對話 3 題、合計 12 題，但實際只有 10 題符合。",
            "",
            "| 已暴露 development 對話 | 需要 | 實際可用 |",
            "|---|---:|---:|",
            *[
                f"| `{sample_id}` | {metrics['required_cases_per_conversation']} | {count} |"
                for sample_id, count in metrics["eligible_count_by_conversation"].items()
            ],
            f"| **合計** | **{metrics['required_question_count']}** | **{metrics['eligible_question_count']}** |",
            "",
            "因此沒有建立 case manifest，也沒有呼叫模型。直接從其他對話補題會違反預註冊分配，不能事後修改。",
            "",
            "下一版只可重新預註冊 development 題數與分配；Top-3 投影、模型與六段 reserve 都必須保持不動。",
            "",
        ]
    )


def main():
    if REPORT_JSON.exists() or REPORT_MD.exists() or LOCK.exists():
        raise SystemExit("V2.6 feasibility result already exists")
    prereg = v26.load_preregistration()
    data = v25.ensure_official_dataset(v25.load_preregistration())
    report = summarize(data, prereg)
    REPORT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    REPORT_MD.write_text(markdown(report), encoding="utf-8")
    lock = {
        "schema": "uruha_source_preserving_memory_projection_corrected_oracle_feasibility_lock_v2_6",
        "experiment_id": prereg["experiment_id"],
        "decision": report["decision"],
        "model_calls": 0,
        "artifacts": {
            path.relative_to(ROOT).as_posix(): v25.file_sha256(path)
            for path in (v26.PREREG, Path(v26.__file__), Path(__file__), REPORT_JSON, REPORT_MD)
        },
        "authorization": report["authorization"],
        "evidence_boundary": report["evidence_boundary"],
    }
    LOCK.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "decision": report["decision"],
                "eligible": report["metrics"]["eligible_question_count"],
                "required": report["metrics"]["required_question_count"],
                "model_calls": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
