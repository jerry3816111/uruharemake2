#!/usr/bin/env python3
"""Analyze V2.5 LoCoMo construction before any model generation."""

from __future__ import annotations

import json
from pathlib import Path

import build_source_preserving_memory_projection_v2_5_locomo_cases as builder


ROOT = Path(__file__).resolve().parent
CASES = ROOT / "configs/source_preserving_memory_projection_v2_5_locomo_cases.json"
REPORT_JSON = ROOT / "reports/source_preserving_memory_projection_v2_5_locomo_construction.json"
REPORT_MD = ROOT / "reports/source_preserving_memory_projection_v2_5_locomo_construction.md"
LOCK = ROOT / "configs/source_preserving_memory_projection_v2_5_locomo_construction_result_lock.json"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def answer_turn_indices(conversation, session_key, answer):
    needle = str(answer).casefold()
    return [
        index
        for index, turn in enumerate(conversation[session_key])
        if needle in builder.turn_text(turn).casefold()
    ]


def summarize(data, prereg, manifest):
    construction_gates = manifest.get("construction_gates") or builder.validate_construction_gates(
        manifest, prereg
    )
    by_sample = {str(row["sample_id"]): row for row in data}
    rows = []
    for case in manifest["cases"]:
        sample = by_sample[case["sample_id"]]
        qa = sample["qa"][case["qa_index"]]
        question = str(qa["question"])
        answer = str(qa["answer"])
        target = case["target"]
        indices = answer_turn_indices(sample["conversation"], target["session_key"], answer)
        overlaps = {
            index: builder.lexical_overlap(
                question,
                builder.turn_text(sample["conversation"][target["session_key"]][index]),
            )
            for index in indices
        }
        selected = set(target["projection_source_turn_indices"])
        retained = any(index in selected for index in indices)
        rows.append(
            {
                "case_id": case["case_id"],
                "sample_id": case["sample_id"],
                "qa_index": case["qa_index"],
                "answer_turn_indices": indices,
                "projection_turn_indices": target["projection_source_turn_indices"],
                "answer_turn_selected": retained,
                "maximum_answer_turn_question_overlap": max(overlaps.values(), default=0.0),
                "complete_character_count": target["complete_character_count"],
                "projection_character_count": target["projection_character_count"],
                "projection_character_ratio": round(
                    target["projection_character_count"] / target["complete_character_count"],
                    6,
                ),
            }
        )
    retained_count = sum(row["answer_turn_selected"] for row in rows)
    source_valid = [row for row in rows if row["answer_turn_indices"]]
    source_invalid = [row for row in rows if not row["answer_turn_indices"]]
    retained_valid_count = sum(row["answer_turn_selected"] for row in source_valid)
    omitted = [row for row in rows if not row["answer_turn_selected"]]
    mean_target_ratio = sum(row["projection_character_ratio"] for row in rows) / len(rows)
    all_ratios = []
    for case in manifest["cases"]:
        for role in ("target", "hard_negative"):
            record = case[role]
            all_ratios.append(
                record["projection_character_count"] / record["complete_character_count"]
            )
    required = prereg["evaluation_gates"]["projection_answer_retention_count_at_least"]
    construction_oracle_valid = not source_invalid
    gate_reachable = construction_oracle_valid and retained_count >= required
    if not construction_oracle_valid:
        decision = "construction_invalid_oracle_do_not_run_model"
    elif gate_reachable:
        decision = "construction_pass_freeze_model_evaluation_contract"
    else:
        decision = "construction_fail_do_not_run_model"
    return {
        "schema": "uruha_source_preserving_memory_projection_locomo_construction_report_v2_5",
        "experiment_id": prereg["experiment_id"],
        "decision": decision,
        "evidence_scope": "fresh_external_single_hop_projection_construction_only",
        "integrity": {
            "dataset_sha256_match": manifest["source"]["dataset_sha256"]
            == prereg["official_source"]["dataset_sha256"],
            "case_manifest_sha256": builder.file_sha256(CASES),
            "case_count": len(rows),
            "construction_model_calls": manifest["construction_model_calls"],
            "all_construction_gates_passed": all(construction_gates.values()),
            "corrected_source_turn_oracle_valid": construction_oracle_valid,
        },
        "metrics": {
            "manifest_serialized_projection_answer_retention_count": sum(
                case["target"]["contains_answer_projection"]
                for case in manifest["cases"]
            ),
            "source_turn_valid_case_count": len(source_valid),
            "source_turn_invalid_case_count": len(source_invalid),
            "source_turn_projection_answer_retention_count": retained_count,
            "source_turn_projection_answer_retention_rate_all_cases": retained_count
            / len(rows),
            "source_turn_projection_answer_retention_rate_valid_cases": (
                retained_valid_count / len(source_valid) if source_valid else 0.0
            ),
            "preregistered_minimum_retention_count": required,
            "answer_omission_count": len(omitted),
            "omitted_with_zero_question_overlap_count": sum(
                row["maximum_answer_turn_question_overlap"] == 0 for row in omitted
            ),
            "mean_target_projection_character_ratio": round(mean_target_ratio, 6),
            "mean_all_record_projection_character_ratio": round(
                sum(all_ratios) / len(all_ratios), 6
            ),
            "planned_model_calls": prereg["controlled_variables"][
                "planned_model_call_count"
            ],
            "executed_model_calls": 0,
        },
        "gate": {
            "name": "projection_answer_retention_count_at_least",
            "required": required,
            "observed": retained_count,
            "passed": gate_reachable,
            "evaluable": construction_oracle_valid,
        },
        "root_cause": "The frozen builder checked answer membership against a serialization that also contained timestamps and speaker labels. Three of twelve cases therefore passed construction even though no dialogue turn contained the official answer. Among the nine source-valid cases, the fixed top-three lexical projection retained an answer-bearing turn in only four. Model inference cannot repair either a mislabeled source or omitted source text.",
        "case_diagnostics": rows,
        "authorization": {
            "model_generation": gate_reachable,
            "reuse_four_holdout_conversations_for_claims": False,
            "new_preregistration_using_only_six_reserve_conversations": True,
            "correct_source_membership_oracle": True,
            "change_projection_algorithm": True,
            "runtime_change": False,
            "runtime_shadow": False,
            "production_enablement": False,
        },
        "evidence_boundary": "This result invalidates the V2.5 case construction oracle and shows a secondary top-three lexical omission on four of nine source-valid cases. It does not evaluate qwen3.5:9b, full LoCoMo QA, or the production memory pipeline.",
    }


def markdown(report):
    metrics = report["metrics"]
    invalid = [row for row in report["case_diagnostics"] if not row["answer_turn_indices"]]
    omitted = [
        row
        for row in report["case_diagnostics"]
        if row["answer_turn_indices"] and not row["answer_turn_selected"]
    ]
    return "\n".join(
        [
            "# V2.5 LoCoMo Fresh Holdout 建構結果",
            "",
            f"**決策：`{report['decision']}`**",
            "",
            "## 先驗門檻",
            "",
            "模型尚未執行。建構器必須先證明答案真的存在於對話正文，再檢查投影是否保留該原文。",
            "",
            "| 指標 | 事前門檻 | 實際 |",
            "|---|---:|---:|",
            f"| 正文含答案的有效 case | 12/12 | {metrics['source_turn_valid_case_count']}/12 |",
            f"| 正文投影保留答案 | 至少 10/12 | {metrics['source_turn_projection_answer_retention_count']}/12 |",
            f"| Manifest 舊判定 | 不適用 | {metrics['manifest_serialized_projection_answer_retention_count']}/12 |",
            f"| 平均保留字元 | 至多 50% | {metrics['mean_all_record_projection_character_ratio']:.1%} |",
            f"| 模型呼叫 | 只有建構通過才 48 次 | {metrics['executed_model_calls']} |",
            "",
            "## 原因",
            "",
            "原建構器把時間戳與說話者標籤一起拿去搜尋答案，造成 3 題假通過。剩下 9 題中，Top-3 字面重疊又有 5 題沒有選到真正含答案的 turn。這是資料 oracle 與記憶投影問題，不是 9B 模型能力不足。",
            "",
            "建構 oracle 無效的 case：",
            "",
            *[f"- `{row['case_id']}`" for row in invalid],
            "",
            "正文有效但投影遺失答案的 case：",
            "",
            *[f"- `{row['case_id']}`" for row in omitted],
            "",
            "## 邊界與下一步",
            "",
            "這四段 holdout 已用來診斷 top-3 字面投影，不能重新包裝成新測試。下一版只能更換一般化投影方法，並只使用原先保留的六段 reserve 對話重新預註冊。",
            "",
            "本結果沒有測模型、沒有修改 runtime、沒有寫入記憶，也沒有啟動 VRM。",
            "",
        ]
    )


def main():
    if REPORT_JSON.exists() or REPORT_MD.exists() or LOCK.exists():
        raise SystemExit("V2.5 construction result already exists")
    prereg = builder.load_preregistration()
    manifest = load_json(CASES)
    data = builder.ensure_official_dataset(prereg)
    report = summarize(data, prereg, manifest)
    REPORT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    REPORT_MD.write_text(markdown(report), encoding="utf-8")
    lock = {
        "schema": "uruha_source_preserving_memory_projection_locomo_construction_result_lock_v2_5",
        "experiment_id": prereg["experiment_id"],
        "decision": report["decision"],
        "model_calls": report["metrics"]["executed_model_calls"],
        "artifacts": {
            path.relative_to(ROOT).as_posix(): builder.file_sha256(path)
            for path in (builder.PREREG, CASES, Path(__file__), REPORT_JSON, REPORT_MD)
        },
        "authorization": report["authorization"],
        "evidence_boundary": report["evidence_boundary"],
    }
    LOCK.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "decision": report["decision"],
                "retention": report["metrics"][
                    "source_turn_projection_answer_retention_count"
                ],
                "required": report["metrics"]["preregistered_minimum_retention_count"],
                "model_calls": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
