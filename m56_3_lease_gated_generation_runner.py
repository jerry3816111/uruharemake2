#!/usr/bin/env python3
"""M56.3 lease-gated, no-retry formal generation runner.

The formal entry point accepts only a run id.  A separate M56.2 activation
controller must already have consumed a valid receipt and created the lease.
This module never opens the scoring compartment and never accepts outcomes,
readiness, provider injection, or retry overrides.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import inspect
import json
import math
import os
from pathlib import Path
import platform
import resource
import subprocess
import time
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest

import m55_temporal_row_contract as temporal_m55
import m56_2_real_data_activation_envelope as activation_m56
import m56_blinded_execution_capsule as capsule_m56
import m56_fair_comparison_preflight as preflight_m56


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/m56_3_lease_gated_generation_runner_v1.json"
PRIVATE_ROOT = activation_m56.DEFAULT_PRIVATE_ROOT

SCHEDULE_SCHEMA = "uruha_m56_formal_generation_schedule_v1"
SUBMISSION_SCHEMA = "uruha_m56_formal_prediction_submission_v1"
COMMITMENT_SCHEMA = "uruha_m56_formal_prediction_commitment_v1"
SCORING_RELEASE_SCHEMA = "uruha_m56_post_commit_scoring_release_v1"
FAILURE_SCHEMA = "uruha_m56_terminal_generation_failure_v1"
AUDIT_SCHEMA = "uruha_m56_lease_gated_runner_audit_v1"
REHEARSAL_SCHEMA = "uruha_m56_generation_runner_synthetic_rehearsal_v1"
SUMMARY_SCHEMA = "uruha_m56_formal_b4_summary_artifact_v1"
CALL_SCHEMA = "uruha_m56_formal_model_call_telemetry_v1"

SCHEDULE_FILENAME = "formal_generation_schedule.json"
SUBMISSION_FILENAME = "formal_prediction_submission.json"
COMMITMENT_FILENAME = "formal_prediction_commitment.json"
SCORING_RELEASE_FILENAME = "post_commit_scoring_release.json"
CALL_LEDGER_FILENAME = "formal_call_ledger.json"
FAILURE_FILENAME = "terminal_generation_failure.json"

FORBIDDEN_OUTCOME_KEYS = set(capsule_m56.OUTCOME_KEYS) | {
    "target_outcome",
    "target_behavior",
    "private_outcome_key",
}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return sha256(canonical(value).encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    return sha256(Path(path).read_bytes()).hexdigest()


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_contract(path: str | Path = CONTRACT_PATH) -> dict[str, Any]:
    return load_json(path)


def _binding_valid(binding: Any) -> bool:
    if not isinstance(binding, dict):
        return False
    path = Path(str(binding.get("path") or ""))
    if not path.is_absolute():
        path = ROOT / path
    expected = str(binding.get("sha256") or "")
    return path.is_file() and len(expected) == 64 and sha256_file(path) == expected


def _find_keys(value: Any, forbidden: set[str], prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{prefix}.{key}" if prefix else str(key)
            if key in forbidden:
                found.append(child_path)
            found.extend(_find_keys(child, forbidden, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_find_keys(child, forbidden, f"{prefix}[{index}]"))
    return found


def validate_contract(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors: list[str] = []
    if contract.get("schema") != "uruha_m56_lease_gated_generation_runner_contract_v1":
        errors.append("schema")
    if contract.get("version") != "1.0.0":
        errors.append("version")
    if contract.get("status") != "frozen_before_any_formal_m56_generation_call_or_target_outcome_access":
        errors.append("status")
    bindings = contract.get("bindings")
    if not isinstance(bindings, dict) or len(bindings) != 6:
        errors.append("bindings")
    else:
        errors.extend(f"binding:{name}" for name, row in bindings.items() if not _binding_valid(row))
    if contract.get("schemas") != {
        "generation_schedule": SCHEDULE_SCHEMA,
        "formal_submission": SUBMISSION_SCHEMA,
        "prediction_commitment": COMMITMENT_SCHEMA,
        "scoring_release": SCORING_RELEASE_SCHEMA,
        "failure_record": FAILURE_SCHEMA,
        "runner_audit": AUDIT_SCHEMA,
        "synthetic_rehearsal": REHEARSAL_SCHEMA,
    }:
        errors.append("schemas")
    expected_states = [
        "activation_receipt_issued",
        "execution_lease_consumed",
        "schedule_committed",
        "b4_summaries_complete",
        "all_predictions_complete",
        "resource_ledger_complete",
        "submission_committed",
        "scoring_release_issued",
    ]
    if contract.get("state_machine") != expected_states:
        errors.append("state_machine")
    execution = contract.get("execution") or {}
    expected_execution = {
        "endpoint": "http://127.0.0.1:11434/api/generate",
        "provider": "local_ollama",
        "model": "qwen3.5:9b",
        "summary_tasks_before_prediction_tasks": True,
        "prediction_task_count": 210,
        "model_prediction_calls_per_non_B0_task": 1,
        "model_prediction_calls_per_B0_task": 0,
        "model_summary_calls_per_distinct_nonempty_history": 1,
        "transport_attempts_per_call": 1,
        "retry_count": 0,
        "fallback_count": 0,
        "public_provider_injection_allowed": False,
        "public_readiness_injection_allowed": False,
        "public_outcome_input_allowed": False,
        "public_retry_override_allowed": False,
        "terminal_failure_prevents_commitment": True,
    }
    if execution != expected_execution:
        errors.append("execution")
    boundary = contract.get("generation_boundary") or {}
    if boundary.get("permitted_compartments") != ["generation", "commitments", "telemetry"]:
        errors.append("boundary.compartments")
    if boundary.get("scoring_compartment_access_allowed") is not False:
        errors.append("boundary.scoring")
    if boundary.get("target_outcome_access_before_commitment") != 0:
        errors.append("boundary.outcome")
    if boundary.get("outcome_named_keys_forbidden") is not True:
        errors.append("boundary.outcome_keys")
    prompt = contract.get("prompt_and_output") or {}
    if prompt.get("input_token_budget") != 8192 or prompt.get("output_token_budget") != 384:
        errors.append("prompt.token_budget")
    if prompt.get("strict_json_only") is not True or prompt.get("raw_model_response_persisted") is not False:
        errors.append("prompt.output_boundary")
    commitment = contract.get("commitment") or {}
    if not all(commitment.get(name) is True for name in (
        "complete_matrix_required", "atomic_submission_write", "sha256_commitment_before_scoring_release",
        "post_commit_mutation_invalidates_release",
    )):
        errors.append("commitment.required")
    if any(commitment.get(name) is not False for name in (
        "scoring_release_authorizes_result_claim", "scoring_release_authorizes_production",
        "scoring_release_authorizes_retry",
    )):
        errors.append("commitment.excess_authority")
    authorization = contract.get("authorization") or {}
    if any(authorization.get(name) is not False for name in authorization):
        errors.append("authorization.current")
    return {
        "valid": not errors,
        "errors": errors,
        "contract_hash": digest(contract),
        "binding_count": len(bindings or {}),
    }


def _atomic_write_json(path: Path, value: dict[str, Any], *, exclusive: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if exclusive:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        fd = os.open(path, flags, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return
    temp = path.with_name(path.name + f".tmp-{os.getpid()}")
    with temp.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed.astimezone(timezone.utc)


def _run_root(run_id: str) -> Path:
    if not isinstance(run_id, str) or not run_id or run_id in (".", "..") or "/" in run_id or "\\" in run_id:
        raise ValueError("run_id must be one safe path component")
    root = (PRIVATE_ROOT / run_id).resolve()
    if root.parent != PRIVATE_ROOT.resolve():
        raise ValueError("run root escapes private root")
    return root


def _permitted_paths(run_id: str) -> dict[str, Path]:
    root = _run_root(run_id)
    return {
        "root": root,
        "generation": root / "generation",
        "commitments": root / "commitments",
        "telemetry": root / "telemetry",
    }


def _validate_consumed_receipt_and_lease(
    request_row: dict[str, Any], receipt: dict[str, Any], lease: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    expected_request_fields = {
        "schema", "version", "status", "run_id", "contract_hash", "dependency_set_hash",
        "dataset_hash", "prediction_packet_hash", "outcome_key_hash", "split_report_hash",
        "run_manifest_hash", "capsule_hash", "equation_artifact_bundle_hash",
        "runtime_snapshot_hash", "private_layout_hash", "sample_count", "condition_count",
        "generation_target_outcome_access_count", "model_calls_before_activation",
        "formal_execution_authorized", "formal_scoring_authorized", "activation_request_hash",
    }
    if set(request_row) != expected_request_fields:
        errors.append("request.fields")
    request_unhashed = {key: value for key, value in request_row.items() if key != "activation_request_hash"}
    if request_row.get("activation_request_hash") != digest(request_unhashed):
        errors.append("request.hash")
    expected_receipt_fields = {
        "schema", "version", "status", "run_id", "activation_request_hash",
        "runtime_snapshot_hash", "equation_artifact_bundle_hash", "execution_nonce",
        "issued_at", "expires_at", "consumed_at", "formal_generation_authorized",
        "formal_scoring_authorized", "formal_result_claim_authorized",
        "production_memory_write_authorized", "external_deployment_authorized",
        "retry_or_fallback_authorized", "generation_target_outcome_access_count", "receipt_hash",
    }
    if set(receipt) != expected_receipt_fields:
        errors.append("receipt.fields")
    receipt_unhashed = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    if receipt.get("schema") != activation_m56.RECEIPT_SCHEMA or receipt.get("status") != "consumed":
        errors.append("receipt.state")
    if receipt.get("receipt_hash") != digest(receipt_unhashed):
        errors.append("receipt.hash")
    if receipt.get("activation_request_hash") != request_row.get("activation_request_hash"):
        errors.append("receipt.request_hash")
    if receipt.get("runtime_snapshot_hash") != request_row.get("runtime_snapshot_hash"):
        errors.append("receipt.runtime_hash")
    if receipt.get("equation_artifact_bundle_hash") != request_row.get("equation_artifact_bundle_hash"):
        errors.append("receipt.bundle_hash")
    if receipt.get("formal_generation_authorized") is not True:
        errors.append("receipt.generation_authority")
    if any(receipt.get(name) is not False for name in (
        "formal_scoring_authorized", "formal_result_claim_authorized",
        "production_memory_write_authorized", "external_deployment_authorized",
        "retry_or_fallback_authorized",
    )):
        errors.append("receipt.excess_authority")
    try:
        issued = _parse_time(str(receipt.get("issued_at") or ""))
        expires = _parse_time(str(receipt.get("expires_at") or ""))
        consumed = _parse_time(str(receipt.get("consumed_at") or ""))
        if (expires - issued).total_seconds() != int(activation_m56.load_contract()["receipt"]["ttl_seconds"]):
            errors.append("receipt.ttl")
        if not issued <= consumed <= expires:
            errors.append("receipt.consume_time")
    except (TypeError, ValueError):
        errors.append("receipt.time")
    expected_lease_fields = {
        "schema", "version", "status", "run_id", "consumed_receipt_hash",
        "activation_request_hash", "execution_nonce_hash", "started_at",
        "formal_generation_authorized", "formal_scoring_authorized",
        "retry_or_fallback_authorized", "generation_target_outcome_access_count", "lease_hash",
    }
    if set(lease) != expected_lease_fields:
        errors.append("lease.fields")
    if lease.get("schema") != activation_m56.LEASE_SCHEMA or lease.get("status") != "single_formal_generation_run_in_progress":
        errors.append("lease.state")
    lease_unhashed = {key: value for key, value in lease.items() if key != "lease_hash"}
    if lease.get("lease_hash") != digest(lease_unhashed):
        errors.append("lease.hash")
    if lease.get("consumed_receipt_hash") != receipt.get("receipt_hash"):
        errors.append("lease.receipt_hash")
    if lease.get("activation_request_hash") != request_row.get("activation_request_hash"):
        errors.append("lease.request_hash")
    nonce = str(receipt.get("execution_nonce") or "")
    if lease.get("execution_nonce_hash") != sha256(nonce.encode("utf-8")).hexdigest():
        errors.append("lease.nonce")
    if lease.get("started_at") != receipt.get("consumed_at"):
        errors.append("lease.started_at")
    if lease.get("formal_generation_authorized") is not True:
        errors.append("lease.generation_authority")
    if lease.get("formal_scoring_authorized") is not False or lease.get("retry_or_fallback_authorized") is not False:
        errors.append("lease.excess_authority")
    if lease.get("generation_target_outcome_access_count") != 0:
        errors.append("lease.outcome_access")
    return errors


def load_permitted_runner_inputs(run_id: str) -> dict[str, dict[str, Any]]:
    """Load only generation, commitments, and telemetry-side metadata.

    This function deliberately has no scoring path and never lists the run root.
    """

    paths = _permitted_paths(run_id)
    for name in ("generation", "commitments", "telemetry"):
        if not paths[name].is_dir():
            raise FileNotFoundError(f"missing permitted compartment: {name}")
    generation = paths["generation"]
    commitments = paths["commitments"]
    return {
        "request": load_json(commitments / "activation_request.json"),
        "receipt": load_json(commitments / activation_m56.FORMAL_RECEIPT_FILENAME),
        "lease": load_json(commitments / activation_m56.FORMAL_LEASE_FILENAME),
        "packet": load_json(generation / "prediction_packet.json"),
        "manifest": load_json(generation / "run_manifest.json"),
        "capsule": load_json(generation / "execution_capsule.json"),
        "bundle": load_json(generation / "equation_artifacts.json"),
        "snapshot": load_json(generation / "runtime_snapshot.json"),
    }


def validate_runner_inputs(run_id: str, rows: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    errors: list[str] = []
    contract_report = validate_contract()
    errors.extend(f"contract:{name}" for name in contract_report["errors"])
    try:
        rows = deepcopy(rows or load_permitted_runner_inputs(run_id))
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        return {"valid": False, "errors": errors + [f"inputs:{exc}"]}
    request_row = rows["request"]
    receipt = rows["receipt"]
    lease = rows["lease"]
    packet = rows["packet"]
    manifest = rows["manifest"]
    capsule = rows["capsule"]
    bundle = rows["bundle"]
    snapshot = rows["snapshot"]
    errors.extend(_validate_consumed_receipt_and_lease(request_row, receipt, lease))
    errors.extend(f"packet:{name}" for name in preflight_m56.validate_prediction_packet(packet)["errors"])
    errors.extend(f"manifest:{name}" for name in preflight_m56.validate_run_manifest(manifest, packet)["errors"])
    errors.extend(f"capsule:{name}" for name in activation_m56.validate_formal_capsule(capsule, packet, manifest)["errors"])
    errors.extend(f"bundle:{name}" for name in activation_m56.validate_formal_artifact_bundle(bundle, packet, capsule, manifest)["errors"])
    errors.extend(f"runtime:{name}" for name in activation_m56.validate_runtime_snapshot(snapshot, compare_live=True)["errors"])
    for field, actual in (
        ("prediction_packet_hash", digest(packet)),
        ("run_manifest_hash", digest(manifest)),
        ("capsule_hash", capsule.get("capsule_hash")),
        ("equation_artifact_bundle_hash", bundle.get("artifact_bundle_hash")),
        ("runtime_snapshot_hash", snapshot.get("runtime_snapshot_hash")),
    ):
        if request_row.get(field) != actual:
            errors.append(f"request.{field}")
    activation_audit = activation_m56.build_live_activation_audit()
    if request_row.get("contract_hash") != activation_m56.validate_contract()["contract_hash"]:
        errors.append("request.contract_hash")
    if request_row.get("dependency_set_hash") != activation_audit["dependency_set_hash"]:
        errors.append("request.dependency_set_hash")
    if request_row.get("run_id") != run_id or lease.get("run_id") != run_id or receipt.get("run_id") != run_id:
        errors.append("run_id")
    forbidden = []
    for name in ("request", "receipt", "lease", "packet", "manifest", "capsule", "bundle", "snapshot"):
        forbidden.extend(f"{name}:{key}" for key in _find_keys(rows[name], FORBIDDEN_OUTCOME_KEYS))
    errors.extend(f"forbidden:{name}" for name in forbidden)
    return {
        "valid": not errors,
        "errors": errors,
        "lease_hash": lease.get("lease_hash"),
        "packet_hash": digest(packet),
        "capsule_hash": capsule.get("capsule_hash"),
        "bundle_hash": bundle.get("artifact_bundle_hash"),
        "generation_target_outcome_access_count": 0,
    }


def _artifact_hashes_by_sample(bundle: dict[str, Any]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for row in bundle.get("sample_artifacts") or []:
        result[str(row["sample_id"])] = {
            "fit_artifact_hash": row["fit_artifact"]["fit_artifact_hash"],
            "state_snapshot_hash": row["state_snapshot"]["state_snapshot_hash"],
            "transition_trace_hash": row["transition_trace"]["transition_trace_hash"],
        }
    return result


def build_generation_schedule(
    packet: dict[str, Any], manifest: dict[str, Any], capsule: dict[str, Any],
    bundle: dict[str, Any], lease_hash: str,
) -> dict[str, Any]:
    errors = []
    errors.extend(activation_m56.validate_formal_capsule(capsule, packet, manifest)["errors"])
    errors.extend(activation_m56.validate_formal_artifact_bundle(bundle, packet, capsule, manifest)["errors"])
    if errors:
        raise ValueError("formal mechanics invalid: " + "; ".join(errors))
    if not isinstance(lease_hash, str) or len(lease_hash) != 64:
        raise ValueError("lease hash required")
    artifact_hashes = _artifact_hashes_by_sample(bundle)
    summary_steps = [
        {
            "phase": "b4_summary",
            "step_index": index,
            "step_id": row["summary_task_id"],
            "model_call_required": bool(row["model_call_required"]),
            "source_hash": row["summary_view_hash"],
        }
        for index, row in enumerate(capsule["summary_tasks"])
    ]
    prediction_steps = []
    offset = len(summary_steps)
    for index, task in enumerate(capsule["prediction_tasks"]):
        condition = task["condition_id"]
        prediction_steps.append({
            "phase": "prediction",
            "step_index": offset + index,
            "step_id": task["task_id"],
            "sample_id": task["sample_id"],
            "condition_id": condition,
            "model_call_required": condition != "B0_PRIOR",
            "source_hash": task["view_hash"],
            "equation_artifact_hashes": artifact_hashes[task["sample_id"]] if condition == capsule_m56.PRIMARY_SYSTEM else None,
        })
    schedule = {
        "schema": SCHEDULE_SCHEMA,
        "version": "1.0.0",
        "status": "formal_schedule_bound_to_consumed_lease_not_yet_executed",
        "data_kind": packet["data_kind"],
        "runner_contract_hash": validate_contract()["contract_hash"],
        "activation_contract_hash": capsule["activation_contract_hash"],
        "lease_hash": lease_hash,
        "dataset_hash": packet["dataset_hash"],
        "prediction_packet_hash": digest(packet),
        "run_manifest_hash": digest(manifest),
        "capsule_hash": capsule["capsule_hash"],
        "equation_artifact_bundle_hash": bundle["artifact_bundle_hash"],
        "summary_steps": summary_steps,
        "prediction_steps": prediction_steps,
        "prediction_task_count": len(prediction_steps),
        "required_model_call_count": sum(int(row["model_call_required"]) for row in summary_steps + prediction_steps),
        "retry_count": 0,
        "fallback_count": 0,
        "generation_target_outcome_access_count": 0,
        "formal_result_authorized": False,
    }
    schedule["schedule_hash"] = digest(schedule)
    report = validate_generation_schedule(schedule, packet, manifest, capsule, bundle, lease_hash)
    if not report["valid"]:
        raise ValueError("schedule invalid: " + "; ".join(report["errors"]))
    return schedule


def validate_generation_schedule(
    schedule: dict[str, Any], packet: dict[str, Any], manifest: dict[str, Any],
    capsule: dict[str, Any], bundle: dict[str, Any], lease_hash: str,
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        expected_fields = {
            "schema", "version", "status", "data_kind", "runner_contract_hash",
            "activation_contract_hash", "lease_hash", "dataset_hash", "prediction_packet_hash",
            "run_manifest_hash", "capsule_hash", "equation_artifact_bundle_hash", "summary_steps",
            "prediction_steps", "prediction_task_count", "required_model_call_count", "retry_count",
            "fallback_count", "generation_target_outcome_access_count", "formal_result_authorized",
            "schedule_hash",
        }
        if set(schedule) != expected_fields:
            errors.append("schedule.fields")
        if schedule.get("schema") != SCHEDULE_SCHEMA or schedule.get("version") != "1.0.0":
            errors.append("schedule.schema_or_version")
        if schedule.get("status") != "formal_schedule_bound_to_consumed_lease_not_yet_executed":
            errors.append("schedule.status")
        if schedule.get("data_kind") != temporal_m55.REAL_KIND:
            errors.append("schedule.data_kind")
        if schedule.get("runner_contract_hash") != validate_contract()["contract_hash"]:
            errors.append("schedule.runner_contract_hash")
        if schedule.get("activation_contract_hash") != capsule.get("activation_contract_hash"):
            errors.append("schedule.activation_contract_hash")
        expected = deepcopy(schedule)
        expected.pop("schedule_hash", None)
        if schedule.get("schedule_hash") != digest(expected):
            errors.append("schedule.hash")
        expected_summary_ids = [row["summary_task_id"] for row in capsule["summary_tasks"]]
        expected_task_ids = [row["task_id"] for row in capsule["prediction_tasks"]]
        if [row.get("step_id") for row in schedule.get("summary_steps") or []] != expected_summary_ids:
            errors.append("schedule.summary_order")
        if [row.get("step_id") for row in schedule.get("prediction_steps") or []] != expected_task_ids:
            errors.append("schedule.prediction_order")
        if schedule.get("prediction_task_count") != 210 or len(expected_task_ids) != 210:
            errors.append("schedule.task_count")
        expected_model_calls = sum(int(row["model_call_required"]) for row in schedule["summary_steps"] + schedule["prediction_steps"])
        if schedule.get("required_model_call_count") != expected_model_calls:
            errors.append("schedule.model_calls")
        bindings = {
            "lease_hash": lease_hash,
            "dataset_hash": packet.get("dataset_hash"),
            "prediction_packet_hash": digest(packet),
            "run_manifest_hash": digest(manifest),
            "capsule_hash": capsule.get("capsule_hash"),
            "equation_artifact_bundle_hash": bundle.get("artifact_bundle_hash"),
        }
        for name, value in bindings.items():
            if schedule.get(name) != value:
                errors.append(f"schedule.{name}")
        if schedule.get("retry_count") != 0 or schedule.get("fallback_count") != 0:
            errors.append("schedule.retry_or_fallback")
        if schedule.get("generation_target_outcome_access_count") != 0:
            errors.append("schedule.outcome_access")
        if schedule.get("formal_result_authorized") is not False:
            errors.append("schedule.formal_result")
        forbidden = _find_keys(schedule, FORBIDDEN_OUTCOME_KEYS)
        errors.extend(f"schedule.forbidden:{name}" for name in forbidden)
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"schedule.structure:{exc}")
    return {
        "valid": not errors,
        "errors": errors,
        "summary_step_count": len(schedule.get("summary_steps") or []),
        "prediction_task_count": len(schedule.get("prediction_steps") or []),
        "schedule_hash": schedule.get("schedule_hash"),
    }


def _authorized_evidence_ids(task: dict[str, Any], summary_by_id: dict[str, dict[str, Any]]) -> set[str]:
    view = task["view"]
    condition = task["condition_id"]
    if condition == "B3_RAG":
        return {str(row["history_id"]) for row in view["deterministic_top4_pre_cutoff_history"]}
    if condition == "B4_FULL_HISTORY_SUMMARY":
        return set(summary_by_id[view["summary_task_id"]]["source_history_ids"])
    if condition in (capsule_m56.PRIMARY_CONTROL, capsule_m56.PRIMARY_SYSTEM):
        return {str(row["history_id"]) for row in view["source_information"]["all_pre_cutoff_history"]}
    return set()


def _artifact_row(bundle: dict[str, Any], sample_id: str) -> dict[str, Any]:
    row = next((item for item in bundle["sample_artifacts"] if item["sample_id"] == sample_id), None)
    if row is None:
        raise KeyError(f"missing Equation artifacts for {sample_id}")
    return row


def _prediction_payload(task: dict[str, Any], summary_by_id: dict[str, dict[str, Any]], bundle: dict[str, Any]) -> dict[str, Any]:
    view = deepcopy(task["view"])
    condition = task["condition_id"]
    if condition == "B4_FULL_HISTORY_SUMMARY":
        sid = str(view.pop("summary_task_id"))
        view.pop("summary_artifact_hash_required", None)
        summary = summary_by_id[sid]
        view["frozen_model_summary_artifact"] = {
            "summary_text": summary["summary_text"],
            "summary_artifact_hash": summary["summary_artifact_hash"],
        }
    if condition == capsule_m56.PRIMARY_SYSTEM:
        artifact = _artifact_row(bundle, task["sample_id"])
        view["pre_outcome_equation_artifacts"] = {
            "fit_artifact": deepcopy(artifact["fit_artifact"]),
            "state_snapshot": deepcopy(artifact["state_snapshot"]),
            "transition_trace": deepcopy(artifact["transition_trace"]),
        }
    return view


def build_summary_prompt(task: dict[str, Any]) -> dict[str, Any]:
    if task.get("empty_history_artifact"):
        raise ValueError("empty history must not call the model")
    payload = {
        "instruction": "Summarize only the observable pre-cutoff history. Do not infer private mental states. Return JSON only.",
        "source_history": deepcopy(task["source_history"]),
        "output_schema": {"summary_text": "string"},
    }
    prompt = canonical(payload)
    return {"prompt": prompt, "prompt_hash": sha256(prompt.encode("utf-8")).hexdigest()}


def build_prediction_prompt(
    task: dict[str, Any], summary_by_id: dict[str, dict[str, Any]], bundle: dict[str, Any]
) -> dict[str, Any]:
    if task["condition_id"] == "B0_PRIOR":
        raise ValueError("B0 must not create a model prompt")
    labels = task["view"]["candidate_behavior_labels"]
    payload = {
        "instruction": (
            "Predict the next observable behavior category from only the authorized pre-cutoff view. "
            "Return JSON only. Probabilities must cover every label and sum to 1. "
            "authorized_evidence_ids may contain only history_id values visible in this view. "
            "Do not output hidden reasoning or private mental facts."
        ),
        "condition_id": task["condition_id"],
        "authorized_view": _prediction_payload(task, summary_by_id, bundle),
        "output_schema": {
            "probabilities": {label: "number" for label in labels},
            "authorized_evidence_ids": ["history_id"],
            "brief_evidence": "string_max_500",
        },
    }
    prompt = canonical(payload)
    return {"prompt": prompt, "prompt_hash": sha256(prompt.encode("utf-8")).hexdigest()}


def _prediction_json_schema(labels: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["probabilities", "authorized_evidence_ids", "brief_evidence"],
        "properties": {
            "probabilities": {
                "type": "object",
                "additionalProperties": False,
                "required": labels,
                "properties": {label: {"type": "number", "minimum": 0, "maximum": 1} for label in labels},
            },
            "authorized_evidence_ids": {"type": "array", "items": {"type": "string"}},
            "brief_evidence": {"type": "string", "maxLength": 500},
        },
    }


def _summary_json_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["summary_text"],
        "properties": {"summary_text": {"type": "string", "maxLength": 2000}},
    }


def _process_peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if platform.system() == "Darwin" else value * 1024


def _ollama_rss_bytes() -> int:
    try:
        output = subprocess.run(
            ["ps", "-axo", "rss=,command="], check=True, capture_output=True, text=True, timeout=5
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return 0
    rows = []
    for line in output.splitlines():
        if "ollama" not in line.lower():
            continue
        first = line.strip().split(maxsplit=1)[0]
        if first.isdigit():
            rows.append(int(first) * 1024)
    return sum(rows)


def _ollama_generate(prompt: str, output_schema: dict[str, Any], options: dict[str, Any]) -> dict[str, Any]:
    """Perform exactly one transport attempt against the frozen local endpoint."""

    contract = load_contract()
    endpoint = contract["execution"]["endpoint"]
    body = {
        "model": contract["execution"]["model"],
        "prompt": prompt,
        "stream": False,
        "format": output_schema,
        "options": deepcopy(options),
        "think": False,
    }
    encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
    started_wall = time.perf_counter()
    started_cpu = time.process_time()
    try:
        with urlrequest.urlopen(
            urlrequest.Request(endpoint, data=encoded, headers={"Content-Type": "application/json"}),
            timeout=300,
        ) as response:
            response_body = json.loads(response.read().decode("utf-8"))
    except (urlerror.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"single Ollama transport attempt failed: {type(exc).__name__}") from exc
    latency = time.perf_counter() - started_wall
    cpu = time.process_time() - started_cpu
    raw = response_body.get("response")
    if not isinstance(raw, str):
        raise ValueError("Ollama response text missing")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("single model response is not strict JSON") from exc
    return {
        "parsed": parsed,
        "raw_response_hash": sha256(raw.encode("utf-8")).hexdigest(),
        "prompt_tokens": response_body.get("prompt_eval_count"),
        "completion_tokens": response_body.get("eval_count"),
        "latency_seconds": latency,
        "process_cpu_seconds": cpu,
        "process_peak_rss_bytes": _process_peak_rss_bytes(),
        "ollama_rss_bytes": _ollama_rss_bytes(),
        "total_duration_ns": response_body.get("total_duration"),
        "load_duration_ns": response_body.get("load_duration"),
        "prompt_eval_duration_ns": response_body.get("prompt_eval_duration"),
        "eval_duration_ns": response_body.get("eval_duration"),
        "model_reported": response_body.get("model"),
        "transport_attempt_count": 1,
        "retry_count": 0,
        "fallback_count": 0,
    }


def _validate_call_resources(call: dict[str, Any], *, input_budget: int, output_budget: int) -> list[str]:
    errors: list[str] = []
    for name in ("prompt_tokens", "completion_tokens", "process_peak_rss_bytes", "ollama_rss_bytes"):
        if not isinstance(call.get(name), int) or call[name] < 0:
            errors.append(f"resource.{name}")
    for name in ("latency_seconds", "process_cpu_seconds"):
        value = call.get(name)
        if not isinstance(value, (int, float)) or not math.isfinite(float(value)) or value < 0:
            errors.append(f"resource.{name}")
    for name in ("total_duration_ns", "load_duration_ns", "prompt_eval_duration_ns", "eval_duration_ns"):
        if not isinstance(call.get(name), int) or call[name] < 0:
            errors.append(f"resource.{name}")
    if call.get("prompt_tokens", input_budget + 1) > input_budget:
        errors.append("resource.input_token_budget")
    if call.get("completion_tokens", output_budget + 1) > output_budget:
        errors.append("resource.output_token_budget")
    if call.get("transport_attempt_count") != 1 or call.get("retry_count") != 0 or call.get("fallback_count") != 0:
        errors.append("resource.retry_or_fallback")
    if max(int(call.get("process_peak_rss_bytes") or 0), int(call.get("ollama_rss_bytes") or 0)) <= 0:
        errors.append("resource.memory_observation")
    if len(str(call.get("raw_response_hash") or "")) != 64:
        errors.append("resource.raw_response_hash")
    return errors


def _validate_model_identity(call: dict[str, Any], expected_model: str) -> None:
    if call.get("model_reported") != expected_model:
        raise ValueError("Ollama model identity drift")


def _argmax(probabilities: dict[str, float], labels: list[str]) -> str:
    return max(labels, key=lambda label: (float(probabilities[label]), -labels.index(label)))


def _validate_prediction_output(
    parsed: Any, labels: list[str], authorized_ids: set[str]
) -> tuple[dict[str, float], list[str], str]:
    if not isinstance(parsed, dict) or set(parsed) != {"probabilities", "authorized_evidence_ids", "brief_evidence"}:
        raise ValueError("prediction output fields invalid")
    probabilities = parsed["probabilities"]
    if not isinstance(probabilities, dict) or set(probabilities) != set(labels):
        raise ValueError("probability labels invalid")
    normalized: dict[str, float] = {}
    for label in labels:
        value = probabilities[label]
        if not isinstance(value, (int, float)) or not math.isfinite(float(value)) or value < 0 or value > 1:
            raise ValueError("probability value invalid")
        normalized[label] = float(value)
    if abs(sum(normalized.values()) - 1.0) > 0.000001:
        raise ValueError("probability mass invalid")
    evidence = parsed["authorized_evidence_ids"]
    if not isinstance(evidence, list) or any(not isinstance(item, str) for item in evidence):
        raise ValueError("evidence ids invalid")
    if len(evidence) != len(set(evidence)) or set(evidence) - authorized_ids:
        raise ValueError("unauthorized evidence id")
    brief = parsed["brief_evidence"]
    if not isinstance(brief, str) or len(brief) > 500:
        raise ValueError("brief evidence invalid")
    return normalized, evidence, brief


def _deterministic_b0(task: dict[str, Any], run: dict[str, Any]) -> dict[str, Any]:
    labels = task["view"]["candidate_behavior_labels"]
    counts = task["view"]["pre_cutoff_historical_behavior_counts"]
    weights = {label: float(counts[label]) + 1.0 for label in labels}
    total = sum(weights.values())
    probabilities = {label: weights[label] / total for label in labels}
    return {
        "task_id": task["task_id"],
        "sample_id": task["sample_id"],
        "condition_id": task["condition_id"],
        "view_hash": task["view_hash"],
        "probabilities": probabilities,
        "selected_behavior": _argmax(probabilities, labels),
        "authorized_evidence_ids": [],
        "brief_evidence": "Deterministic Laplace-smoothed pre-cutoff prior.",
        "prompt_hash": None,
        "raw_response_hash": None,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "latency_seconds": 0.0,
        "process_cpu_seconds": 0.0,
        "process_peak_rss_bytes": 0,
        "ollama_rss_bytes": 0,
        "total_duration_ns": 0,
        "load_duration_ns": 0,
        "prompt_eval_duration_ns": 0,
        "eval_duration_ns": 0,
        "transport_attempt_count": 0,
        "prediction_model_call_count": 0,
        "semantic_model_call_count": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "model_name": run["model_name"],
        "model_artifact_digest": run["model_artifact_digest"],
        "hardware_fingerprint": run["hardware_fingerprint"],
        "provider_options": deepcopy(run["provider_options"]),
        "b4_summary_artifact_hash": None,
        "fit_artifact_hash": None,
        "state_snapshot_hash": None,
        "transition_trace_hash": None,
    }


def _formal_row_fields() -> set[str]:
    return {
        "task_id", "sample_id", "condition_id", "view_hash", "probabilities",
        "selected_behavior", "authorized_evidence_ids", "brief_evidence", "prompt_hash",
        "raw_response_hash", "prompt_tokens", "completion_tokens", "latency_seconds",
        "process_cpu_seconds", "process_peak_rss_bytes", "ollama_rss_bytes", "total_duration_ns",
        "load_duration_ns", "prompt_eval_duration_ns", "eval_duration_ns", "transport_attempt_count",
        "prediction_model_call_count", "semantic_model_call_count", "retry_count", "fallback_count",
        "model_name", "model_artifact_digest", "hardware_fingerprint", "provider_options",
        "b4_summary_artifact_hash", "fit_artifact_hash", "state_snapshot_hash", "transition_trace_hash",
    }


def build_formal_submission(
    schedule: dict[str, Any], packet: dict[str, Any], manifest: dict[str, Any], capsule: dict[str, Any],
    bundle: dict[str, Any], lease: dict[str, Any], summary_artifacts: list[dict[str, Any]],
    prediction_rows: list[dict[str, Any]], equation_artifact_cpu_seconds: float,
) -> dict[str, Any]:
    submission = {
        "schema": SUBMISSION_SCHEMA,
        "version": "1.0.0",
        "status": "formal_predictions_complete_pending_sha_commitment",
        "data_kind": temporal_m55.REAL_KIND,
        "runner_contract_hash": validate_contract()["contract_hash"],
        "activation_contract_hash": capsule["activation_contract_hash"],
        "lease_hash": lease["lease_hash"],
        "schedule_hash": schedule["schedule_hash"],
        "dataset_hash": packet["dataset_hash"],
        "prediction_packet_hash": digest(packet),
        "run_manifest_hash": digest(manifest),
        "capsule_hash": capsule["capsule_hash"],
        "equation_artifact_bundle_hash": bundle["artifact_bundle_hash"],
        "summary_artifacts": deepcopy(summary_artifacts),
        "prediction_rows": deepcopy(prediction_rows),
        "equation_artifact_rematerialization_cpu_seconds": equation_artifact_cpu_seconds,
        "outcome_access_count_before_commitment": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "formal_scoring_authorized": False,
        "formal_result_claim_authorized": False,
        "production_memory_write_authorized": False,
    }
    submission["submission_hash"] = digest(submission)
    report = validate_formal_submission(submission, schedule, packet, manifest, capsule, bundle, lease)
    if not report["valid"]:
        raise ValueError("formal submission invalid: " + "; ".join(report["errors"]))
    return submission


def validate_formal_submission(
    submission: dict[str, Any], schedule: dict[str, Any], packet: dict[str, Any], manifest: dict[str, Any],
    capsule: dict[str, Any], bundle: dict[str, Any], lease: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(submission, dict):
        return {"valid": False, "errors": ["submission.object"]}
    expected_submission_fields = {
        "schema", "version", "status", "data_kind", "runner_contract_hash",
        "activation_contract_hash", "lease_hash", "schedule_hash", "dataset_hash",
        "prediction_packet_hash", "run_manifest_hash", "capsule_hash",
        "equation_artifact_bundle_hash", "summary_artifacts", "prediction_rows",
        "equation_artifact_rematerialization_cpu_seconds", "outcome_access_count_before_commitment",
        "retry_count", "fallback_count", "formal_scoring_authorized",
        "formal_result_claim_authorized", "production_memory_write_authorized", "submission_hash",
    }
    if set(submission) != expected_submission_fields:
        errors.append("submission.fields")
    unhashed = {key: value for key, value in submission.items() if key != "submission_hash"}
    if submission.get("submission_hash") != digest(unhashed):
        errors.append("submission.hash")
    if submission.get("schema") != SUBMISSION_SCHEMA or submission.get("status") != "formal_predictions_complete_pending_sha_commitment":
        errors.append("submission.schema_or_status")
    for name, expected in (
        ("data_kind", temporal_m55.REAL_KIND),
        ("lease_hash", lease.get("lease_hash")),
        ("schedule_hash", schedule.get("schedule_hash")),
        ("dataset_hash", packet.get("dataset_hash")),
        ("prediction_packet_hash", digest(packet)),
        ("run_manifest_hash", digest(manifest)),
        ("capsule_hash", capsule.get("capsule_hash")),
        ("equation_artifact_bundle_hash", bundle.get("artifact_bundle_hash")),
    ):
        if submission.get(name) != expected:
            errors.append(f"submission.{name}")
    if submission.get("outcome_access_count_before_commitment") != 0:
        errors.append("submission.outcome_access")
    if submission.get("retry_count") != 0 or submission.get("fallback_count") != 0:
        errors.append("submission.retry_or_fallback")
    if any(submission.get(name) is not False for name in (
        "formal_scoring_authorized", "formal_result_claim_authorized", "production_memory_write_authorized",
    )):
        errors.append("submission.excess_authority")
    cpu = submission.get("equation_artifact_rematerialization_cpu_seconds")
    if not isinstance(cpu, (int, float)) or not math.isfinite(float(cpu)) or cpu < 0:
        errors.append("submission.equation_cpu")
    summary_tasks = {row["summary_task_id"]: row for row in capsule["summary_tasks"]}
    summary_rows = submission.get("summary_artifacts")
    if not isinstance(summary_rows, list):
        summary_rows = []
        errors.append("submission.summary_artifacts")
    summary_map: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(summary_rows):
        scope = f"summary[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{scope}.object")
            continue
        expected_summary_fields = {
            "schema", "summary_task_id", "summary_view_hash", "summary_text",
            "source_history_ids", "prompt_hash", "raw_response_hash", "model_call_count",
            "prompt_tokens", "completion_tokens", "latency_seconds", "process_cpu_seconds",
            "process_peak_rss_bytes", "ollama_rss_bytes", "total_duration_ns", "load_duration_ns",
            "prompt_eval_duration_ns", "eval_duration_ns", "transport_attempt_count",
            "retry_count", "fallback_count", "model_name", "model_artifact_digest",
            "hardware_fingerprint", "provider_options", "summary_artifact_hash",
        }
        if set(row) != expected_summary_fields:
            errors.append(f"{scope}.fields")
        sid = str(row.get("summary_task_id") or "")
        if sid in summary_map or sid not in summary_tasks:
            errors.append(f"{scope}.id")
        summary_map[sid] = row
        task = summary_tasks.get(sid) or {}
        if row.get("schema") != SUMMARY_SCHEMA or row.get("summary_view_hash") != task.get("summary_view_hash"):
            errors.append(f"{scope}.binding")
        if row.get("source_history_ids") != task.get("source_history_ids"):
            errors.append(f"{scope}.history_ids")
        if not isinstance(row.get("summary_text"), str) or len(row.get("summary_text", "")) > 2000:
            errors.append(f"{scope}.text")
        expected_calls = 0 if task.get("empty_history_artifact") else 1
        if row.get("model_call_count") != expected_calls:
            errors.append(f"{scope}.model_calls")
        if row.get("retry_count") != 0 or row.get("fallback_count") != 0:
            errors.append(f"{scope}.retry")
        if row.get("summary_artifact_hash") != digest({key: value for key, value in row.items() if key != "summary_artifact_hash"}):
            errors.append(f"{scope}.hash")
    if set(summary_map) != set(summary_tasks):
        errors.append("submission.summary_completeness")
    tasks = capsule["prediction_tasks"]
    task_map = {row["task_id"]: row for row in tasks}
    rows = submission.get("prediction_rows")
    if not isinstance(rows, list):
        rows = []
        errors.append("submission.prediction_rows")
    if [row.get("task_id") for row in rows if isinstance(row, dict)] != [row["task_id"] for row in tasks]:
        errors.append("submission.prediction_order")
    run_map = {row["condition_id"]: row for row in manifest["condition_runs"]}
    bundle_hashes = _artifact_hashes_by_sample(bundle)
    b5_tokens: dict[str, int] = {}
    ours_tokens: dict[str, int] = {}
    total_model_calls = sum(int(row.get("model_call_count") or 0) for row in summary_rows if isinstance(row, dict))
    for index, row in enumerate(rows):
        scope = f"prediction[{index}]"
        if not isinstance(row, dict) or set(row) != _formal_row_fields():
            errors.append(f"{scope}.fields")
            continue
        task = task_map.get(str(row.get("task_id") or ""))
        if not task:
            errors.append(f"{scope}.task")
            continue
        condition = task["condition_id"]
        if row.get("sample_id") != task["sample_id"] or row.get("condition_id") != condition or row.get("view_hash") != task["view_hash"]:
            errors.append(f"{scope}.binding")
        labels = task["view"]["candidate_behavior_labels"]
        try:
            probabilities, evidence, brief = _validate_prediction_output(
                {
                    "probabilities": row.get("probabilities"),
                    "authorized_evidence_ids": row.get("authorized_evidence_ids"),
                    "brief_evidence": row.get("brief_evidence"),
                },
                labels,
                _authorized_evidence_ids(task, summary_map),
            )
            if row.get("selected_behavior") != _argmax(probabilities, labels):
                errors.append(f"{scope}.argmax")
            del evidence, brief
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"{scope}.output:{exc}")
        run = run_map[condition]
        for name in ("model_name", "model_artifact_digest", "hardware_fingerprint", "provider_options"):
            if row.get(name) != run.get(name):
                errors.append(f"{scope}.{name}")
        if row.get("retry_count") != 0 or row.get("fallback_count") != 0:
            errors.append(f"{scope}.retry")
        if condition == "B0_PRIOR":
            expected = _deterministic_b0(task, run)
            if row != expected:
                errors.append(f"{scope}.B0")
        else:
            total_model_calls += 1
            errors.extend(f"{scope}.{name}" for name in _validate_call_resources(
                row, input_budget=int(run["input_token_budget"]), output_budget=int(run["output_token_budget"])
            ))
            expected_prediction_calls = 0 if condition == capsule_m56.PRIMARY_SYSTEM else 1
            expected_semantic_calls = 1 if condition == capsule_m56.PRIMARY_SYSTEM else 0
            if row.get("prediction_model_call_count") != expected_prediction_calls or row.get("semantic_model_call_count") != expected_semantic_calls:
                errors.append(f"{scope}.call_role")
            if condition == "B4_FULL_HISTORY_SUMMARY":
                sid = task["view"]["summary_task_id"]
                if row.get("b4_summary_artifact_hash") != (summary_map.get(sid) or {}).get("summary_artifact_hash"):
                    errors.append(f"{scope}.b4_summary")
            elif row.get("b4_summary_artifact_hash") is not None:
                errors.append(f"{scope}.unexpected_summary")
            if condition == capsule_m56.PRIMARY_SYSTEM:
                for name, expected in bundle_hashes[task["sample_id"]].items():
                    if row.get(name) != expected:
                        errors.append(f"{scope}.{name}")
                ours_tokens[task["sample_id"]] = int(row.get("prompt_tokens") or 0)
            else:
                if any(row.get(name) is not None for name in (
                    "fit_artifact_hash", "state_snapshot_hash", "transition_trace_hash",
                )):
                    errors.append(f"{scope}.equation_leak")
            if condition == capsule_m56.PRIMARY_CONTROL:
                b5_tokens[task["sample_id"]] = int(row.get("prompt_tokens") or 0)
    if total_model_calls != schedule.get("required_model_call_count"):
        errors.append("submission.total_model_calls")
    max_difference = 0.0
    for sample_id in sorted(set(b5_tokens) | set(ours_tokens)):
        b5 = b5_tokens.get(sample_id, 0)
        ours = ours_tokens.get(sample_id, 0)
        max_difference = max(max_difference, abs(ours - b5) / max(b5, ours, 1))
    forbidden = _find_keys(submission, FORBIDDEN_OUTCOME_KEYS)
    errors.extend(f"submission.forbidden:{name}" for name in forbidden)
    return {
        "valid": not errors,
        "errors": errors,
        "row_count": len(rows),
        "summary_count": len(summary_rows),
        "model_call_count": total_model_calls,
        "max_primary_prompt_token_difference_fraction": max_difference,
        "exact_token_sensitivity_required": max_difference > 0.05,
        "submission_hash": submission.get("submission_hash"),
    }


def build_prediction_commitment(
    submission: dict[str, Any], schedule: dict[str, Any], lease: dict[str, Any], validation: dict[str, Any]
) -> dict[str, Any]:
    if not validation.get("valid"):
        raise ValueError("invalid submission cannot be committed")
    value = {
        "schema": COMMITMENT_SCHEMA,
        "version": "1.0.0",
        "status": "complete_formal_prediction_matrix_sha256_committed",
        "lease_hash": lease["lease_hash"],
        "schedule_hash": schedule["schedule_hash"],
        "submission_hash": submission["submission_hash"],
        "submission_validation_hash": digest(validation),
        "committed_prediction_task_ids": [row["task_id"] for row in submission["prediction_rows"]],
        "committed_prediction_row_count": len(submission["prediction_rows"]),
        "committed_summary_artifact_hashes": [row["summary_artifact_hash"] for row in submission["summary_artifacts"]],
        "model_call_count": validation["model_call_count"],
        "outcome_access_count_at_commitment": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "formal_result_claim_authorized": False,
        "production_memory_write_authorized": False,
    }
    value["commitment_hash"] = digest(value)
    return value


def validate_prediction_commitment(
    commitment: dict[str, Any], submission: dict[str, Any], schedule: dict[str, Any], lease: dict[str, Any],
    submission_validation: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    expected_fields = {
        "schema", "version", "status", "lease_hash", "schedule_hash", "submission_hash",
        "submission_validation_hash", "committed_prediction_task_ids",
        "committed_prediction_row_count", "committed_summary_artifact_hashes", "model_call_count",
        "outcome_access_count_at_commitment", "retry_count", "fallback_count",
        "formal_result_claim_authorized", "production_memory_write_authorized", "commitment_hash",
    }
    if set(commitment) != expected_fields:
        errors.append("commitment.fields")
    unhashed = {key: value for key, value in commitment.items() if key != "commitment_hash"}
    if commitment.get("commitment_hash") != digest(unhashed):
        errors.append("commitment.hash")
    if commitment.get("schema") != COMMITMENT_SCHEMA or commitment.get("status") != "complete_formal_prediction_matrix_sha256_committed":
        errors.append("commitment.schema_or_status")
    for name, expected in (
        ("lease_hash", lease.get("lease_hash")),
        ("schedule_hash", schedule.get("schedule_hash")),
        ("submission_hash", submission.get("submission_hash")),
    ):
        if commitment.get(name) != expected:
            errors.append(f"commitment.{name}")
    if not submission_validation.get("valid"):
        errors.append("commitment.submission_invalid")
    if commitment.get("submission_validation_hash") != digest(submission_validation):
        errors.append("commitment.submission_validation_hash")
    if commitment.get("committed_prediction_task_ids") != [row["task_id"] for row in submission.get("prediction_rows") or []]:
        errors.append("commitment.tasks")
    if commitment.get("committed_prediction_row_count") != 210:
        errors.append("commitment.row_count")
    if commitment.get("outcome_access_count_at_commitment") != 0:
        errors.append("commitment.outcome_access")
    if commitment.get("retry_count") != 0 or commitment.get("fallback_count") != 0:
        errors.append("commitment.retry")
    if commitment.get("formal_result_claim_authorized") is not False or commitment.get("production_memory_write_authorized") is not False:
        errors.append("commitment.excess_authority")
    return {"valid": not errors, "errors": errors, "commitment_hash": commitment.get("commitment_hash")}


def build_scoring_release(
    commitment: dict[str, Any], submission: dict[str, Any], schedule: dict[str, Any], lease: dict[str, Any],
    submission_validation: dict[str, Any],
) -> dict[str, Any]:
    report = validate_prediction_commitment(
        commitment, submission, schedule, lease, submission_validation
    )
    if not report["valid"]:
        raise ValueError("scoring release requires a valid complete commitment")
    value = {
        "schema": SCORING_RELEASE_SCHEMA,
        "version": "1.0.0",
        "status": "separate_scorer_may_begin_after_complete_commitment",
        "lease_hash": lease["lease_hash"],
        "schedule_hash": schedule["schedule_hash"],
        "submission_hash": submission["submission_hash"],
        "commitment_hash": commitment["commitment_hash"],
        "scoring_compartment_read_allowed_by_separate_scorer": True,
        "generation_target_outcome_access_allowed": False,
        "formal_result_claim_authorized": False,
        "production_memory_write_authorized": False,
        "external_deployment_authorized": False,
        "retry_or_fallback_authorized": False,
    }
    value["release_hash"] = digest(value)
    return value


def validate_scoring_release(
    release: dict[str, Any], commitment: dict[str, Any], submission: dict[str, Any],
    schedule: dict[str, Any], lease: dict[str, Any], submission_validation: dict[str, Any],
) -> dict[str, Any]:
    errors = validate_prediction_commitment(
        commitment, submission, schedule, lease, submission_validation
    )["errors"]
    expected_fields = {
        "schema", "version", "status", "lease_hash", "schedule_hash", "submission_hash",
        "commitment_hash", "scoring_compartment_read_allowed_by_separate_scorer",
        "generation_target_outcome_access_allowed", "formal_result_claim_authorized",
        "production_memory_write_authorized", "external_deployment_authorized",
        "retry_or_fallback_authorized", "release_hash",
    }
    if set(release) != expected_fields:
        errors.append("release.fields")
    unhashed = {key: value for key, value in release.items() if key != "release_hash"}
    if release.get("release_hash") != digest(unhashed):
        errors.append("release.hash")
    if release.get("schema") != SCORING_RELEASE_SCHEMA or release.get("status") != "separate_scorer_may_begin_after_complete_commitment":
        errors.append("release.schema_or_status")
    for name, expected in (
        ("lease_hash", lease.get("lease_hash")),
        ("schedule_hash", schedule.get("schedule_hash")),
        ("submission_hash", submission.get("submission_hash")),
        ("commitment_hash", commitment.get("commitment_hash")),
    ):
        if release.get(name) != expected:
            errors.append(f"release.{name}")
    if release.get("scoring_compartment_read_allowed_by_separate_scorer") is not True:
        errors.append("release.scorer")
    if release.get("generation_target_outcome_access_allowed") is not False:
        errors.append("release.generation_outcome")
    if any(release.get(name) is not False for name in (
        "formal_result_claim_authorized", "production_memory_write_authorized",
        "external_deployment_authorized", "retry_or_fallback_authorized",
    )):
        errors.append("release.excess_authority")
    return {"valid": not errors, "errors": errors, "release_hash": release.get("release_hash")}


def _empty_summary_artifact(task: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    value = {
        "schema": SUMMARY_SCHEMA,
        "summary_task_id": task["summary_task_id"],
        "summary_view_hash": task["summary_view_hash"],
        "summary_text": "No pre-cutoff history available.",
        "source_history_ids": deepcopy(task["source_history_ids"]),
        "prompt_hash": None,
        "raw_response_hash": None,
        "model_call_count": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "latency_seconds": 0.0,
        "process_cpu_seconds": 0.0,
        "process_peak_rss_bytes": 0,
        "ollama_rss_bytes": 0,
        "total_duration_ns": 0,
        "load_duration_ns": 0,
        "prompt_eval_duration_ns": 0,
        "eval_duration_ns": 0,
        "transport_attempt_count": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "model_name": "deterministic_no_history",
        "model_artifact_digest": "deterministic_no_history",
        "hardware_fingerprint": snapshot["hardware_fingerprint"],
        "provider_options": {},
    }
    value["summary_artifact_hash"] = digest(value)
    return value


def _summary_artifact(task: dict[str, Any], call: dict[str, Any], run: dict[str, Any]) -> dict[str, Any]:
    parsed = call["parsed"]
    if not isinstance(parsed, dict) or set(parsed) != {"summary_text"}:
        raise ValueError("summary output fields invalid")
    summary_text = parsed["summary_text"]
    if not isinstance(summary_text, str) or len(summary_text) > 2000:
        raise ValueError("summary text invalid")
    value = {
        "schema": SUMMARY_SCHEMA,
        "summary_task_id": task["summary_task_id"],
        "summary_view_hash": task["summary_view_hash"],
        "summary_text": summary_text,
        "source_history_ids": deepcopy(task["source_history_ids"]),
        "prompt_hash": call["prompt_hash"],
        "raw_response_hash": call["raw_response_hash"],
        "model_call_count": 1,
        "prompt_tokens": call["prompt_tokens"],
        "completion_tokens": call["completion_tokens"],
        "latency_seconds": call["latency_seconds"],
        "process_cpu_seconds": call["process_cpu_seconds"],
        "process_peak_rss_bytes": call["process_peak_rss_bytes"],
        "ollama_rss_bytes": call["ollama_rss_bytes"],
        "total_duration_ns": call["total_duration_ns"],
        "load_duration_ns": call["load_duration_ns"],
        "prompt_eval_duration_ns": call["prompt_eval_duration_ns"],
        "eval_duration_ns": call["eval_duration_ns"],
        "transport_attempt_count": 1,
        "retry_count": 0,
        "fallback_count": 0,
        "model_name": run["model_name"],
        "model_artifact_digest": run["model_artifact_digest"],
        "hardware_fingerprint": run["hardware_fingerprint"],
        "provider_options": deepcopy(run["provider_options"]),
    }
    value["summary_artifact_hash"] = digest(value)
    return value


def _prediction_row(
    task: dict[str, Any], call: dict[str, Any], run: dict[str, Any],
    summary_by_id: dict[str, dict[str, Any]], bundle: dict[str, Any],
) -> dict[str, Any]:
    labels = task["view"]["candidate_behavior_labels"]
    probabilities, evidence, brief = _validate_prediction_output(
        call["parsed"], labels, _authorized_evidence_ids(task, summary_by_id)
    )
    condition = task["condition_id"]
    hashes = _artifact_hashes_by_sample(bundle).get(task["sample_id"], {})
    row = {
        "task_id": task["task_id"],
        "sample_id": task["sample_id"],
        "condition_id": condition,
        "view_hash": task["view_hash"],
        "probabilities": probabilities,
        "selected_behavior": _argmax(probabilities, labels),
        "authorized_evidence_ids": evidence,
        "brief_evidence": brief,
        "prompt_hash": call["prompt_hash"],
        "raw_response_hash": call["raw_response_hash"],
        "prompt_tokens": call["prompt_tokens"],
        "completion_tokens": call["completion_tokens"],
        "latency_seconds": call["latency_seconds"],
        "process_cpu_seconds": call["process_cpu_seconds"],
        "process_peak_rss_bytes": call["process_peak_rss_bytes"],
        "ollama_rss_bytes": call["ollama_rss_bytes"],
        "total_duration_ns": call["total_duration_ns"],
        "load_duration_ns": call["load_duration_ns"],
        "prompt_eval_duration_ns": call["prompt_eval_duration_ns"],
        "eval_duration_ns": call["eval_duration_ns"],
        "transport_attempt_count": 1,
        "prediction_model_call_count": 0 if condition == capsule_m56.PRIMARY_SYSTEM else 1,
        "semantic_model_call_count": 1 if condition == capsule_m56.PRIMARY_SYSTEM else 0,
        "retry_count": 0,
        "fallback_count": 0,
        "model_name": run["model_name"],
        "model_artifact_digest": run["model_artifact_digest"],
        "hardware_fingerprint": run["hardware_fingerprint"],
        "provider_options": deepcopy(run["provider_options"]),
        "b4_summary_artifact_hash": summary_by_id[task["view"]["summary_task_id"]]["summary_artifact_hash"] if condition == "B4_FULL_HISTORY_SUMMARY" else None,
        "fit_artifact_hash": hashes.get("fit_artifact_hash") if condition == capsule_m56.PRIMARY_SYSTEM else None,
        "state_snapshot_hash": hashes.get("state_snapshot_hash") if condition == capsule_m56.PRIMARY_SYSTEM else None,
        "transition_trace_hash": hashes.get("transition_trace_hash") if condition == capsule_m56.PRIMARY_SYSTEM else None,
    }
    return row


def _terminal_failure(paths: dict[str, Path], lease_hash: str | None, phase: str, exc: Exception) -> None:
    value = {
        "schema": FAILURE_SCHEMA,
        "version": "1.0.0",
        "status": "terminal_no_retry_generation_failure",
        "lease_hash": lease_hash,
        "phase": phase,
        "error_type": type(exc).__name__,
        "error_message_digest": sha256(str(exc).encode("utf-8")).hexdigest(),
        "retry_authorized": False,
        "fallback_authorized": False,
        "commitment_created": False,
        "scoring_release_created": False,
        "generation_target_outcome_access_count": 0,
    }
    value["failure_hash"] = digest(value)
    try:
        _atomic_write_json(paths["telemetry"] / FAILURE_FILENAME, value, exclusive=True)
    except FileExistsError:
        pass


def execute_formal_generation(run_id: str) -> dict[str, Any]:
    """Execute one already-leased formal run. No injectable provider or outcomes."""

    paths = _permitted_paths(run_id)
    phase = "input_validation"
    lease_hash: str | None = None
    try:
        rows = load_permitted_runner_inputs(run_id)
        validation = validate_runner_inputs(run_id, rows)
        if not validation["valid"]:
            raise PermissionError("runner inputs invalid: " + "; ".join(validation["errors"]))
        lease = rows["lease"]
        lease_hash = lease["lease_hash"]
        for path in (
            paths["generation"] / SCHEDULE_FILENAME,
            paths["generation"] / SUBMISSION_FILENAME,
            paths["commitments"] / COMMITMENT_FILENAME,
            paths["commitments"] / SCORING_RELEASE_FILENAME,
            paths["telemetry"] / CALL_LEDGER_FILENAME,
            paths["telemetry"] / FAILURE_FILENAME,
        ):
            if path.exists():
                raise FileExistsError("formal lease already attempted; retry is forbidden")
        packet, manifest = rows["packet"], rows["manifest"]
        capsule, bundle, snapshot = rows["capsule"], rows["bundle"], rows["snapshot"]
        phase = "schedule_commitment"
        schedule = build_generation_schedule(packet, manifest, capsule, bundle, lease_hash)
        _atomic_write_json(paths["generation"] / SCHEDULE_FILENAME, schedule, exclusive=True)
        phase = "equation_artifact_rematerialization"
        cpu_started = time.process_time()
        rebuilt = activation_m56.build_formal_artifact_bundle(packet, capsule, manifest)
        equation_cpu = time.process_time() - cpu_started
        if rebuilt != bundle:
            raise ValueError("Equation artifact rematerialization drift")
        run_map = {row["condition_id"]: row for row in manifest["condition_runs"]}
        phase = "b4_summaries"
        summaries: list[dict[str, Any]] = []
        calls: list[dict[str, Any]] = []
        for task in capsule["summary_tasks"]:
            if task["empty_history_artifact"]:
                summaries.append(_empty_summary_artifact(task, snapshot))
                continue
            prompt = build_summary_prompt(task)
            call = _ollama_generate(prompt["prompt"], _summary_json_schema(), run_map["B4_FULL_HISTORY_SUMMARY"]["provider_options"])
            call["prompt_hash"] = prompt["prompt_hash"]
            resource_errors = _validate_call_resources(
                call,
                input_budget=int(run_map["B4_FULL_HISTORY_SUMMARY"]["input_token_budget"]),
                output_budget=int(run_map["B4_FULL_HISTORY_SUMMARY"]["output_token_budget"]),
            )
            if resource_errors:
                raise ValueError("summary resource gate failed: " + "; ".join(resource_errors))
            _validate_model_identity(call, run_map["B4_FULL_HISTORY_SUMMARY"]["model_name"])
            artifact = _summary_artifact(task, call, run_map["B4_FULL_HISTORY_SUMMARY"])
            summaries.append(artifact)
            calls.append({
                "schema": CALL_SCHEMA,
                "phase": "b4_summary",
                "step_id": task["summary_task_id"],
                **{key: value for key, value in call.items() if key != "parsed"},
            })
        summary_by_id = {row["summary_task_id"]: row for row in summaries}
        phase = "predictions"
        predictions: list[dict[str, Any]] = []
        for task in capsule["prediction_tasks"]:
            condition = task["condition_id"]
            run = run_map[condition]
            if condition == "B0_PRIOR":
                predictions.append(_deterministic_b0(task, run))
                continue
            prompt = build_prediction_prompt(task, summary_by_id, bundle)
            call = _ollama_generate(prompt["prompt"], _prediction_json_schema(task["view"]["candidate_behavior_labels"]), run["provider_options"])
            call["prompt_hash"] = prompt["prompt_hash"]
            resource_errors = _validate_call_resources(
                call, input_budget=int(run["input_token_budget"]), output_budget=int(run["output_token_budget"])
            )
            if resource_errors:
                raise ValueError("prediction resource gate failed: " + "; ".join(resource_errors))
            _validate_model_identity(call, run["model_name"])
            predictions.append(_prediction_row(task, call, run, summary_by_id, bundle))
            calls.append({
                "schema": CALL_SCHEMA,
                "phase": "prediction",
                "step_id": task["task_id"],
                **{key: value for key, value in call.items() if key != "parsed"},
            })
        phase = "submission_validation"
        submission = build_formal_submission(
            schedule, packet, manifest, capsule, bundle, lease, summaries, predictions, equation_cpu
        )
        submission_report = validate_formal_submission(submission, schedule, packet, manifest, capsule, bundle, lease)
        ledger = {
            "schema": "uruha_m56_formal_call_ledger_v1",
            "version": "1.0.0",
            "status": "complete_before_prediction_commitment",
            "lease_hash": lease_hash,
            "schedule_hash": schedule["schedule_hash"],
            "call_count": len(calls),
            "required_call_count": schedule["required_model_call_count"],
            "calls": calls,
            "equation_artifact_rematerialization_cpu_seconds": equation_cpu,
            "retry_count": 0,
            "fallback_count": 0,
            "generation_target_outcome_access_count": 0,
        }
        ledger["ledger_hash"] = digest(ledger)
        _atomic_write_json(paths["generation"] / SUBMISSION_FILENAME, submission, exclusive=True)
        _atomic_write_json(paths["telemetry"] / CALL_LEDGER_FILENAME, ledger, exclusive=True)
        phase = "prediction_commitment"
        commitment = build_prediction_commitment(submission, schedule, lease, submission_report)
        _atomic_write_json(paths["commitments"] / COMMITMENT_FILENAME, commitment, exclusive=True)
        phase = "scoring_release"
        release = build_scoring_release(
            commitment, submission, schedule, lease, submission_report
        )
        _atomic_write_json(paths["commitments"] / SCORING_RELEASE_FILENAME, release, exclusive=True)
        return {
            "status": "formal_generation_complete_scoring_released",
            "submission_hash": submission["submission_hash"],
            "commitment_hash": commitment["commitment_hash"],
            "scoring_release_hash": release["release_hash"],
            "model_call_count": len(calls),
            "generation_target_outcome_access_count": 0,
            "formal_result_claim_authorized": False,
        }
    except Exception as exc:
        if paths["telemetry"].is_dir():
            _terminal_failure(paths, lease_hash, phase, exc)
        raise


def build_synthetic_rehearsal() -> dict[str, Any]:
    packet, manifest, capsule = __import__("m56_pre_outcome_equation_artifacts").build_demo_packet()
    summary_count = len(capsule["summary_tasks"])
    prediction_count = len(capsule["prediction_tasks"])
    value = {
        "schema": REHEARSAL_SCHEMA,
        "version": "1.0.0",
        "status": "synthetic_no_call_state_machine_rehearsal_only",
        "data_kind": packet["data_kind"],
        "runner_contract_hash": validate_contract()["contract_hash"],
        "state_order": deepcopy(load_contract()["state_machine"]),
        "summary_step_count": summary_count,
        "prediction_step_count": prediction_count,
        "model_calls": 0,
        "formal_lease_created": False,
        "formal_commitment_created": False,
        "scoring_release_created": False,
        "human_evidence_count": 0,
        "target_outcome_access_count": 0,
        "formal_execution_authorized": False,
        "claim_boundary": "no-call wiring rehearsal only; cannot become a formal lease, commitment, score, or result",
    }
    value["rehearsal_hash"] = digest(value)
    return value


def build_live_audit() -> dict[str, Any]:
    contract_report = validate_contract()
    activation = activation_m56.build_live_activation_audit()
    signature = inspect.signature(execute_formal_generation)
    value = {
        "schema": AUDIT_SCHEMA,
        "version": "1.0.0",
        "status": "formal_generation_denied_waiting_for_human_chain",
        "runner_contract_valid": contract_report["valid"],
        "runner_contract_hash": contract_report["contract_hash"],
        "activation_audit_hash": activation["audit_hash"],
        "public_execution_parameters": list(signature.parameters),
        "public_provider_or_readiness_or_outcome_injection": any(
            name in signature.parameters for name in ("provider", "readiness", "outcome", "retry", "fallback")
        ),
        "gates": deepcopy(activation["gates"]),
        "counts": deepcopy(activation["counts"]),
        "formal_generation_authorized": False,
        "formal_model_calls": 0,
        "formal_commitment_created": False,
        "formal_scoring_release_created": False,
        "generation_target_outcome_access_count": 0,
        "formal_result_created": False,
        "claim_boundary": load_contract()["claim_boundary"],
    }
    value["audit_hash"] = digest(value)
    return value


def build_live_report() -> dict[str, Any]:
    return {
        "schema": "uruha_m56_lease_gated_generation_runner_live_report_v1",
        "audit": build_live_audit(),
        "synthetic_rehearsal": build_synthetic_rehearsal(),
    }


def render_dashboard(report: dict[str, Any] | None = None) -> str:
    report = deepcopy(report or build_live_report())
    audit = report["audit"]
    counts = audit["counts"]
    stages = [
        ("1", "M56.2 lease", "真人 gate 通過後，receipt 只能消耗一次", False),
        ("2", "凍結 schedule", "B4 summaries 先跑；之後 30 × 7 tasks", True),
        ("3", "no-retry generation", "每個模型 task 只准一次 transport attempt", True),
        ("4", "actual resources", "tokens、latency、CPU、memory、Ollama durations", True),
        ("5", "SHA commitment", "210 筆完整、順序正確才可 commit", True),
        ("6", "separate scorer", "commit 後才取得讀 scoring 分艙的能力", True),
    ]
    cards = "".join(
        f'<article class="stage {"waiting" if not ready else "ready"}"><span>{n}</span><h3>{html.escape(title)}</h3><p>{html.escape(text)}</p></article>'
        for n, title, text, ready in stages
    )
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M56.3 Lease-Gated Generation Runner</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#07111f;color:#eef5ff;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}main{{max-width:1280px;margin:auto;padding:30px}}.hero,.panel{{border:1px solid #304968;border-radius:22px;padding:24px;margin-bottom:18px;background:#101c2e}}.hero{{background:linear-gradient(135deg,#173149,#2b1932)}}.status{{display:inline-block;padding:7px 11px;border-radius:999px;background:#571a2e;color:#ffc0ce;font-weight:800}}h1{{font-size:clamp(30px,5vw,48px);margin:.35em 0}}h2{{margin-top:0}}p{{line-height:1.55}}.pink{{color:#ff9db4;font-weight:800;font-size:20px}}.flow{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}.stage{{border:1px solid #34506e;border-radius:16px;padding:16px;min-height:135px;background:#091527}}.stage span{{display:grid;place-items:center;width:30px;height:30px;border-radius:50%;background:#24566b;color:#78ead5;font-weight:900}}.stage.waiting{{border-color:#a64d66}}.stage.waiting span{{background:#5d2134;color:#ffc0ce}}.stage h3{{margin:12px 0 6px}}.stage p{{margin:0;color:#c5d4e7}}.split{{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:14px}}.box{{border:1px solid #365575;border-radius:18px;padding:22px;text-align:center;background:#081426}}.wall{{font-size:42px;color:#ff829e}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}}.metric{{padding:16px;background:#081426;border:1px solid #334d6c;border-radius:14px}}.metric strong{{display:block;font-size:24px;color:#77e4cf}}.boundary{{border-left:5px solid #ff7e99}}.hash{{font-family:ui-monospace,monospace;word-break:break-all;color:#9fc4eb}}@media(max-width:800px){{.flow,.metrics,.split{{grid-template-columns:1fr}}.wall{{transform:rotate(90deg);text-align:center}}}}</style></head><body><main>
<section class="hero"><span class="status">M56.3 FORMAL GENERATION · DENIED NOW</span><h1>正式模型不是按下「跑」：它是一條不能跳步的狀態機</h1><p class="pink">目前真人證據仍是 {counts['v7_slots_by_ledger'][0]}/18 + {counts['v7_slots_by_ledger'][1]}/18，所以 lease 不存在、正式呼叫 0、commitment 0。</p><p>M56.3 只補齊未來通過 gate 後的真實執行與資源記錄；現在不會偷跑模型，也不會把 rehearsal 當結果。</p></section>
<section class="panel"><h2>六步缺一不可</h2><div class="flow">{cards}</div></section>
<section class="panel"><h2>生成端與答案端之間有硬邊界</h2><div class="split"><div class="box"><b>GENERATION</b><p>lease、schedule、authorized views、Equation artifacts、tokens/CPU/memory</p></div><div class="wall">║</div><div class="box"><b>SCORING · PRIVATE</b><p>outcome key 不會被 generation 開啟；只有完整 SHA commitment 後，獨立 scorer 才能讀</p></div></div></section>
<section class="panel"><h2>現在的 authoritative 數字</h2><div class="metrics"><div class="metric"><strong>{counts['v9_independently_reviewed_events']}/30</strong>V9 events</div><div class="metric"><strong>{counts['real_temporal_rows']}/30</strong>real rows</div><div class="metric"><strong>0</strong>formal calls</div><div class="metric"><strong>0</strong>formal result</div></div></section>
<section class="panel boundary"><h2>證據邊界</h2><p>這一頁證明 runner 的 gate、順序、分艙與資源欄位已可檢查，不證明模型比較、Equation V1、人類方程式或 production。</p><p class="hash">audit SHA-256 · {html.escape(audit['audit_hash'])}</p></section>
</main></body></html>"""


def serve_demo(port: int) -> None:
    page = render_dashboard().encode("utf-8")
    status = json.dumps(build_live_report(), ensure_ascii=False, indent=2).encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path in ("/", "/dashboard"):
                body, content_type, code = page, "text/html; charset=utf-8", 200
            elif self.path == "/status.json":
                body, content_type, code = status, "application/json; charset=utf-8", 200
            elif self.path == "/health":
                body, content_type, code = b"ok", "text/plain; charset=utf-8", 200
            else:
                body, content_type, code = b"not found", "text/plain; charset=utf-8", 404
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args: Any) -> None:
            return

    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--port", type=int, default=7911)
    parser.add_argument("--format", choices=("json", "html"), default="json")
    args = parser.parse_args()
    if args.serve:
        serve_demo(args.port)
    elif args.format == "html":
        print(render_dashboard())
    else:
        print(json.dumps(build_live_report(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
