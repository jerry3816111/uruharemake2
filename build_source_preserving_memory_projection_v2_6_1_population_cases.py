#!/usr/bin/env python3
"""Build all corrected-oracle cases from the exposed LoCoMo population."""

from __future__ import annotations

import json
from pathlib import Path

import build_source_preserving_memory_projection_v2_5_locomo_cases as v25
import build_source_preserving_memory_projection_v2_6_corrected_oracle_cases as v26


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/source_preserving_memory_projection_v2_6_1_population_preregistration.json"
OUTPUT = ROOT / "configs/source_preserving_memory_projection_v2_6_1_population_cases.json"


def load_preregistration(path=PREREG):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_manifest(data, base, revision):
    by_id = {str(row["sample_id"]): row for row in data}
    expected_counts = revision["controlled_variables"]["expected_case_count_by_sample"]
    cases = []
    for sample_id in revision["controlled_variables"]["exposed_sample_ids"]:
        sample = by_id[sample_id]
        eligible = v26.eligible_cases_for_sample(sample, base)
        if len(eligible) != expected_counts[sample_id]:
            raise ValueError(
                f"corrected population drift for {sample_id}: {len(eligible)}"
            )
        for row in eligible:
            cases.append(
                {
                    "case_id": f"locomo-v2-6-1-{sample_id}-{row['qa_index']}",
                    "sample_id": sample_id,
                    "qa_index": row["qa_index"],
                    "official_category": revision["controlled_variables"][
                        "official_category"
                    ],
                    "question_sha256": v25.text_sha256(row["question"]),
                    "answer_sha256": v25.text_sha256(row["answer"]),
                    "evidence_ids_sha256": v25.canonical_sha256(row["evidence"]),
                    "evidence_id_count": len(row["evidence"]),
                    "all_evidence_ids_exist": row["all_evidence_ids_exist"],
                    "evidence_session_count": row["evidence_session_count"],
                    "target": v26.corrected_record_manifest(
                        sample,
                        row["target_key"],
                        row["target_complete"],
                        row["question"],
                        row["answer"],
                    ),
                    "hard_negative": v26.corrected_record_manifest(
                        sample,
                        row["negative_key"],
                        row["negative_complete"],
                        row["question"],
                        row["answer"],
                    ),
                }
            )
    return {
        "schema": "uruha_source_preserving_memory_projection_exposed_population_cases_v2_6_1",
        "status": "frozen_corrected_oracle_development_baseline",
        "experiment_id": revision["experiment_id"],
        "source": {
            "dataset_sha256": revision["controlled_variables"][
                "official_dataset_sha256"
            ]
        },
        "exposed_sample_ids": revision["controlled_variables"]["exposed_sample_ids"],
        "reserve_sample_access_count": 0,
        "case_count": len(cases),
        "case_ids_sha256": v25.canonical_sha256([case["case_id"] for case in cases]),
        "contains_official_text": False,
        "contains_official_answers": False,
        "construction_model_calls": 0,
        "cases": cases,
    }


def validate_gates(manifest, revision):
    gates = revision["construction_gates"]
    cases = manifest["cases"]
    counts = {}
    for case in cases:
        counts[case["sample_id"]] = counts.get(case["sample_id"], 0) + 1
    checks = {
        "question_count_equals": manifest["case_count"] == gates["question_count_equals"],
        "case_count_by_sample_equals_frozen_map": counts
        == revision["controlled_variables"]["expected_case_count_by_sample"],
        "all_target_answers_exist_in_original_turn_text": all(
            case["target"]["contains_answer_complete"] for case in cases
        ),
        "all_hard_negative_answers_absent_from_original_turn_text": all(
            not case["hard_negative"]["contains_answer_complete"] for case in cases
        ),
        "all_official_evidence_ids_exist": all(
            case["all_evidence_ids_exist"] for case in cases
        ),
        "all_official_evidence_belongs_to_one_session": all(
            case["evidence_session_count"] == 1 for case in cases
        ),
        "manifest_contains_official_text": manifest["contains_official_text"]
        is gates["manifest_contains_official_text"],
        "manifest_contains_official_answers": manifest["contains_official_answers"]
        is gates["manifest_contains_official_answers"],
        "reserve_sample_access_count_equals": manifest["reserve_sample_access_count"]
        == gates["reserve_sample_access_count_equals"],
        "model_calls_equal": manifest["construction_model_calls"]
        == gates["model_calls_equal"],
    }
    if not all(checks.values()):
        raise ValueError(
            "V2.6.1 construction gates failed: "
            + ", ".join(name for name, passed in checks.items() if not passed)
        )
    return checks


def main():
    if OUTPUT.exists():
        raise SystemExit("V2.6.1 population manifest already exists")
    revision = load_preregistration()
    base = v26.load_preregistration()
    for name, path_key, hash_key in (
        ("base preregistration", "preregistration_path", "preregistration_sha256"),
        ("feasibility lock", "feasibility_lock_path", "feasibility_lock_sha256"),
        ("feasibility report", "feasibility_report_path", "feasibility_report_sha256"),
    ):
        expected = revision["failed_control"][hash_key]
        actual = v25.file_sha256(ROOT / revision["failed_control"][path_key])
        if actual != expected:
            raise ValueError(f"{name} hash drift")
    data = v25.ensure_official_dataset(v25.load_preregistration())
    manifest = build_manifest(data, base, revision)
    manifest["construction_gates"] = validate_gates(manifest, revision)
    OUTPUT.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    ratios = [
        case["target"]["projection_character_count"]
        / case["target"]["complete_character_count"]
        for case in manifest["cases"]
    ]
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "sha256": v25.file_sha256(OUTPUT),
                "case_count": manifest["case_count"],
                "projection_answer_retention_count": sum(
                    case["target"]["contains_answer_projection"]
                    for case in manifest["cases"]
                ),
                "mean_target_character_ratio": sum(ratios) / len(ratios),
                "reserve_sample_access_count": 0,
                "model_calls": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
