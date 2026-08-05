#!/usr/bin/env python3
"""Evaluate two-anchor adjacency projection on the frozen V2.6.1 cases."""

from __future__ import annotations

import json
import time
from pathlib import Path

import build_source_preserving_memory_projection_v2_5_locomo_cases as v25
import build_source_preserving_memory_projection_v2_6_corrected_oracle_cases as v26


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/source_preserving_memory_projection_v2_7_adjacency_preregistration.json"
CASES = ROOT / "configs/source_preserving_memory_projection_v2_6_1_population_cases.json"
REPORT_JSON = ROOT / "reports/source_preserving_memory_projection_v2_7_adjacency.json"
REPORT_MD = ROOT / "reports/source_preserving_memory_projection_v2_7_adjacency.md"
LOCK = ROOT / "configs/source_preserving_memory_projection_v2_7_adjacency_result_lock.json"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def adjacency_indices(conversation, session_key, question, anchor_count=2):
    ranked = []
    turns = conversation[session_key]
    for index, turn in enumerate(turns):
        text = v25.turn_text(turn)
        if text:
            ranked.append((-v25.lexical_overlap(question, text), index))
    ranked.sort(key=lambda item: (item[0], item[1]))
    anchors = [index for _, index in ranked[:anchor_count]]
    selected = set()
    for anchor in anchors:
        for index in (anchor - 1, anchor, anchor + 1):
            if 0 <= index < len(turns) and v25.turn_text(turns[index]):
                selected.add(index)
    return sorted(selected), anchors


def selected_turn_text(conversation, session_key, indices):
    return "\n".join(v25.turn_text(conversation[session_key][index]) for index in indices)


def evaluate_record(sample, question, answer, frozen_record, role):
    conversation = sample["conversation"]
    session_key = frozen_record["session_key"]
    indices, anchors = adjacency_indices(conversation, session_key, question)
    projected = v25.serialize_session(conversation, session_key, indices)
    turn_text = selected_turn_text(conversation, session_key, indices)
    source_ids = [str(conversation[session_key][index].get("dia_id") or "") for index in indices]
    source_hashes = [
        v25.canonical_sha256(
            {
                "source_turn_index": index,
                "speaker": str(conversation[session_key][index].get("speaker") or ""),
                "text": v25.turn_text(conversation[session_key][index]),
            }
        )
        for index in indices
    ]
    complete_characters = frozen_record["complete_character_count"]
    return {
        "role": role,
        "session_key": session_key,
        "anchor_turn_indices_rank_order": anchors,
        "selected_turn_indices": indices,
        "selected_turn_ids": source_ids,
        "selected_turn_sha256_list": source_hashes,
        "projected_text_sha256": v25.text_sha256(projected),
        "selected_turn_count": len(indices),
        "projection_character_count": len(projected),
        "complete_character_count": complete_characters,
        "projection_character_ratio": len(projected) / complete_characters,
        "contains_answer_projection": answer.casefold() in turn_text.casefold(),
        "source_exact": all(
            index in frozen_record["source_turn_indices"] for index in indices
        ),
    }


def evaluate(data, manifest, prereg):
    started = time.perf_counter()
    by_id = {str(row["sample_id"]): row for row in data}
    rows = []
    for case in manifest["cases"]:
        sample = by_id[case["sample_id"]]
        qa = sample["qa"][case["qa_index"]]
        question = str(qa["question"])
        answer = str(qa["answer"])
        target = evaluate_record(sample, question, answer, case["target"], "target")
        negative = evaluate_record(
            sample, question, answer, case["hard_negative"], "hard_negative"
        )
        rows.append(
            {
                "case_id": case["case_id"],
                "sample_id": case["sample_id"],
                "qa_index": case["qa_index"],
                "question_sha256": case["question_sha256"],
                "answer_sha256": case["answer_sha256"],
                "target": target,
                "hard_negative": negative,
            }
        )
    control_retention = prereg["frozen_control"]["target_answer_retention_count"]
    retention = sum(row["target"]["contains_answer_projection"] for row in rows)
    target_ratios = [row["target"]["projection_character_ratio"] for row in rows]
    all_ratios = [
        row[role]["projection_character_ratio"]
        for row in rows
        for role in ("target", "hard_negative")
    ]
    metrics = {
        "control_target_answer_retention_count": control_retention,
        "adjacency_target_answer_retention_count": retention,
        "retention_delta_vs_control": retention - control_retention,
        "adjacency_target_answer_omission_count": len(rows) - retention,
        "mean_target_projection_character_ratio": round(
            sum(target_ratios) / len(target_ratios), 6
        ),
        "mean_all_record_projection_character_ratio": round(
            sum(all_ratios) / len(all_ratios), 6
        ),
        "mean_selected_turn_count": round(
            sum(
                row[role]["selected_turn_count"]
                for row in rows
                for role in ("target", "hard_negative")
            )
            / (2 * len(rows)),
            6,
        ),
        "execution_duration_seconds": round(time.perf_counter() - started, 6),
        "reserve_sample_access_count": 0,
        "model_calls": 0,
        "production_memory_write_count": 0,
        "physical_vrm_action_count": 0,
    }
    success = prereg["success_gates"]
    expected_case_keys = [
        (case["case_id"], case["target"]["session_key"], case["hard_negative"]["session_key"])
        for case in manifest["cases"]
    ]
    actual_case_keys = [
        (row["case_id"], row["target"]["session_key"], row["hard_negative"]["session_key"])
        for row in rows
    ]
    gates = {
        "case_count_equals": len(rows) == success["case_count_equals"],
        "adjacency_target_answer_retention_count_at_least": retention
        >= success["adjacency_target_answer_retention_count_at_least"],
        "retention_delta_vs_control_at_least": metrics["retention_delta_vs_control"]
        >= success["retention_delta_vs_control_at_least"],
        "adjacency_target_answer_omission_count_at_most": metrics[
            "adjacency_target_answer_omission_count"
        ]
        <= success["adjacency_target_answer_omission_count_at_most"],
        "mean_target_projection_character_ratio_at_most": metrics[
            "mean_target_projection_character_ratio"
        ]
        <= success["mean_target_projection_character_ratio_at_most"],
        "mean_all_record_projection_character_ratio_at_most": metrics[
            "mean_all_record_projection_character_ratio"
        ]
        <= success["mean_all_record_projection_character_ratio_at_most"],
        "all_selected_turns_are_exact_original_sources": all(
            row[role]["source_exact"]
            for row in rows
            for role in ("target", "hard_negative")
        ),
        "all_case_and_session_ids_match_control": actual_case_keys == expected_case_keys,
        "reserve_sample_access_count_equals": metrics["reserve_sample_access_count"]
        == success["reserve_sample_access_count_equals"],
        "model_calls_equal": metrics["model_calls"] == success["model_calls_equal"],
        "production_memory_write_count_equals": metrics[
            "production_memory_write_count"
        ]
        == success["production_memory_write_count_equals"],
        "physical_vrm_action_count_equals": metrics["physical_vrm_action_count"]
        == success["physical_vrm_action_count_equals"],
    }
    decision = (
        "development_pass_authorize_reserve_holdout_preregistration_only"
        if all(gates.values())
        else "development_reject_adjacency_projection"
    )
    return {
        "schema": "uruha_source_preserving_memory_projection_adjacency_report_v2_7",
        "experiment_id": prereg["experiment_id"],
        "decision": decision,
        "evidence_scope": prereg["evidence_scope"],
        "integrity": {
            "case_manifest_sha256": v25.file_sha256(CASES),
            "case_ids_sha256": v25.canonical_sha256([row["case_id"] for row in rows]),
            "contains_official_text": False,
            "contains_official_answers": False,
        },
        "metrics": metrics,
        "gates": gates,
        "case_diagnostics": rows,
        "authorization": {
            "preregister_reserve_fresh_holdout": all(gates.values()),
            "model_generation": False,
            "use_reserve_conversations_now": False,
            "runtime_change": False,
            "runtime_shadow": False,
            "production_enablement": False,
        },
        "evidence_boundary": prereg["evidence_boundary"],
    }


def markdown(report):
    metrics = report["metrics"]
    failed = [name for name, passed in report["gates"].items() if not passed]
    return "\n".join(
        [
            "# V2.7 Two-anchor Adjacency Projection",
            "",
            f"**決策：`{report['decision']}`**",
            "",
            "| 指標 | Top-3 孤立 control | 鄰接視窗 |",
            "|---|---:|---:|",
            f"| 答案原文保留 | {metrics['control_target_answer_retention_count']}/10 | {metrics['adjacency_target_answer_retention_count']}/10 |",
            f"| 相對增益 | - | {metrics['retention_delta_vs_control']:+d} 題 |",
            f"| 目標平均字元比例 | 17.4% | {metrics['mean_target_projection_character_ratio']:.1%} |",
            f"| 全部 record 平均字元比例 | - | {metrics['mean_all_record_projection_character_ratio']:.1%} |",
            f"| 模型呼叫 | 0 | {metrics['model_calls']} |",
            "",
            "## 未通過門檻",
            "",
            *([f"- `{name}`" for name in failed] or ["- 無"]),
            "",
            "本結果只評價 deterministic source retention，不代表模型、runtime 或完整記憶系統已通過。",
            "",
        ]
    )


def main():
    if REPORT_JSON.exists() or REPORT_MD.exists() or LOCK.exists():
        raise SystemExit("V2.7 adjacency result already exists")
    prereg = load_json(PREREG)
    for relative, expected in (
        (prereg["frozen_control"]["cases_path"], prereg["frozen_control"]["cases_sha256"]),
        (
            prereg["frozen_control"]["result_lock_path"],
            prereg["frozen_control"]["result_lock_sha256"],
        ),
        (prereg["frozen_control"]["report_path"], prereg["frozen_control"]["report_sha256"]),
    ):
        if v25.file_sha256(ROOT / relative) != expected:
            raise ValueError(f"frozen control hash drift: {relative}")
    manifest = load_json(CASES)
    data = v25.ensure_official_dataset(v25.load_preregistration())
    report = evaluate(data, manifest, prereg)
    REPORT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    REPORT_MD.write_text(markdown(report), encoding="utf-8")
    lock = {
        "schema": "uruha_source_preserving_memory_projection_adjacency_result_lock_v2_7",
        "experiment_id": prereg["experiment_id"],
        "decision": report["decision"],
        "model_calls": 0,
        "artifacts": {
            path.relative_to(ROOT).as_posix(): v25.file_sha256(path)
            for path in (PREREG, CASES, Path(__file__), REPORT_JSON, REPORT_MD)
        },
        "authorization": report["authorization"],
        "evidence_boundary": report["evidence_boundary"],
    }
    LOCK.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "decision": report["decision"],
                "retention": report["metrics"]["adjacency_target_answer_retention_count"],
                "delta": report["metrics"]["retention_delta_vs_control"],
                "model_calls": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
