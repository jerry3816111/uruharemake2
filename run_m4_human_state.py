#!/usr/bin/env python3
"""Build and replay frozen M4 HumanState snapshots without state transition."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Mapping

from longitudinal_human_model.registry import (
    git_snapshot,
    load_json,
    runtime_snapshot,
    sha256_file,
    verify_lock,
    write_json_atomic,
)
from longitudinal_human_model.state import HumanStateSnapshot, REQUIRED_DIMENSIONS, build_human_state_snapshot


REPO_ROOT = Path(__file__).resolve().parent


def _materialize_estimate(raw: Mapping[str, Any], timestamp: str) -> dict[str, Any]:
    status = str(raw.get("status") or "inferred")
    if status == "unknown":
        value = None
        confidence = 0.0
        evidence_ids: list[str] = []
    else:
        value = raw.get("value")
        confidence = float(raw["confidence"])
        evidence_ids = [str(value) for value in raw.get("evidence_ids") or ()]
    return {
        "value": value,
        "confidence": confidence,
        "status": status,
        "evidence_ids": evidence_ids,
        "updated_at": timestamp,
        "hypothesis_note": str(raw.get("note") or raw.get("hypothesis_note") or "").strip(),
    }


def materialize_draft(raw: Mapping[str, Any]) -> dict[str, Any]:
    timestamp = str(raw["timestamp"])
    dimensions = {
        name: {
            str(key): _materialize_estimate(value, timestamp)
            for key, value in raw["dimensions"][name].items()
        }
        for name in REQUIRED_DIMENSIONS
    }
    relationships = {
        str(entity_id): {
            "entity_id": str(value["entity_id"]),
            "fields": {
                str(key): _materialize_estimate(estimate, timestamp)
                for key, estimate in value["fields"].items()
            },
        }
        for entity_id, value in raw["relationships"].items()
    }
    return {
        **{key: value for key, value in raw.items() if key not in {"dimensions", "relationships"}},
        "dimensions": dimensions,
        "relationships": relationships,
    }


def _m3_rows(result: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row["query_id"]): row for row in result["conditions"]["none"]["rows"]
    }


def validate_inputs(
    dataset: dict[str, Any],
    config: dict[str, Any],
    m3_dataset: dict[str, Any],
    m3_result: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    if dataset.get("formal_target_claim") is not False or config.get("formal_target_claim") is not False:
        errors.append("M4 fixture and config must explicitly refuse formal target claims")
    if config.get("state_transition_enabled") is not False:
        errors.append("M4 must not enable state transition")
    if config.get("behavior_predictor_enabled") is not False:
        errors.append("M4 must not enable a behavior predictor")
    if m3_result.get("status") != "complete_mechanism_run" or not m3_result.get("gate_pass"):
        errors.append("inherited M3 result is not a complete passing mechanism run")
    drafts = dataset.get("drafts")
    if not isinstance(drafts, list) or not drafts:
        errors.append("M4 fixture requires non-empty drafts")
        drafts = []
    m3_queries = {str(row["query_id"]): row for row in m3_dataset.get("queries") or []}
    m3_rows = _m3_rows(m3_result) if not errors else {}
    snapshots: list[HumanStateSnapshot] = []
    for index, raw in enumerate(drafts):
        try:
            draft = materialize_draft(raw)
            query_id = str(draft["current_event_id"])
            query = m3_queries.get(query_id)
            retrieval = m3_rows.get(query_id)
            if query is None or retrieval is None:
                raise ValueError(f"current_event_id {query_id} is absent from inherited M3")
            if draft["timestamp"] != query["prediction_time"]:
                raise ValueError("draft timestamp does not match M3 query prediction_time")
            if draft["available_history_cutoff"] != query["available_history_cutoff"]:
                raise ValueError("draft cutoff does not match M3 query cutoff")
            snapshot = build_human_state_snapshot(
                draft,
                retrieval,
                low_confidence_threshold=float(config["low_confidence_threshold"]),
            )
            snapshots.append(snapshot)
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"draft[{index}] invalid: {exc}")
    expected = int(config.get("success_contract", {}).get("snapshot_count") or -1)
    if len(drafts) != expected:
        errors.append("fixture draft count does not match success contract")
    return {
        "valid": not errors,
        "errors": errors,
        "draft_count": len(drafts),
        "snapshot_count": len(snapshots),
    }


def run_state_snapshots(
    dataset: dict[str, Any],
    config: dict[str, Any],
    m3_dataset: dict[str, Any],
    m3_result: dict[str, Any],
) -> dict[str, Any]:
    validation = validate_inputs(dataset, config, m3_dataset, m3_result)
    if not validation["valid"]:
        raise ValueError("invalid M4 inputs: " + "; ".join(validation["errors"]))
    rows = _m3_rows(m3_result)
    snapshots = []
    deterministic_ids = True
    replay_exact = True
    all_dimensions = True
    unknown_space = True
    future_evidence_count = 0
    unresolved_evidence_reference_count = 0
    for raw in dataset["drafts"]:
        draft = materialize_draft(raw)
        first = build_human_state_snapshot(
            draft,
            rows[draft["current_event_id"]],
            low_confidence_threshold=float(config["low_confidence_threshold"]),
        )
        second = build_human_state_snapshot(
            draft,
            rows[draft["current_event_id"]],
            low_confidence_threshold=float(config["low_confidence_threshold"]),
        )
        deterministic_ids = deterministic_ids and first.snapshot_id == second.snapshot_id
        serialized = first.to_dict()
        replay = HumanStateSnapshot.from_dict(serialized)
        replay_exact = replay_exact and replay.to_dict() == serialized
        all_dimensions = all_dimensions and all(bool(getattr(first, name)) for name in REQUIRED_DIMENSIONS)
        all_dimensions = all_dimensions and bool(first.relationships) and bool(first.memory_activations)
        unknown_space = unknown_space and bool(first.uncertainty.unknown_fields)
        evidence_ids = {item.evidence_id for item in first.evidence_catalog}
        for evidence in first.evidence_catalog:
            boundary = (
                first.available_history_cutoff
                if evidence.evidence_kind == "memory"
                else first.timestamp
            )
            future_evidence_count += int(evidence.available_at > boundary)
        for _, estimate in first.estimate_paths().items():
            unresolved_evidence_reference_count += len(set(estimate.evidence_ids) - evidence_ids)
        snapshots.append(serialized)
    contract = config["success_contract"]
    gates = {
        "snapshot_count": len(snapshots) == int(contract["snapshot_count"]),
        "deterministic_snapshot_ids": deterministic_ids
        is bool(contract["deterministic_snapshot_ids"]),
        "roundtrip_replay_exact": replay_exact is bool(contract["roundtrip_replay_exact"]),
        "all_required_dimensions_present": all_dimensions
        is bool(contract["all_required_dimensions_present"]),
        "each_snapshot_has_unknown_space": unknown_space
        is bool(contract["each_snapshot_has_unknown_space"]),
        "future_evidence_count": future_evidence_count == int(contract["future_evidence_count"]),
        "unresolved_evidence_reference_count": unresolved_evidence_reference_count
        == int(contract["unresolved_evidence_reference_count"]),
    }
    return {
        "schema": "ilhdt_m4_state_result_v1",
        "status": "complete_snapshot_run" if all(gates.values()) else "failed_snapshot_gate",
        "claim_level": config["claim_level"],
        "formal_target_claim": False,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "dataset_id": dataset["dataset_id"],
        "state_transition_enabled": False,
        "behavior_predictor_enabled": False,
        "validation": validation,
        "snapshots": snapshots,
        "gate_checks": gates,
        "gate_pass": all(gates.values()),
        "summary": {
            "snapshot_count": len(snapshots),
            "unique_snapshot_ids": len({item["snapshot_id"] for item in snapshots}),
            "unknown_field_count": sum(
                len(item["uncertainty"]["unknown_fields"]) for item in snapshots
            ),
            "low_confidence_field_count": sum(
                len(item["uncertainty"]["low_confidence_fields"]) for item in snapshots
            ),
            "memory_activation_count": sum(len(item["memory_activations"]) for item in snapshots),
            "future_evidence_count": future_evidence_count,
            "unresolved_evidence_reference_count": unresolved_evidence_reference_count,
        },
        "limitations": [
            "Both state drafts and confidence values are author-designed synthetic fixtures.",
            "Psychological labels are model variables, not private-state ground truth.",
            "M4 implements snapshots and replay only; it does not implement state transition.",
            "M4 does not test behavior prediction or language realization.",
            "No Uruha or real-person claim is authorized.",
        ],
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("validate", "run"), default="validate")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--lock", required=True)
    parser.add_argument("--output")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    dataset_path = (REPO_ROOT / args.dataset).resolve()
    config_path = (REPO_ROOT / args.config).resolve()
    lock_path = (REPO_ROOT / args.lock).resolve()
    dataset = load_json(dataset_path)
    config = load_json(config_path)
    lock = load_json(lock_path)
    m3_dataset_path = (REPO_ROOT / config["m3_dataset"]).resolve()
    m3_result_path = (REPO_ROOT / config["m3_result"]["path"]).resolve()
    m3_dataset = load_json(m3_dataset_path)
    m3_result = load_json(m3_result_path)
    input_validation = validate_inputs(dataset, config, m3_dataset, m3_result)
    lock_errors = verify_lock(lock, repo_root=REPO_ROOT)
    actual_m3_sha = sha256_file(m3_result_path)
    if actual_m3_sha != config["m3_result"]["sha256"]:
        lock_errors.append(
            f"M3 result hash mismatch: expected {config['m3_result']['sha256']}, got {actual_m3_sha}"
        )
    validation = {
        "schema": "ilhdt_m4_validation_v1",
        "valid": input_validation["valid"] and not lock_errors,
        "inputs": input_validation,
        "lock_errors": lock_errors,
        "dataset_sha256": sha256_file(dataset_path),
        "config_sha256": sha256_file(config_path),
        "m3_result_sha256": actual_m3_sha,
        "lock_sha256": sha256_file(lock_path),
    }
    if args.mode == "validate":
        print(json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if validation["valid"] else 2
    if not validation["valid"]:
        raise SystemExit("M4 frozen validation failed")
    if not args.output:
        raise SystemExit("--output is required in run mode")
    result = run_state_snapshots(dataset, config, m3_dataset, m3_result)
    result["experiment_lock"] = lock
    result["environment"] = runtime_snapshot()
    result["git"] = git_snapshot(REPO_ROOT)
    output_path = (REPO_ROOT / args.output).resolve()
    write_json_atomic(output_path, result)
    print(json.dumps({"output": str(output_path), "status": result["status"]}, indent=2))
    return 0 if result["gate_pass"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
