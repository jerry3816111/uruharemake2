#!/usr/bin/env python3
"""Run the frozen staged local-model screen for answer-bearing memory spans."""

import argparse
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from run_answer_bearing_memory_span_v1_development import (
    ROOT,
    call_evidence_model,
    condition_candidates,
    file_sha256,
    git_value,
    installed_models,
    load_json,
    run_one,
)


PREREG_PATH = ROOT / "configs/answer_bearing_memory_span_model_capacity_v1_preregistration.json"
DEFAULT_RAW = ROOT / "analysis/local_answer_bearing_memory_span_model_capacity_v1/raw.jsonl"
DEFAULT_METADATA = ROOT / "analysis/local_answer_bearing_memory_span_model_capacity_v1/run_metadata.json"


def verify_frozen_scope(prereg, endpoint):
    for artifact in prereg["frozen_artifacts"].values():
        if file_sha256(ROOT / artifact["path"]) != artifact["sha256"]:
            raise ValueError(f"frozen artifact drift: {artifact['path']}")
    inventory = {row.get("name"): row for row in installed_models(endpoint)}
    for model in prereg["models"]:
        row = inventory.get(model["tag"])
        if not row:
            raise ValueError(f"missing local model: {model['tag']}")
        if row.get("digest") != model["digest"]:
            raise ValueError(f"model digest mismatch: {model['tag']}")


def model_v1_prereg(v1_prereg, model):
    payload = deepcopy(v1_prereg)
    payload["inference"]["model"] = model["tag"]
    payload["inference"]["model_digest"] = model["digest"]
    return payload


def add_model_identity(row, model, stage, reused=False):
    output = dict(row)
    output["screen_model"] = model["tag"]
    output["screen_model_digest"] = model["digest"]
    output["screen_stage"] = stage
    output["reused_prior_result"] = bool(reused)
    return output


def phase_1_summary(rows):
    target_only = [
        row for row in rows if row["condition"] == "n1_remove_exact_hard_negative"
    ]
    target_removed = [
        row for row in rows if row["condition"] == "t1_remove_exact_target"
    ]
    contract_valid = all(row["evidence_validation"].get("valid", False) for row in rows)
    spans_grounded = all(
        row["evidence_validation"].get("all_spans_grounded", False) for row in rows
    )
    target_only_safe_count = sum(row["safe_outcome"] for row in target_only)
    target_removed_selection_count = sum(row["selected"] for row in target_removed)
    transport_error_count = sum(row["transport_error_count"] for row in rows)
    passed = (
        len(target_only) == 8
        and len(target_removed) == 8
        and contract_valid
        and spans_grounded
        and target_only_safe_count >= 6
        and target_removed_selection_count == 0
        and transport_error_count == 0
    )
    return {
        "decision_count": len(rows),
        "contract_valid": contract_valid,
        "all_positive_spans_grounded": spans_grounded,
        "target_only_safe_count": target_only_safe_count,
        "target_only_safe_rate": round(target_only_safe_count / 8, 6),
        "target_removed_selection_count": target_removed_selection_count,
        "transport_error_count": transport_error_count,
        "passed": passed,
    }


def load_reused_rows(model):
    rows = [
        json.loads(line)
        for line in (ROOT / model["prior_raw_path"]).read_text(encoding="utf-8").splitlines()
        if line
    ]
    return [add_model_identity(row, model, "reused_complete", reused=True) for row in rows]


def run_screen(prereg, endpoint, model_call=call_evidence_model):
    v1_prereg = load_json(ROOT / prereg["frozen_artifacts"]["v1_preregistration"]["path"])
    cases = load_json(ROOT / v1_prereg["development_data"]["cases_path"])["cases"]
    condition_map = {row["id"]: row for row in v1_prereg["conditions"]}
    phase_1_conditions = [
        condition_map[name] for name in prereg["staged_execution"]["phase_1_conditions"]
    ]
    phase_2_conditions = [
        condition_map[name]
        for name in prereg["staged_execution"]["phase_2_conditions_for_survivors"]
    ]
    all_rows = []
    execution = {}
    for model in prereg["models"]:
        if model.get("reuse_prior_result"):
            rows = load_reused_rows(model)
            all_rows.extend(rows)
            phase_rows = [
                row
                for row in rows
                if row["condition"] in prereg["staged_execution"]["phase_1_conditions"]
            ]
            execution[model["tag"]] = {
                "reused_prior_result": True,
                "phase_1": phase_1_summary(phase_rows),
                "phase_2_run": True,
                "decision_count": len(rows),
                "new_model_call_count": 0,
            }
            continue

        selected_prereg = model_v1_prereg(v1_prereg, model)
        phase_rows = []
        for case in cases:
            for condition in phase_1_conditions:
                row = run_one(
                    case,
                    condition,
                    selected_prereg,
                    endpoint,
                    model_call=model_call,
                )
                phase_rows.append(add_model_identity(row, model, "phase_1"))
        phase_summary = phase_1_summary(phase_rows)
        all_rows.extend(phase_rows)
        phase_2_rows = []
        if phase_summary["passed"]:
            for case in cases:
                for condition in phase_2_conditions:
                    row = run_one(
                        case,
                        condition,
                        selected_prereg,
                        endpoint,
                        model_call=model_call,
                    )
                    phase_2_rows.append(add_model_identity(row, model, "phase_2"))
            all_rows.extend(phase_2_rows)
        execution[model["tag"]] = {
            "reused_prior_result": False,
            "phase_1": phase_summary,
            "phase_2_run": phase_summary["passed"],
            "decision_count": len(phase_rows) + len(phase_2_rows),
            "new_model_call_count": len(phase_rows) + len(phase_2_rows),
        }
    return all_rows, execution


def write_outputs(rows, execution, prereg, raw_path, metadata_path, endpoint):
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    metadata = {
        "schema": "uruha_answer_bearing_memory_span_model_capacity_run_metadata_v1",
        "experiment_id": prereg["experiment_id"],
        "run_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_value("rev-parse", "HEAD"),
        "git_status_short": git_value("status", "--short"),
        "endpoint": endpoint,
        "row_count": len(rows),
        "raw_path": str(raw_path.relative_to(ROOT)),
        "raw_sha256": file_sha256(raw_path),
        "execution": execution,
        "new_model_call_count": sum(
            row["new_model_call_count"] for row in execution.values()
        ),
        "production_memory_write_count": sum(
            row["production_memory_write_count"] for row in rows
        ),
        "physical_vrm_action_count": sum(
            row["physical_vrm_action_count"] for row in rows
        ),
    }
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return metadata


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434/api/chat")
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    args = parser.parse_args()
    prereg = load_json(PREREG_PATH)
    verify_frozen_scope(prereg, args.endpoint)
    rows, execution = run_screen(prereg, args.endpoint)
    metadata = write_outputs(rows, execution, prereg, args.raw, args.metadata, args.endpoint)
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
