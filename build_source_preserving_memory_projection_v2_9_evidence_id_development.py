#!/usr/bin/env python3
"""Evaluate frozen projections with official LoCoMo evidence IDs, without a model."""

from __future__ import annotations

import json
from pathlib import Path

import build_source_preserving_memory_projection_v2_5_locomo_cases as v25
import evaluate_source_preserving_memory_projection_v2_7_adjacency as v27


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/source_preserving_memory_projection_v2_9_evidence_id_preregistration.json"
OUTPUT = ROOT / "reports/source_preserving_memory_projection_v2_9_evidence_id_development.json"


def load_preregistration(path=PREREG):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def frozen_dependencies(prereg):
    sources = prereg["frozen_sources"]
    return (
        (sources["v2_8_result_lock_path"], sources["v2_8_result_lock_sha256"]),
        (sources["v2_8_cases_path"], sources["v2_8_cases_sha256"]),
        (sources["v2_8_report_path"], sources["v2_8_report_sha256"]),
        (sources["isolated_projection_path"], sources["isolated_projection_sha256"]),
        (sources["adjacency_projection_path"], sources["adjacency_projection_sha256"]),
    )


def verify_frozen_dependencies(prereg, root=ROOT):
    for relative, expected in frozen_dependencies(prereg):
        if v25.file_sha256(Path(root) / relative) != expected:
            raise ValueError(f"frozen source hash drift: {relative}")


def unique_strings(values):
    result = []
    seen = set()
    for value in values or []:
        normalized = str(value).strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def dialog_locations(conversation):
    locations = {}
    for session_key in v25.session_keys(conversation):
        for turn_index, turn in enumerate(conversation[session_key]):
            dialog_id = str(turn.get("dia_id") or "").strip()
            if dialog_id:
                locations.setdefault(dialog_id, []).append((session_key, turn_index))
    return locations


def eligible_cases(sample, prereg):
    conversation = sample["conversation"]
    locations = dialog_locations(conversation)
    category = prereg["official_source"]["official_category"]
    maximum = prereg["development_scope"]["maximum_session_characters"]
    cases = []
    for qa_index, qa in enumerate(sample.get("qa") or []):
        if qa.get("category") != category:
            continue
        question = str(qa.get("question") or "").strip()
        evidence_ids = unique_strings(qa.get("evidence"))
        if not question or not evidence_ids:
            continue
        if not all(len(locations.get(dialog_id, [])) == 1 for dialog_id in evidence_ids):
            continue
        evidence_locations = [locations[dialog_id][0] for dialog_id in evidence_ids]
        evidence_sessions = {session_key for session_key, _index in evidence_locations}
        if len(evidence_sessions) != 1:
            continue
        target_session = next(iter(evidence_sessions))
        complete = v25.serialize_session(conversation, target_session)
        if len(complete) > maximum:
            continue
        cases.append(
            {
                "qa_index": qa_index,
                "question": question,
                "evidence_ids": evidence_ids,
                "target_session": target_session,
                "complete": complete,
            }
        )
    return cases


def projection_manifest(
    conversation, session_key, complete, evidence_ids, source_indices, anchor_indices=None
):
    source_indices = sorted(set(source_indices))
    turns = conversation[session_key]
    selected_ids = [str(turns[index].get("dia_id") or "") for index in source_indices]
    selected_id_set = set(selected_ids)
    evidence_set = set(evidence_ids)
    evidence_hit_count = len(evidence_set & selected_id_set)
    projected = v25.serialize_session(conversation, session_key, source_indices)
    return {
        "source_turn_indices": source_indices,
        "source_turn_ids_sha256": v25.canonical_sha256(selected_ids),
        "source_turn_sha256_list": [
            v25.canonical_sha256(
                {
                    "source_turn_index": index,
                    "speaker": str(turns[index].get("speaker") or ""),
                    "text": v25.turn_text(turns[index]),
                }
            )
            for index in source_indices
        ],
        "anchor_turn_indices_rank_order": list(anchor_indices or []),
        "projection_text_sha256": v25.text_sha256(projected),
        "projection_character_count": len(projected),
        "complete_character_count": len(complete),
        "character_ratio": len(projected) / len(complete),
        "official_evidence_count": len(evidence_set),
        "official_evidence_hit_count": evidence_hit_count,
        "official_evidence_recall": evidence_hit_count / len(evidence_set),
        "contains_any_official_evidence": evidence_hit_count > 0,
        "contains_all_official_evidence": evidence_hit_count == len(evidence_set),
        "source_exact": source_indices == sorted(set(source_indices))
        and all(0 <= index < len(turns) for index in source_indices),
    }


def evaluate_case(sample, row):
    conversation = sample["conversation"]
    session_key = row["target_session"]
    isolated_indices = v25.projection_indices(
        conversation, session_key, row["question"], top_k=3
    )
    adjacency_indices, anchors = v27.adjacency_indices(
        conversation, session_key, row["question"]
    )
    return {
        "case_id": f"locomo-v2-9-{sample['sample_id']}-{row['qa_index']}",
        "sample_id": str(sample["sample_id"]),
        "qa_index": row["qa_index"],
        "question_sha256": v25.text_sha256(row["question"]),
        "official_evidence_ids_sha256": v25.canonical_sha256(row["evidence_ids"]),
        "target_session": session_key,
        "isolated": projection_manifest(
            conversation,
            session_key,
            row["complete"],
            row["evidence_ids"],
            isolated_indices,
        ),
        "adjacency": projection_manifest(
            conversation,
            session_key,
            row["complete"],
            row["evidence_ids"],
            adjacency_indices,
            anchors,
        ),
    }


def mean(values):
    return sum(values) / len(values) if values else 0.0


def build_report(data, prereg, dataset_sha256=None, dataset_bytes=None):
    exposed_ids = prereg["development_scope"]["exposed_sample_ids"]
    by_id = {str(row["sample_id"]): row for row in data}
    exposed = [by_id[sample_id] for sample_id in exposed_ids]
    cases = [
        evaluate_case(sample, row)
        for sample in exposed
        for row in eligible_cases(sample, prereg)
    ]
    evidence_total = sum(case["isolated"]["official_evidence_count"] for case in cases)
    isolated_hits = sum(
        case["isolated"]["official_evidence_hit_count"] for case in cases
    )
    adjacency_hits = sum(
        case["adjacency"]["official_evidence_hit_count"] for case in cases
    )
    isolated_micro = isolated_hits / evidence_total if evidence_total else 0.0
    adjacency_micro = adjacency_hits / evidence_total if evidence_total else 0.0
    adjacency_full_rate = mean(
        [
            float(case["adjacency"]["contains_all_official_evidence"])
            for case in cases
        ]
    )
    per_sample = {
        sample_id: sum(case["sample_id"] == sample_id for case in cases)
        for sample_id in exposed_ids
    }
    metrics = {
        "eligible_case_count": len(cases),
        "represented_conversation_count": sum(count > 0 for count in per_sample.values()),
        "official_evidence_id_count": evidence_total,
        "isolated_official_evidence_hit_count": isolated_hits,
        "adjacency_official_evidence_hit_count": adjacency_hits,
        "isolated_micro_evidence_recall": round(isolated_micro, 6),
        "adjacency_micro_evidence_recall": round(adjacency_micro, 6),
        "adjacency_micro_recall_delta_vs_isolated": round(
            adjacency_micro - isolated_micro, 6
        ),
        "isolated_full_evidence_case_count": sum(
            case["isolated"]["contains_all_official_evidence"] for case in cases
        ),
        "adjacency_full_evidence_case_count": sum(
            case["adjacency"]["contains_all_official_evidence"] for case in cases
        ),
        "adjacency_full_evidence_case_rate": round(
            adjacency_full_rate, 6
        ),
        "mean_isolated_character_ratio": round(
            mean([case["isolated"]["character_ratio"] for case in cases]), 6
        ),
        "mean_adjacency_character_ratio": round(
            mean([case["adjacency"]["character_ratio"] for case in cases]), 6
        ),
        "final_reserve_case_selection_payload_access_count": 0,
        "model_calls": 0,
        "production_memory_write_count": 0,
        "physical_vrm_action_count": 0,
    }
    gates = prereg["success_gates"]
    checks = {
        "dataset_hash_matches": (
            dataset_sha256
            if dataset_sha256 is not None
            else prereg["official_source"]["dataset_sha256"]
        )
        == prereg["official_source"]["dataset_sha256"],
        "dataset_bytes_match": (
            dataset_bytes
            if dataset_bytes is not None
            else prereg["official_source"]["dataset_bytes"]
        )
        == prereg["official_source"]["dataset_bytes"],
        "exposed_sample_ids_hash_matches": v25.canonical_sha256(exposed_ids)
        == prereg["development_scope"]["exposed_sample_ids_sha256"],
        "eligible_case_count_at_least": len(cases)
        >= gates["eligible_case_count_at_least"],
        "represented_conversation_count_equals": metrics[
            "represented_conversation_count"
        ]
        == gates["represented_conversation_count_equals"],
        "all_official_evidence_ids_exist_exactly_once": bool(cases),
        "all_official_evidence_ids_belong_to_one_session": bool(cases),
        "adjacency_micro_evidence_recall_at_least": adjacency_micro
        >= gates["adjacency_micro_evidence_recall_at_least"],
        "adjacency_micro_recall_delta_vs_isolated_at_least": adjacency_micro
        - isolated_micro
        >= gates["adjacency_micro_recall_delta_vs_isolated_at_least"],
        "adjacency_full_evidence_case_rate_at_least": adjacency_full_rate
        >= gates["adjacency_full_evidence_case_rate_at_least"],
        "mean_adjacency_character_ratio_at_most": metrics[
            "mean_adjacency_character_ratio"
        ]
        <= gates["mean_adjacency_character_ratio_at_most"],
        "all_selected_turns_are_exact_original_sources": bool(cases)
        and all(
            case[representation]["source_exact"]
            for case in cases
            for representation in ("isolated", "adjacency")
        ),
        "final_reserve_case_selection_payload_access_count_equals": metrics[
            "final_reserve_case_selection_payload_access_count"
        ]
        == gates["final_reserve_case_selection_payload_access_count_equals"],
        "model_calls_equal": metrics["model_calls"] == gates["model_calls_equal"],
        "production_memory_write_count_equals": metrics[
            "production_memory_write_count"
        ]
        == gates["production_memory_write_count_equals"],
        "physical_vrm_action_count_equals": metrics["physical_vrm_action_count"]
        == gates["physical_vrm_action_count_equals"],
    }
    passed = all(checks.values())
    return {
        "schema": "uruha_source_preserving_memory_projection_evidence_id_report_v2_9",
        "experiment_id": prereg["experiment_id"],
        "decision": "development_pass_authorize_final_reserve_preregistration_only"
        if passed
        else "development_reject_adjacency_evidence_retention",
        "source": {
            "dataset_sha256": dataset_sha256
            if dataset_sha256 is not None
            else prereg["official_source"]["dataset_sha256"],
            "dataset_bytes": dataset_bytes
            if dataset_bytes is not None
            else prereg["official_source"]["dataset_bytes"],
        },
        "scope": {
            "exposed_sample_ids": exposed_ids,
            "exposed_sample_ids_sha256": v25.canonical_sha256(exposed_ids),
            "case_count_by_sample": per_sample,
            "final_reserve_sample_ids_sha256": prereg["development_scope"][
                "final_reserve_sample_ids_sha256"
            ],
        },
        "contains_official_text": False,
        "contains_official_answers": False,
        "metrics": metrics,
        "gates": checks,
        "cases": cases,
        "authorization": {
            "preregister_final_reserve_validation": passed,
            "access_final_reserve_case_selection_payload_now": False,
            "run_model_generation": False,
            "runtime_change": False,
            "runtime_shadow": False,
            "production_enablement": False,
        },
        "evidence_boundary": prereg["evidence_boundary"],
    }


def main():
    if OUTPUT.exists():
        raise SystemExit("V2.9 evidence-ID development report already exists")
    prereg = load_preregistration()
    verify_frozen_dependencies(prereg)
    source_prereg = v25.load_preregistration()
    data = v25.ensure_official_dataset(source_prereg)
    report = build_report(
        data,
        prereg,
        dataset_sha256=v25.file_sha256(v25.DATASET),
        dataset_bytes=v25.DATASET.stat().st_size,
    )
    if report["source"]["dataset_sha256"] != prereg["official_source"]["dataset_sha256"]:
        raise ValueError("official dataset hash drift")
    if report["source"]["dataset_bytes"] != prereg["official_source"]["dataset_bytes"]:
        raise ValueError("official dataset byte-size drift")
    OUTPUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "sha256": v25.file_sha256(OUTPUT),
                "decision": report["decision"],
                "metrics": report["metrics"],
                "failed_gates": [
                    name for name, passed in report["gates"].items() if not passed
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
