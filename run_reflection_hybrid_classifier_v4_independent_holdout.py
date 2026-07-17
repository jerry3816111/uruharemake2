#!/usr/bin/env python3
"""Run the frozen 4B native-tool reflection fallback on the new holdout."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import uruha_reflection_runtime as reflection
from reflection_hybrid_classifier_v2_core import analyze_condition
from reflection_hybrid_classifier_v4_core import scorer_gates
from run_reflection_classifier_v1_baseline import git_value, sha256
from run_reflection_hybrid_classifier_v3_tool_carrier_development import (
    _call_model,
    _get_json,
    _ollama_version,
    _parse_tool_response,
)


ROOT = Path(__file__).resolve().parent
PREREG_PATH = (
    ROOT
    / "configs"
    / "reflection_hybrid_classifier_v4_independent_holdout_construction_preregistration.json"
)
AMENDMENT_PATH = (
    ROOT
    / "configs"
    / "reflection_hybrid_classifier_v4_independent_holdout_protocol_amendment.json"
)
CONSTRUCTION_CLOSURE_PATH = (
    ROOT
    / "configs"
    / "reflection_hybrid_classifier_v4_independent_holdout_construction_closure.json"
)
CARRIER_CONTRACT_PATH = (
    ROOT
    / "configs"
    / "reflection_hybrid_classifier_v3_tool_carrier_development_preregistration.json"
)
V3_RESULT_LOCK_PATH = (
    ROOT / "configs" / "reflection_hybrid_classifier_v3_tool_carrier_result_lock.json"
)
LOCK_PATH = (
    ROOT
    / "configs"
    / "reflection_hybrid_classifier_v4_independent_holdout_harness_lock.json"
)
DATASET_PATH = (
    ROOT / "datasets" / "reflection_hybrid_classifier_v4_independent_holdout.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / "reports"
    / "reflection_hybrid_classifier_v4_independent_holdout_raw.json"
)
TAGS_URL = "http://127.0.0.1:11434/api/tags"
TZ = ZoneInfo("Asia/Tokyo")


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_write(path, payload):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def _model_snapshot(model, expected_digest):
    actual = {row["name"]: row for row in (_get_json(TAGS_URL).get("models") or [])}
    row = actual.get(model)
    if not row or row.get("digest") != expected_digest:
        raise ValueError(f"missing or drifted local model: {model}")
    return {
        "digest": row["digest"],
        "size_bytes": row.get("size"),
        "details": row.get("details") or {},
    }


def verify(preregistration, amendment, contract, lock):
    if git_value("branch", "--show-current") != lock["required_run_branch"]:
        raise ValueError("independent holdout must run from main")
    if git_value("rev-parse", "HEAD") != git_value(
        "rev-parse", lock["required_head_ref"]
    ):
        raise ValueError("main must match the locked remote ref")
    if git_value("status", "--porcelain", "--untracked-files=no"):
        raise ValueError("tracked worktree must be clean")
    if _ollama_version() != contract["local_runtime"]["ollama_version"]:
        raise ValueError("Ollama version drift")
    for key, expected in lock["frozen_artifacts"].items():
        if not key.endswith("_sha256"):
            continue
        path_key = key.removesuffix("_sha256")
        if sha256(ROOT / lock["frozen_artifacts"][path_key]) != expected:
            raise ValueError(f"frozen artifact drift: {path_key}")
    if amendment["decision"] != (
        "authorize_harness_freeze_with_only_the_documented_22_call_resource_correction"
    ):
        raise ValueError("protocol amendment does not authorize harness freeze")
    if preregistration["evaluated_model_inference_before_dataset_and_harness_freeze_authorized"]:
        raise ValueError("invalid preregistration inference policy")
    if lock["model_inference_before_harness_merge_authorized"]:
        raise ValueError("invalid harness inference policy")


def _new_report(
    preregistration,
    amendment,
    contract,
    model,
    model_snapshot,
    rules_predictions,
):
    return {
        "schema": "uruha_reflection_hybrid_classifier_independent_holdout_raw_v4",
        "evidence_status": "model_blind_id_disjoint_same_corpus_engineering_holdout",
        "started_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "completed_at": None,
        "runner_commit": git_value("rev-parse", "HEAD"),
        "runner_branch": git_value("branch", "--show-current"),
        "ollama_version": _ollama_version(),
        "preregistration_sha256": sha256(PREREG_PATH),
        "protocol_amendment_sha256": sha256(AMENDMENT_PATH),
        "construction_closure_sha256": sha256(CONSTRUCTION_CLOSURE_PATH),
        "carrier_contract_sha256": sha256(CARRIER_CONTRACT_PATH),
        "v3_result_lock_sha256": sha256(V3_RESULT_LOCK_PATH),
        "harness_lock_sha256": sha256(LOCK_PATH),
        "dataset_sha256": sha256(DATASET_PATH),
        "model": model,
        "model_snapshot": model_snapshot,
        "model_calls": 0,
        "gold_label_passed_to_model": False,
        "rules_predictions": rules_predictions,
        "fallback_rows": [],
        "gate_snapshot": None,
        "runtime_memory_write_performed": False,
    }


def run(output=DEFAULT_OUTPUT):
    preregistration = _load(PREREG_PATH)
    amendment = _load(AMENDMENT_PATH)
    contract = _load(CARRIER_CONTRACT_PATH)
    lock = _load(LOCK_PATH)
    verify(preregistration, amendment, contract, lock)
    dataset = _load(DATASET_PATH)
    model = preregistration["frozen_system_conditions"]["selected_model"]
    digest = preregistration["frozen_system_conditions"]["selected_model_digest"]
    model_snapshot = _model_snapshot(model, digest)
    rules_predictions = {
        case["id"]: reflection.classify_reflection_type(case["text"])
        for case in dataset["cases"]
    }
    rules_none_ids = [
        case["id"]
        for case in dataset["cases"]
        if rules_predictions[case["id"]] == "none"
    ]
    expected_none_ids = amendment["frozen_rules_feasibility_snapshot"][
        "rules_none_case_ids"
    ]
    if rules_none_ids != expected_none_ids:
        raise ValueError("rules-none feasibility snapshot drift")

    if output.exists():
        report = _load(output)
        if report.get("completed_at"):
            raise FileExistsError("refusing to rerun a completed independent holdout")
        expected_resume = {
            "runner_commit": git_value("rev-parse", "HEAD"),
            "runner_branch": lock["required_run_branch"],
            "ollama_version": _ollama_version(),
            "preregistration_sha256": sha256(PREREG_PATH),
            "protocol_amendment_sha256": sha256(AMENDMENT_PATH),
            "construction_closure_sha256": sha256(CONSTRUCTION_CLOSURE_PATH),
            "carrier_contract_sha256": sha256(CARRIER_CONTRACT_PATH),
            "v3_result_lock_sha256": sha256(V3_RESULT_LOCK_PATH),
            "harness_lock_sha256": sha256(LOCK_PATH),
            "dataset_sha256": sha256(DATASET_PATH),
            "model": model,
            "model_snapshot": model_snapshot,
            "rules_predictions": rules_predictions,
            "gold_label_passed_to_model": False,
        }
        for key, expected in expected_resume.items():
            if report.get(key) != expected:
                raise ValueError(f"resume provenance drift: {key}")
    else:
        report = _new_report(
            preregistration,
            amendment,
            contract,
            model,
            model_snapshot,
            rules_predictions,
        )
        _atomic_write(output, report)

    completed_case_ids = {row["id"] for row in report["fallback_rows"]}
    maximum_calls = amendment["protocol_change"]["corrected_value"]
    for case in dataset["cases"]:
        if rules_predictions[case["id"]] != "none":
            continue
        if case["id"] in completed_case_ids:
            continue
        if report["model_calls"] >= maximum_calls:
            raise ValueError("model call ceiling reached before full fallback coverage")
        called = _call_model(contract, model, case["language"], case["text"])
        report["fallback_rows"].append({"id": case["id"], **called})
        report["model_calls"] += 1
        _atomic_write(output, report)

    report["gate_snapshot"] = analyze_condition(
        dataset["cases"],
        rules_predictions,
        report["fallback_rows"],
        scorer_gates(preregistration, amendment),
    )
    report["completed_at"] = datetime.now(TZ).isoformat(timespec="seconds")
    _atomic_write(output, report)
    subprocess.run(
        ["ollama", "stop", model],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(output)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    run(args.output)


if __name__ == "__main__":
    main()
