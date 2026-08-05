#!/usr/bin/env python3
"""Build V2.8 fresh cases without model calls or final-reserve case selection."""

from __future__ import annotations

import json
from pathlib import Path

import build_source_preserving_memory_projection_v2_5_locomo_cases as v25
import build_source_preserving_memory_projection_v2_6_corrected_oracle_cases as v26
import evaluate_source_preserving_memory_projection_v2_7_adjacency as v27


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/source_preserving_memory_projection_v2_8_reserve_holdout_preregistration.json"
OUTPUT = ROOT / "configs/source_preserving_memory_projection_v2_8_reserve_cases.json"


def load_preregistration(path=PREREG):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def frozen_dependencies(prereg):
    return (
        (
            prereg["development_authorization"]["preregistration_path"],
            prereg["development_authorization"]["preregistration_sha256"],
        ),
        (
            prereg["development_authorization"]["result_lock_path"],
            prereg["development_authorization"]["result_lock_sha256"],
        ),
        (
            prereg["development_authorization"]["report_path"],
            prereg["development_authorization"]["report_sha256"],
        ),
        (
            prereg["reserve_partition"]["original_split_preregistration_path"],
            prereg["reserve_partition"]["original_split_preregistration_sha256"],
        ),
        (
            prereg["reserve_partition"]["original_manifest_path"],
            prereg["reserve_partition"]["original_manifest_sha256"],
        ),
        (
            prereg["model_evaluation_contract_to_freeze_after_construction_pass"][
                "single_record_carrier_path"
            ],
            prereg["model_evaluation_contract_to_freeze_after_construction_pass"][
                "single_record_carrier_sha256"
            ],
        ),
        (
            prereg["model_evaluation_contract_to_freeze_after_construction_pass"][
                "boundary_normalizer_path"
            ],
            prereg["model_evaluation_contract_to_freeze_after_construction_pass"][
                "boundary_normalizer_sha256"
            ],
        ),
    )


def verify_frozen_dependencies(prereg, root=ROOT):
    for relative, expected in frozen_dependencies(prereg):
        if v25.file_sha256(Path(root) / relative) != expected:
            raise ValueError(f"frozen source hash drift: {relative}")


def verify_official_source_contract(prereg, source_prereg):
    source = source_prereg["official_source"]
    expected = prereg["official_source"]
    checks = {
        "dataset_sha256": source["dataset_sha256"] == expected["dataset_sha256"],
        "dataset_bytes": source["dataset_bytes"] == expected["dataset_bytes"],
        "conversation_count": source["expected_conversation_count"]
        == expected["conversation_count"],
    }
    if not all(checks.values()):
        failed = [name for name, passed in checks.items() if not passed]
        raise ValueError("official source contract drift: " + ", ".join(failed))


def partition_digest(sample_id, prereg):
    salt = prereg["reserve_partition"]["partition_salt"]
    return v25.text_sha256(f"{salt}:{sample_id}")


def partition_reserve(data, prereg):
    excluded = set(prereg["reserve_partition"]["excluded_exposed_sample_ids"])
    pool = [row for row in data if str(row["sample_id"]) not in excluded]
    pool.sort(key=lambda row: partition_digest(str(row["sample_id"]), prereg))
    fresh_count = prereg["reserve_partition"]["fresh_holdout_conversation_count"]
    return pool[:fresh_count], pool[fresh_count:]


def corrected_selection_prereg(prereg):
    base = v26.load_preregistration()
    base["controlled_variables"]["official_category"] = prereg["case_selection"][
        "official_category"
    ]
    base["controlled_variables"]["selection_salt"] = prereg["case_selection"][
        "selection_salt"
    ]
    return base


def balanced_select(fresh, prereg):
    selection = corrected_selection_prereg(prereg)
    candidates = {
        str(sample["sample_id"]): v26.eligible_cases_for_sample(sample, selection)
        for sample in fresh
    }
    sample_order = [str(sample["sample_id"]) for sample in fresh]
    maximum = prereg["case_selection"]["maximum_cases_per_conversation"]
    required = prereg["case_selection"]["question_count"]
    selected = []
    for round_index in range(maximum):
        for sample_id in sample_order:
            rows = candidates[sample_id]
            if round_index < len(rows) and len(selected) < required:
                selected.append((sample_id, rows[round_index]))
        if len(selected) >= required:
            break
    return selected, {sample_id: len(rows) for sample_id, rows in candidates.items()}


def adjacency_manifest(
    sample, session_key, complete, question, answer, complete_source_indices
):
    conversation = sample["conversation"]
    indices, anchors = v27.adjacency_indices(conversation, session_key, question)
    projected = v25.serialize_session(conversation, session_key, indices)
    turn_text = v27.selected_turn_text(conversation, session_key, indices)
    return {
        "session_key": session_key,
        "anchor_turn_indices_rank_order": anchors,
        "source_turn_indices": indices,
        "source_turn_ids": [
            str(conversation[session_key][index].get("dia_id") or "")
            for index in indices
        ],
        "source_turn_sha256_list": [
            v25.canonical_sha256(
                {
                    "source_turn_index": index,
                    "speaker": str(
                        conversation[session_key][index].get("speaker") or ""
                    ),
                    "text": v25.turn_text(conversation[session_key][index]),
                }
            )
            for index in indices
        ],
        "text_sha256": v25.text_sha256(projected),
        "character_count": len(projected),
        "complete_character_count": len(complete),
        "character_ratio": len(projected) / len(complete),
        "contains_answer": answer.casefold() in turn_text.casefold(),
        "source_exact": indices == sorted(set(indices))
        and all(index in complete_source_indices for index in indices),
    }


def build_manifest(data, prereg, dataset_sha256=None, dataset_bytes=None):
    fresh, final_reserve = partition_reserve(data, prereg)
    selected, eligible_counts = balanced_select(fresh, prereg)
    by_id = {str(row["sample_id"]): row for row in fresh}
    cases = []
    for sample_id, row in selected:
        sample = by_id[sample_id]
        target_complete = v26.corrected_record_manifest(
            sample,
            row["target_key"],
            row["target_complete"],
            row["question"],
            row["answer"],
        )
        negative_complete = v26.corrected_record_manifest(
            sample,
            row["negative_key"],
            row["negative_complete"],
            row["question"],
            row["answer"],
        )
        cases.append(
            {
                "case_id": f"locomo-v2-8-{sample_id}-{row['qa_index']}",
                "sample_id": sample_id,
                "qa_index": row["qa_index"],
                "official_category": prereg["case_selection"]["official_category"],
                "question_sha256": v25.text_sha256(row["question"]),
                "answer_sha256": v25.text_sha256(row["answer"]),
                "evidence_ids_sha256": v25.canonical_sha256(row["evidence"]),
                "evidence_session_count": row["evidence_session_count"],
                "all_evidence_ids_exist": row["all_evidence_ids_exist"],
                "target": {
                    "complete": target_complete,
                    "adjacency": adjacency_manifest(
                        sample,
                        row["target_key"],
                        row["target_complete"],
                        row["question"],
                        row["answer"],
                        target_complete["source_turn_indices"],
                    ),
                },
                "hard_negative": {
                    "complete": negative_complete,
                    "adjacency": adjacency_manifest(
                        sample,
                        row["negative_key"],
                        row["negative_complete"],
                        row["question"],
                        row["answer"],
                        negative_complete["source_turn_indices"],
                    ),
                },
            }
        )
    fresh_ids = [str(row["sample_id"]) for row in fresh]
    final_ids = [str(row["sample_id"]) for row in final_reserve]
    return {
        "schema": "uruha_source_preserving_memory_projection_reserve_cases_v2_8",
        "status": "frozen_before_model_evaluation_contract",
        "experiment_id": prereg["experiment_id"],
        "source": {
            "dataset_sha256": dataset_sha256
            or prereg["official_source"]["dataset_sha256"],
            "dataset_bytes": dataset_bytes
            if dataset_bytes is not None
            else prereg["official_source"]["dataset_bytes"],
        },
        "partition": {
            "fresh_sample_ids": fresh_ids,
            "fresh_sample_ids_sha256": v25.canonical_sha256(fresh_ids),
            "final_reserve_sample_ids_sha256": v25.canonical_sha256(final_ids),
            "fresh_count": len(fresh_ids),
            "final_reserve_count": len(final_ids),
            "overlap_count": len(set(fresh_ids) & set(final_ids)),
            "final_reserve_case_selection_payload_access_count": 0,
        },
        "selection": {
            "eligible_count_by_fresh_sample": eligible_counts,
            "selected_count_by_fresh_sample": {
                sample_id: sum(case["sample_id"] == sample_id for case in cases)
                for sample_id in fresh_ids
            },
        },
        "case_count": len(cases),
        "case_ids_sha256": v25.canonical_sha256([case["case_id"] for case in cases]),
        "contains_official_text": False,
        "contains_official_answers": False,
        "construction_model_calls": 0,
        "cases": cases,
        "authorization": {
            "freeze_model_evaluation_contract": False,
            "model_generation": False,
            "runtime_change": False,
            "production_enablement": False,
        },
    }


def validate_gates(manifest, prereg):
    gates = prereg["construction_gates_before_model_calls"]
    cases = manifest["cases"]
    selected_counts = manifest["selection"]["selected_count_by_fresh_sample"]
    target_retention = sum(case["target"]["adjacency"]["contains_answer"] for case in cases)
    isolated_retention = sum(
        case["target"]["complete"]["contains_answer_projection"] for case in cases
    )
    target_ratios = [case["target"]["adjacency"]["character_ratio"] for case in cases]
    all_ratios = [
        case[role]["adjacency"]["character_ratio"]
        for case in cases
        for role in ("target", "hard_negative")
    ]
    mean_target_ratio = sum(target_ratios) / len(target_ratios) if target_ratios else 0.0
    mean_all_ratio = sum(all_ratios) / len(all_ratios) if all_ratios else 0.0
    checks = {
        "dataset_hash_matches": manifest["source"]["dataset_sha256"]
        == prereg["official_source"]["dataset_sha256"],
        "dataset_bytes_match": manifest["source"]["dataset_bytes"]
        == prereg["official_source"]["dataset_bytes"],
        "reserve_pool_count_equals": manifest["partition"]["fresh_count"]
        + manifest["partition"]["final_reserve_count"]
        == gates["reserve_pool_count_equals"],
        "fresh_holdout_conversation_count_equals": manifest["partition"]["fresh_count"]
        == gates["fresh_holdout_conversation_count_equals"],
        "final_reserve_conversation_count_equals": manifest["partition"][
            "final_reserve_count"
        ]
        == gates["final_reserve_conversation_count_equals"],
        "partition_overlap_equals": manifest["partition"]["overlap_count"]
        == gates["partition_overlap_equals"],
        "question_count_equals": len(cases) == gates["question_count_equals"],
        "represented_conversation_count_at_least": sum(
            count > 0 for count in selected_counts.values()
        )
        >= gates["represented_conversation_count_at_least"],
        "maximum_cases_per_conversation_at_most": max(selected_counts.values(), default=0)
        <= gates["maximum_cases_per_conversation_at_most"],
        "all_corrected_source_oracles_valid": all(
            case["target"]["complete"]["contains_answer_complete"]
            and not case["hard_negative"]["complete"]["contains_answer_complete"]
            and case["all_evidence_ids_exist"]
            and case["evidence_session_count"] == 1
            for case in cases
        )
        and bool(cases),
        "adjacency_answer_retention_count_at_least": target_retention
        >= gates["adjacency_answer_retention_count_at_least"],
        "adjacency_retention_delta_vs_isolated_at_least": target_retention
        - isolated_retention
        >= gates["adjacency_retention_delta_vs_isolated_at_least"],
        "mean_target_adjacency_character_ratio_at_most": mean_target_ratio
        <= gates["mean_target_adjacency_character_ratio_at_most"],
        "mean_all_record_adjacency_character_ratio_at_most": mean_all_ratio
        <= gates["mean_all_record_adjacency_character_ratio_at_most"],
        "all_adjacency_turns_are_exact_sources": all(
            case[role]["adjacency"]["source_exact"]
            for case in cases
            for role in ("target", "hard_negative")
        )
        and bool(cases),
        "final_reserve_case_selection_payload_access_count_equals": manifest[
            "partition"
        ][
            "final_reserve_case_selection_payload_access_count"
        ]
        == gates["final_reserve_case_selection_payload_access_count_equals"],
        "model_calls_equal": manifest["construction_model_calls"]
        == gates["model_calls_equal"],
    }
    metrics = {
        "isolated_target_answer_retention_count": isolated_retention,
        "adjacency_target_answer_retention_count": target_retention,
        "retention_delta_vs_isolated": target_retention - isolated_retention,
        "mean_target_adjacency_character_ratio": round(mean_target_ratio, 6),
        "mean_all_record_adjacency_character_ratio": round(mean_all_ratio, 6),
    }
    return checks, metrics


def main():
    if OUTPUT.exists():
        raise SystemExit("V2.8 reserve case manifest already exists")
    prereg = load_preregistration()
    verify_frozen_dependencies(prereg)
    source_prereg = v25.load_preregistration()
    verify_official_source_contract(prereg, source_prereg)
    data = v25.ensure_official_dataset(source_prereg)
    manifest = build_manifest(
        data,
        prereg,
        dataset_sha256=v25.file_sha256(v25.DATASET),
        dataset_bytes=v25.DATASET.stat().st_size,
    )
    checks, metrics = validate_gates(manifest, prereg)
    manifest["construction_gates"] = checks
    manifest["construction_metrics"] = metrics
    manifest["authorization"]["freeze_model_evaluation_contract"] = all(checks.values())
    OUTPUT.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "sha256": v25.file_sha256(OUTPUT),
                "case_count": manifest["case_count"],
                "metrics": metrics,
                "failed_gates": [name for name, passed in checks.items() if not passed],
                "model_calls": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
