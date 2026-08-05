#!/usr/bin/env python3
"""Diagnose the locked semantic recall-support holdout failure."""

from __future__ import annotations

import json
from pathlib import Path

import uruha_memory_runtime as umr
from run_semantic_memory_recall_support_v1_holdout import memory_item, wrapped_query


ROOT = Path(__file__).resolve().parent
CASES = ROOT / "configs/semantic_memory_recall_support_v1_holdout_cases.json"
CONTRACT = ROOT / "configs/semantic_memory_recall_support_v1_holdout_evaluation_contract.json"
RESULT = ROOT / "reports/semantic_memory_recall_support_v1_holdout.json"
OUTPUT_JSON = ROOT / "reports/semantic_memory_recall_support_v1_holdout_diagnosis.json"
OUTPUT_MD = ROOT / "reports/semantic_memory_recall_support_v1_holdout_diagnosis.md"


def diagnose(cases_payload, contract, result):
    rows = []
    for case in cases_payload["cases"]:
        query = wrapped_query(case, contract)
        support = {
            name: umr.memory_query_support(query, case[name]["text"])
            for name in ("target", "replacement", "hard_negative")
        }
        target_decision = umr.select_high_confidence_recall_item(
            query,
            {"working_memory_items": [memory_item(case["target"])]},
        )
        rows.append(
            {
                "case_id": case["case_id"],
                "language": case["language"],
                "target_shared_count": support["target"]["shared_focus_unit_count"],
                "replacement_shared_count": support["replacement"][
                    "shared_focus_unit_count"
                ],
                "hard_negative_shared_count": support["hard_negative"][
                    "shared_focus_unit_count"
                ],
                "target_only_status": target_decision.get("status"),
                "target_only_suppression_reason": (
                    target_decision.get("speakability") or {}
                ).get("reason"),
            }
        )
    target_counts = [row["target_shared_count"] for row in rows]
    negative_counts = [row["hard_negative_shared_count"] for row in rows]
    diagnosis = {
        "schema": "uruha_semantic_memory_recall_support_holdout_diagnosis_v1",
        "holdout_decision": result["decision"],
        "observed": {
            "question_count": len(rows),
            "wrong_trace_selection_count": result["wrong_trace_selection_count"],
            "target_removed_selection_count": result["target_removed_selection_count"],
            "target_lexically_supported_count": sum(value > 0 for value in target_counts),
            "replacement_lexically_supported_count": sum(
                row["replacement_shared_count"] > 0 for row in rows
            ),
            "hard_negative_lexically_supported_count": sum(
                value > 0 for value in negative_counts
            ),
            "target_shared_count_range": [min(target_counts), max(target_counts)],
            "hard_negative_shared_count_range": [
                min(negative_counts),
                max(negative_counts),
            ],
            "target_lexical_miss_count": sum(value == 0 for value in target_counts),
            "replacement_paraphrase_support_loss_count": sum(
                row["target_shared_count"] > 0
                and row["replacement_shared_count"] == 0
                for row in rows
            ),
            "whole_record_sensitive_suppression_count": sum(
                row["target_only_status"] == "suppressed"
                and row["target_only_suppression_reason"] == "sensitive_memory"
                for row in rows
            ),
        },
        "root_causes": [
            {
                "id": "topic_overlap_is_not_answer_support",
                "evidence": "Six of eight target-removed hard negatives shared at least one focus unit and were selected.",
            },
            {
                "id": "lexical_support_is_not_paraphrase_invariant",
                "evidence": "Only three of eight faithful replacement paraphrases retained lexical support.",
            },
            {
                "id": "record_level_sensitivity_is_too_coarse",
                "evidence": "One supported target was suppressed because another excerpt in the same memory record triggered the sensitive-memory gate.",
            },
        ],
        "threshold_conclusion": {
            "shared_count_threshold_can_separate_targets_and_negatives": False,
            "reason": "Both target and hard-negative shared-count ranges are 0 to 4; raising the threshold removes valid targets while retaining some hard negatives.",
        },
        "next_falsifiable_hypothesis": "A bypass must require a question-conditioned answer-bearing evidence span, not topic overlap. Span-level speakability must inspect only the proposed evidence span.",
        "forbidden_next_step": "Do not tune token stoplists, shared-unit thresholds, or case-specific terms against this exposed holdout.",
        "rows": rows,
    }
    return diagnosis


def markdown(payload):
    observed = payload["observed"]
    return "\n".join(
        [
            "# Semantic recall support V1 holdout diagnosis",
            "",
            f"- Decision: `{payload['holdout_decision']}`",
            f"- Wrong trace selections: {observed['wrong_trace_selection_count']}",
            f"- Target-removed selections: {observed['target_removed_selection_count']}/8",
            f"- Lexically supported target / replacement / hard negative: {observed['target_lexically_supported_count']}/8 / {observed['replacement_lexically_supported_count']}/8 / {observed['hard_negative_lexically_supported_count']}/8",
            f"- Target and hard-negative shared-unit ranges: {observed['target_shared_count_range']} / {observed['hard_negative_shared_count_range']}",
            f"- Whole-record sensitive suppressions: {observed['whole_record_sensitive_suppression_count']}",
            "",
            "## Conclusion",
            "",
            payload["threshold_conclusion"]["reason"],
            "",
            payload["next_falsifiable_hypothesis"],
            "",
            f"Forbidden: {payload['forbidden_next_step']}",
        ]
    ) + "\n"


def main():
    payload = diagnose(
        json.loads(CASES.read_text(encoding="utf-8")),
        json.loads(CONTRACT.read_text(encoding="utf-8")),
        json.loads(RESULT.read_text(encoding="utf-8")),
    )
    OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    OUTPUT_MD.write_text(markdown(payload), encoding="utf-8")
    print(json.dumps(payload["observed"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
