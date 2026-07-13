#!/usr/bin/env python3
"""Audit the completed evidence-ledger held-out result without rerunning it."""

import datetime
import json
from collections import Counter, defaultdict
from pathlib import Path

import run_longmemeval_evidence_ledger_heldout as heldout_module
from memory_evidence_ledger import strict_answer_support
from project_paths import (
    LONGMEMEVAL_EVIDENCE_LEDGER_HELDOUT_ANALYSIS_JSON_PATH,
    LONGMEMEVAL_EVIDENCE_LEDGER_HELDOUT_ANALYSIS_MD_PATH,
    LONGMEMEVAL_EVIDENCE_LEDGER_HELDOUT_REPORT_JSON_PATH,
)
from run_longmemeval_evidence_ledger_development import CONDITIONS
from run_longmemeval_evidence_ledger_heldout import (
    EXPECTED_HELDOUT_COUNT,
    SCOPE as HELDOUT_SCOPE,
)
from run_longmemeval_retrieval_benchmark import (
    atomic_write_json,
    canonical_sha256,
    file_sha256,
)


SCOPE = "longmemeval_evidence_ledger_heldout_posthoc_analysis_v1"


def validate_report(report):
    if report.get("scope") != HELDOUT_SCOPE:
        raise ValueError("Held-out report scope differs")
    if report.get("complete") is not True or report.get("status") != "complete":
        raise ValueError("Held-out report is incomplete")
    results = report.get("results") or []
    if len(results) != EXPECTED_HELDOUT_COUNT:
        raise ValueError("Held-out report result count differs")
    if len({row.get("question_id") for row in results}) != EXPECTED_HELDOUT_COUNT:
        raise ValueError("Held-out report question IDs are not unique")
    if report.get("completed_question_count") != EXPECTED_HELDOUT_COUNT:
        raise ValueError("Held-out completed count differs")
    if report.get("results_sha256") != canonical_sha256(results):
        raise ValueError("Held-out result payload SHA differs")
    boundary = report.get("data_boundary") or {}
    if boundary.get("completed_question_count") != EXPECTED_HELDOUT_COUNT:
        raise ValueError("Held-out boundary completed count differs")
    if boundary.get("completed_question_ids_sha256") != canonical_sha256(
        [row["question_id"] for row in results]
    ):
        raise ValueError("Held-out completed question ID SHA differs")
    recorded_runner_sha = (
        report.get("frozen_evidence", {})
        .get("heldout_implementation_evidence", {})
        .get("heldout_runner_sha256")
    )
    if recorded_runner_sha != file_sha256(Path(heldout_module.__file__).resolve()):
        raise ValueError("Frozen held-out runner SHA differs")
    if any(set(row.get("conditions") or {}) != set(CONDITIONS) for row in results):
        raise ValueError("Held-out result condition set differs")
    if boundary.get("candidate_cache_contains_gold_answers"):
        raise ValueError("Held-out candidate cache contains gold answers")
    if report.get("decision", {}).get("authorize_runtime_change") is not False:
        raise ValueError("Held-out report unexpectedly authorized runtime change")
    return results


def condition_value(condition, metric):
    if metric == "strict_answer_support":
        return bool(condition.get(metric))
    if metric == "local_judge":
        return bool((condition.get("local_judge") or {}).get("label"))
    raise ValueError(f"Unsupported metric: {metric}")


def evidence_text_from_notes(condition):
    return "\n".join(
        str(value)
        for note in condition.get("notes") or []
        for fact in ((note.get("evidence") or {}).get("facts") or [])
        for value in (fact.get("quote"), fact.get("claim"), fact.get("value"))
        if value is not None
    )


def evidence_text_from_ledger(condition):
    return "\n".join(
        str(value)
        for event in ((condition.get("ledger") or {}).get("events") or [])
        for value in (
            event.get("source_quote"),
            event.get("claim"),
            event.get("value"),
        )
        if value is not None
    )


def strict_failure_layer(row):
    condition = row["conditions"]["versioned_ledger"]
    if condition_value(condition, "strict_answer_support"):
        return None
    note_support = strict_answer_support(
        row["answer"],
        evidence_text_from_notes(condition),
        question=row["question"],
    )
    ledger_support = strict_answer_support(
        row["answer"],
        evidence_text_from_ledger(condition),
        question=row["question"],
    )
    if not row.get("all_gold_sessions_retrieved"):
        layer = "retrieval_missing_gold_session"
    elif not note_support:
        layer = "note_extraction_missing_gold_support"
    elif not ledger_support:
        layer = "ledger_integration_missing_gold_support"
    else:
        layer = "answer_realization_missing_gold_support"
    return {
        "layer": layer,
        "note_strict_support": note_support,
        "ledger_strict_support": ledger_support,
    }


def scorer_confusion(results, condition):
    counts = Counter()
    disagreements = []
    for row in results:
        output = row["conditions"][condition]
        strict = condition_value(output, "strict_answer_support")
        judged = condition_value(output, "local_judge")
        key = f"strict_{int(strict)}_judge_{int(judged)}"
        counts[key] += 1
        if strict != judged:
            disagreements.append(
                {
                    "question_id": row["question_id"],
                    "strict": strict,
                    "local_judge": judged,
                    "question": row["question"],
                    "gold": row["answer"],
                    "response": output["response"],
                }
            )
    return {"counts": dict(sorted(counts.items())), "disagreements": disagreements}


def operation_summary(results):
    groups = defaultdict(list)
    for row in results:
        frame = row["conditions"]["versioned_ledger"].get("question_frame") or {}
        groups[str(frame.get("operation") or "missing")].append(row)
    output = {}
    for operation, rows in sorted(groups.items()):
        rates = {}
        for condition in CONDITIONS:
            rates[condition] = sum(
                condition_value(row["conditions"][condition], "strict_answer_support")
                for row in rows
            ) / len(rows)
        wins = sum(
            not condition_value(
                row["conditions"]["direct_chronological"],
                "strict_answer_support",
            )
            and condition_value(
                row["conditions"]["versioned_ledger"],
                "strict_answer_support",
            )
            for row in rows
        )
        losses = sum(
            condition_value(
                row["conditions"]["direct_chronological"],
                "strict_answer_support",
            )
            and not condition_value(
                row["conditions"]["versioned_ledger"],
                "strict_answer_support",
            )
            for row in rows
        )
        output[operation] = {
            "case_count": len(rows),
            "strict_rates": rates,
            "ledger_wins": wins,
            "ledger_losses": losses,
        }
    return output


def discordant_cases(results):
    cases = []
    for row in results:
        direct = row["conditions"]["direct_chronological"]
        ledger = row["conditions"]["versioned_ledger"]
        direct_value = condition_value(direct, "strict_answer_support")
        ledger_value = condition_value(ledger, "strict_answer_support")
        if direct_value == ledger_value:
            continue
        cases.append(
            {
                "question_id": row["question_id"],
                "direction": "ledger_win" if ledger_value else "ledger_loss",
                "question": row["question"],
                "gold": row["answer"],
                "direct_response": direct["response"],
                "grounded_notes_response": row["conditions"]["grounded_notes"][
                    "response"
                ],
                "ledger_response": ledger["response"],
                "all_gold_sessions_retrieved": row["all_gold_sessions_retrieved"],
                "question_frame": ledger.get("question_frame"),
            }
        )
    return cases


def build_analysis(report):
    results = validate_report(report)
    failures = []
    for row in results:
        failure = strict_failure_layer(row)
        if failure is not None:
            failures.append(
                {
                    "question_id": row["question_id"],
                    "question": row["question"],
                    "gold": row["answer"],
                    "ledger_response": row["conditions"]["versioned_ledger"][
                        "response"
                    ],
                    **failure,
                }
            )
    layer_counts = Counter(row["layer"] for row in failures)
    return {
        "scope": SCOPE,
        "generated_at": datetime.datetime.now().astimezone().isoformat(
            timespec="seconds"
        ),
        "source_report_sha256": file_sha256(
            LONGMEMEVAL_EVIDENCE_LEDGER_HELDOUT_REPORT_JSON_PATH
        ),
        "source_results_sha256": report["results_sha256"],
        "integrity": {
            "complete": True,
            "result_count": len(results),
            "unique_question_id_count": len(
                {row["question_id"] for row in results}
            ),
            "condition_set_complete": True,
            "candidate_cache_contains_gold_answers": False,
        },
        "primary_result": {
            "direct_strict_rate": report["summaries"]["direct_chronological"][
                "strict_answer_support_rate"
            ],
            "ledger_strict_rate": report["summaries"]["versioned_ledger"][
                "strict_answer_support_rate"
            ],
            "paired": report["paired_comparisons"]["ledger_vs_direct_strict"],
            "supports_hypothesis": report["decision"][
                "supports_evidence_ledger_hypothesis"
            ],
        },
        "strict_failure_layer_counts": dict(sorted(layer_counts.items())),
        "strict_failure_layer_cases": failures,
        "operation_summary": operation_summary(results),
        "scorer_confusion": {
            condition: scorer_confusion(results, condition)
            for condition in CONDITIONS
        },
        "discordant_cases": discordant_cases(results),
        "provenance_diagnostics": {
            "raw_extracted_fact_count": report["summaries"]["versioned_ledger"][
                "extracted_fact_count"
            ],
            "accepted_grounded_fact_count": report["summaries"][
                "versioned_ledger"
            ]["accepted_grounded_fact_count"],
            "rejected_ungrounded_fact_count": report["summaries"][
                "versioned_ledger"
            ]["rejected_ungrounded_fact_count"],
            "ledger_grounding_rate": report["summaries"]["versioned_ledger"][
                "ledger_grounding_rate"
            ],
            "preregistered_structural_integrity_gate": report["decision"][
                "structural_integrity"
            ],
        },
        "decision": {
            "authorize_runtime_change": False,
            "authorize_reuse_of_this_heldout_for_tuning": False,
            "next_development_hypotheses": [
                "utterance-level attention inside each retrieved session",
                "typed answer realization contract for count, location, time, and yes/no",
                "pre-registered scorer calibration before any new held-out observation",
            ],
            "decision_zh": (
                "Ledger 在一次性 held-out 沒有勝過 direct；不得上正式 runtime，"
                "也不得使用這 54 題調參後重新宣稱泛化。下一輪只能在新的 "
                "development cases 驗證 session 內注意力與 typed answer contract。"
            ),
        },
        "interpretation_boundary": (
            "Failure layers are post-hoc lexical diagnostics based on the frozen strict "
            "scorer. They localize observable pipeline boundaries but are not causal proof. "
            "The strict scorer and local Qwen judge both have observed disagreement cases."
        ),
    }


def write_markdown(analysis, path):
    primary = analysis["primary_result"]
    paired = primary["paired"]
    lines = [
        "# LongMemEval Evidence Ledger Held-out 事後審計",
        "",
        "## 結論",
        "",
        (
            f"- Direct 嚴格支持率：{100 * primary['direct_strict_rate']:.2f}%"
        ),
        (
            f"- Ledger 嚴格支持率：{100 * primary['ledger_strict_rate']:.2f}%"
        ),
        (
            f"- 配對結果：修正 {paired['treatment_wins']} 題、弄錯 "
            f"{paired['treatment_losses']} 題、淨增 "
            f"{paired['net_treatment_wins']:+d} 題、McNemar "
            f"p={paired['exact_mcnemar_two_sided_p']:.4f}。"
        ),
        "- 結論：未支持 ledger 優於 direct；正式 runtime 不修改。",
        "",
        "## 17 個 Ledger 嚴格失敗的層級診斷",
        "",
        "| 可觀察邊界 | 題數 |",
        "|---|---:|",
    ]
    labels = {
        "retrieval_missing_gold_session": "Top-5 未取回全部 gold session",
        "note_extraction_missing_gold_support": "Notes 未保留 gold 支持值",
        "ledger_integration_missing_gold_support": "Ledger 未保留 notes 支持值",
        "answer_realization_missing_gold_support": "Ledger 有支持值但回答未說出",
    }
    for key, label in labels.items():
        lines.append(
            f"| {label} | {analysis['strict_failure_layer_counts'].get(key, 0)} |"
        )
    lines.extend(
        [
            "",
            "此分層使用凍結 strict scorer，只能定位可觀察邊界，不能當作因果證明。",
            "",
            "## 操作分組",
            "",
            "| 操作 | 題數 | Direct | Notes | Ledger | Ledger 修正/弄錯 |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for operation, values in analysis["operation_summary"].items():
        rates = values["strict_rates"]
        lines.append(
            f"| {operation} | {values['case_count']} | "
            f"{100 * rates['direct_chronological']:.1f}% | "
            f"{100 * rates['grounded_notes']:.1f}% | "
            f"{100 * rates['versioned_ledger']:.1f}% | "
            f"{values['ledger_wins']}/{values['ledger_losses']} |"
        )
    provenance = analysis["provenance_diagnostics"]
    lines.extend(
        [
            "",
            "## 來源完整性",
            "",
            (
                f"- 模型抽出 {provenance['raw_extracted_fact_count']} facts；"
                f"接受 {provenance['accepted_grounded_fact_count']}，拒絕 "
                f"{provenance['rejected_ungrounded_fact_count']} 個未逐字落地 fact。"
            ),
            (
                f"- 實際進入 ledger 的事件來源驗證率："
                f"{100 * provenance['ledger_grounding_rate']:.1f}%。"
            ),
            "- 但預先設定的原始抽取全通過 gate 仍失敗，不能事後改門檻翻案。",
            "",
            "## 評分邊界",
            "",
            "- Strict scorer 對同義格式可能 false negative。",
            "- 本機 Qwen judge 對矛盾推論可能 false positive。",
            "- 兩者均未提供 ledger 優於 direct 的可靠證據。",
            "",
            "## 下一輪",
            "",
            "1. 在新的 development cases 做 session 內 utterance-level attention。",
            "2. 加入 count/location/time/yes-no typed answer contract。",
            "3. 新 held-out 前先凍結並校準 scorer；這 54 題不得再作調參後泛化證據。",
            "",
            analysis["decision"]["decision_zh"],
            "",
        ]
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    report = json.loads(
        Path(LONGMEMEVAL_EVIDENCE_LEDGER_HELDOUT_REPORT_JSON_PATH).read_text(
            encoding="utf-8"
        )
    )
    analysis = build_analysis(report)
    atomic_write_json(
        LONGMEMEVAL_EVIDENCE_LEDGER_HELDOUT_ANALYSIS_JSON_PATH,
        analysis,
    )
    write_markdown(
        analysis,
        LONGMEMEVAL_EVIDENCE_LEDGER_HELDOUT_ANALYSIS_MD_PATH,
    )
    print(
        json.dumps(
            {
                "primary_result": analysis["primary_result"],
                "strict_failure_layer_counts": analysis[
                    "strict_failure_layer_counts"
                ],
                "decision": analysis["decision"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
