#!/usr/bin/env python3
"""Run the frozen V2.2 9B evidence-extractor capacity screen once."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from run_source_preserving_memory_projection_v2_1_development import (
    ROOT,
    call_evidence_model,
    file_sha256,
    git_value,
    installed_models,
    load_json,
    phase_1_passes,
    phase_rows,
)


CONTRACT = ROOT / "configs/source_preserving_memory_projection_v2_2_model_capacity_evaluation_contract.json"
DEFAULT_RAW = ROOT / "analysis/local_source_preserving_memory_projection_v2_2_9b_capacity/raw.jsonl"
DEFAULT_METADATA = ROOT / "analysis/local_source_preserving_memory_projection_v2_2_9b_capacity/run_metadata.json"


def load_frozen_configuration():
    contract = load_json(CONTRACT)
    prereg = load_json(ROOT / contract["artifacts"]["preregistration"]["path"])
    base = load_json(ROOT / "configs/source_preserving_memory_projection_v2_development_preregistration.json")
    execution = {
        **prereg["independent_variable"]["intervention"],
        "model_digest": prereg["independent_variable"]["intervention"]["digest"],
        **{
            key: prereg["controlled_variables"][key]
            for key in ("endpoint", "temperature", "think", "seed", "num_ctx", "max_tokens")
        },
    }
    execution.pop("digest", None)
    runtime = {
        "experiment_id": prereg["experiment_id"],
        "matched_conditions": base["matched_conditions"],
        "span_gate": execution,
        "staged_execution": {
            "phase_1_conditions": prereg["controlled_variables"]["conditions"],
            "phase_1_representations": prereg["controlled_variables"]["representations"],
            "phase_1_call_count": prereg["controlled_variables"]["call_count"],
            "phase_1_continue_only_if": {
                "projected_target_only_supported_count_at_least": prereg["success_gates"][
                    "projected_target_support_count_at_least"
                ],
                "projected_hard_negative_supported_count_equals": prereg["success_gates"][
                    "projected_hard_negative_false_support_count_equals"
                ],
                "transport_error_count_equals": prereg["success_gates"][
                    "transport_error_count_equals"
                ],
            },
        },
    }
    return contract, prereg, runtime


def verify_frozen_inputs(contract, prereg, endpoint):
    for artifact in contract["artifacts"].values():
        if file_sha256(ROOT / artifact["path"]) != artifact["sha256"]:
            raise ValueError(f"frozen artifact hash mismatch: {artifact['path']}")
    if endpoint != prereg["controlled_variables"]["endpoint"]:
        raise ValueError("Ollama endpoint drift")
    intervention = prereg["independent_variable"]["intervention"]
    matched = next(
        (row for row in installed_models(endpoint) if row.get("name") == intervention["model"]),
        None,
    )
    if not matched:
        raise ValueError(f"missing local model: {intervention['model']}")
    if matched.get("digest") != intervention["digest"]:
        raise ValueError("local model digest mismatch")


def run_screen(cases, runtime, endpoint, model_call=None):
    rows = phase_rows(
        cases,
        runtime["staged_execution"]["phase_1_conditions"],
        runtime["staged_execution"]["phase_1_representations"],
        runtime,
        endpoint,
        model_call or call_evidence_model,
    )
    for row in rows:
        row["experiment_id"] = runtime["experiment_id"]
    return rows, phase_1_passes(rows, runtime)


def write_outputs(rows, passed, prereg, raw_path, metadata_path, endpoint):
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    intervention = prereg["independent_variable"]["intervention"]
    metadata = {
        "schema": "uruha_source_preserving_memory_projection_model_capacity_metadata_v2_2",
        "experiment_id": prereg["experiment_id"],
        "run_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_value("rev-parse", "HEAD"),
        "git_status_short": git_value("status", "--short"),
        "endpoint": endpoint,
        "model": intervention["model"],
        "model_digest": intervention["digest"],
        "phase_1_passed": passed,
        "row_count": len(rows),
        "raw_path": str(raw_path.relative_to(ROOT)),
        "raw_sha256": file_sha256(raw_path),
        "production_memory_write_count": sum(row["production_memory_write_count"] for row in rows),
        "physical_vrm_action_count": sum(row["physical_vrm_action_count"] for row in rows),
    }
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
    if args.raw.exists() or args.metadata.exists():
        raise SystemExit("Frozen V2.2 run output already exists; refusing to rerun")
    contract, prereg, runtime = load_frozen_configuration()
    verify_frozen_inputs(contract, prereg, args.endpoint)
    cases = load_json(ROOT / contract["artifacts"]["cases"]["path"])["cases"]
    rows, passed = run_screen(cases, runtime, args.endpoint)
    metadata = write_outputs(rows, passed, prereg, args.raw, args.metadata, args.endpoint)
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
