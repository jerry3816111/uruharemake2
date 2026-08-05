#!/usr/bin/env python3
"""Freeze V2.1 source-preserving development cases after the context revision."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import build_source_preserving_memory_projection_v2_development as v2
from audit_semantic_memory_recall_support_v1_evidence_contract import file_sha256, load_dataset
from project_paths import LONGMEMEVAL_S_CLEANED_DATASET_PATH


ROOT = Path(__file__).resolve().parent
BASE_PREREG = ROOT / "configs/source_preserving_memory_projection_v2_development_preregistration.json"
REVISION_PREREG = ROOT / "configs/source_preserving_memory_projection_v2_1_development_preregistration.json"
V1_CASES = ROOT / "configs/semantic_memory_recall_support_v1_holdout_cases.json"
OUTPUT = ROOT / "configs/source_preserving_memory_projection_v2_1_development_cases.json"


def effective_preregistration(base, revision):
    effective = copy.deepcopy(base)
    effective["experiment_id"] = revision["experiment_id"]
    for dotted_path, value in revision["effective_overrides"].items():
        target = effective
        parts = dotted_path.split(".")
        for part in parts[:-1]:
            target = target[part]
        target[parts[-1]] = value
    return effective


def run_preflight():
    command = [
        sys.executable,
        "-m",
        "unittest",
        "-q",
        "test_source_preserving_memory_projection_v2_1_development_preregistration.py",
        "test_build_source_preserving_memory_projection_v2_development.py",
        "test_build_source_preserving_memory_projection_v2_1_development.py",
    ]
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    if completed.returncode:
        raise SystemExit(f"V2.1 builder preflight failed:\n{completed.stdout}\n{completed.stderr}")
    return {"passed": True, "tests": command[4:]}


def main():
    if OUTPUT.exists():
        raise SystemExit("Frozen V2.1 development cases already exist; refusing to overwrite")
    base = json.loads(BASE_PREREG.read_text(encoding="utf-8"))
    revision = json.loads(REVISION_PREREG.read_text(encoding="utf-8"))
    if file_sha256(BASE_PREREG) != revision["base_preregistration"]["sha256"]:
        raise SystemExit("Base preregistration hash drift")
    failure = revision["failed_construction_evidence"]
    if file_sha256(ROOT / failure["lock_path"]) != failure["lock_sha256"]:
        raise SystemExit("Construction failure lock hash drift")
    effective = effective_preregistration(base, revision)
    v1_cases = json.loads(V1_CASES.read_text(encoding="utf-8"))
    excluded_ids = {case["official_question_id"] for case in v1_cases["cases"]}
    data, source_evidence = load_dataset(LONGMEMEVAL_S_CLEANED_DATASET_PATH)
    if source_evidence["sha256"] != effective["official_source"]["dataset_sha256"]:
        raise SystemExit("Official source dataset hash drift")
    preflight = run_preflight()
    selected, eligible_count = v2.select_cases(data, excluded_ids, effective)
    required_count = revision["feasibility_gate_before_case_freeze"][
        "selected_case_count_equals"
    ]
    if eligible_count < revision["feasibility_gate_before_case_freeze"][
        "eligible_case_count_at_least"
    ] or len(selected) != required_count:
        raise SystemExit("V2.1 feasibility gate failed")
    cases = [v2.build_case(item) for item in selected]
    selected_ids = [case["official_question_id"] for case in cases]
    if excluded_ids & set(selected_ids):
        raise SystemExit("V2.1 selection overlaps exposed V1 cases")
    projected_target_answer_count = sum(
        str(case["official_answer"]).casefold()
        in case["target"]["source_projection"]["text"].casefold()
        for case in cases
    )
    projected_negative_answer_count = sum(
        str(case["official_answer"]).casefold()
        in case["hard_negative"]["source_projection"]["text"].casefold()
        for case in cases
    )
    payload = {
        "schema": "uruha_source_preserving_memory_projection_development_cases_v2_1",
        "status": "frozen_before_model_evaluation",
        "experiment_id": revision["experiment_id"],
        "data_status": effective["why_this_is_not_a_holdout"]["status"],
        "source": source_evidence,
        "selection": {
            **effective["case_selection"],
            "eligible_count": eligible_count,
            "selected_question_ids_sha256": v2.canonical_sha256(selected_ids),
        },
        "construction": {
            "model_calls": 0,
            "builder_sha256": file_sha256(__file__),
            "inherited_builder_sha256": file_sha256(v2.__file__),
            "base_preregistration_sha256": file_sha256(BASE_PREREG),
            "revision_preregistration_sha256": file_sha256(REVISION_PREREG),
            "v1_exclusion_artifact_sha256": file_sha256(V1_CASES),
            "preflight": preflight,
        },
        "postconstruction_audit": {
            "projected_target_exact_answer_count": projected_target_answer_count,
            "projected_hard_negative_exact_answer_count": projected_negative_answer_count,
            "all_target_projections_preserve_exact_answer": projected_target_answer_count
            == len(cases),
            "all_hard_negative_projections_exclude_exact_answer": projected_negative_answer_count
            == 0,
        },
        "case_count": len(cases),
        "case_ids_sha256": v2.canonical_sha256([case["case_id"] for case in cases]),
        "cases": cases,
        "authorization": revision["authorization"],
        "evidence_boundary": revision["evidence_boundary"],
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "sha256": file_sha256(OUTPUT),
                "eligible_count": eligible_count,
                "selected_question_ids": selected_ids,
                "projected_target_exact_answer_count": projected_target_answer_count,
                "projected_hard_negative_exact_answer_count": projected_negative_answer_count,
                "model_calls": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
