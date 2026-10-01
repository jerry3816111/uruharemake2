#!/usr/bin/env python3
"""M56.2 live-gated activation envelope for one future formal M56 run.

The module deliberately produces a denial on the current repository state.  It
never accepts caller-supplied readiness.  A formal activation can be prepared
only from the standard live V7/V9 evidence and an explicitly supplied private
30-row M55 compilation.  Synthetic rehearsal uses a different schema and can
never create a formal receipt.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import inspect
import json
import os
from pathlib import Path
import platform
import secrets
import subprocess
from typing import Any

import audit_m55_real_person_longitudinal_readiness as readiness_m55
import m55_temporal_row_contract as temporal_m55
import m56_blinded_execution_capsule as capsule_m56
import m56_fair_comparison_preflight as preflight_m56
import m56_pre_outcome_equation_artifacts as artifacts_m56


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/m56_2_real_data_activation_envelope_v1.json"
DEFAULT_PRIVATE_ROOT = ROOT / "analysis/local_m56_formal_execution_v1"

AUDIT_SCHEMA = "uruha_m56_real_data_activation_audit_v1"
REQUEST_SCHEMA = "uruha_m56_real_data_activation_request_v1"
RECEIPT_SCHEMA = "uruha_m56_real_data_activation_receipt_v1"
LEASE_SCHEMA = "uruha_m56_real_data_execution_lease_v1"
REHEARSAL_SCHEMA = "uruha_m56_synthetic_activation_rehearsal_v1"
FORMAL_CAPSULE_SCHEMA = "uruha_m56_private_real_execution_capsule_v1"
FORMAL_BUNDLE_SCHEMA = "uruha_m56_private_real_equation_artifact_bundle_v1"
FORMAL_MANIFEST_STATUS = "private_real_manifest_pending_activation"
FORMAL_CAPSULE_STATUS = "private_real_capsule_pending_activation"
FORMAL_BUNDLE_STATUS = "private_real_pre_outcome_artifacts_pending_activation"
FORMAL_RECEIPT_FILENAME = "activation_receipt.json"
FORMAL_LEASE_FILENAME = "execution_lease.json"
REQUIRED_LAYOUT_DIRS = ("generation", "commitments", "scoring", "telemetry")


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
    relative = str(binding.get("path") or "")
    expected = str(binding.get("sha256") or "")
    path = Path(relative)
    if not path.is_absolute():
        path = ROOT / path
    return bool(relative) and len(expected) == 64 and path.is_file() and sha256_file(path) == expected


def _find_keys(value: Any, forbidden: set[str], prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if key in forbidden:
                found.append(path)
            found.extend(_find_keys(child, forbidden, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_find_keys(child, forbidden, f"{prefix}[{index}]"))
    return found


def validate_contract(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors: list[str] = []
    if contract.get("schema") != "uruha_m56_real_data_activation_envelope_contract_v1":
        errors.append("schema")
    if contract.get("version") != "1.0.0":
        errors.append("version")
    if contract.get("status") != "frozen_before_any_real_m56_model_generation_or_target_outcome_access":
        errors.append("status")
    bindings = contract.get("bindings")
    if not isinstance(bindings, dict) or len(bindings) != 10:
        errors.append("bindings")
    else:
        for name, binding in bindings.items():
            if not _binding_valid(binding):
                errors.append(f"binding:{name}")
    schemas = contract.get("schemas") or {}
    if schemas != {
        "activation_audit": AUDIT_SCHEMA,
        "activation_request": REQUEST_SCHEMA,
        "activation_receipt": RECEIPT_SCHEMA,
        "execution_lease": LEASE_SCHEMA,
        "synthetic_rehearsal": REHEARSAL_SCHEMA,
    }:
        errors.append("schemas")
    gate = contract.get("live_gate") or {}
    if gate.get("required_data_kind") != temporal_m55.REAL_KIND:
        errors.append("live_gate.data_kind")
    for field, expected in (
        ("required_prediction_rows", 30),
        ("required_v7_human_ledgers", 2),
        ("required_v7_slots_per_ledger", 18),
        ("required_v9_independently_reviewed_events", 30),
        ("required_v9_human_coders", 2),
        ("future_leakage_violations", 0),
    ):
        if gate.get(field) != expected:
            errors.append(f"live_gate.{field}")
    if gate.get("caller_supplied_readiness_allowed") is not False:
        errors.append("live_gate.caller_readiness")
    layout = contract.get("private_layout") or {}
    if layout.get("root") != "analysis/local_m56_formal_execution_v1":
        errors.append("private_layout.root")
    if tuple(layout.get("required_directories") or []) != REQUIRED_LAYOUT_DIRS:
        errors.append("private_layout.directories")
    if layout.get("required_gitignored") is not True or layout.get("formal_artifacts_git_tracked") is not False:
        errors.append("private_layout.git_boundary")
    runtime = contract.get("runtime_snapshot") or {}
    if runtime.get("provider") != "local_ollama" or runtime.get("model_name") != "qwen3.5:9b":
        errors.append("runtime_snapshot.model")
    if runtime.get("model_calls_during_activation") != 0:
        errors.append("runtime_snapshot.model_calls")
    receipt = contract.get("receipt") or {}
    ttl = receipt.get("ttl_seconds")
    if not isinstance(ttl, int) or isinstance(ttl, bool) or ttl <= 0 or ttl > 3600:
        errors.append("receipt.ttl_seconds")
    if receipt.get("single_use") is not True or receipt.get("atomic_consumption_required") is not True:
        errors.append("receipt.single_use")
    if receipt.get("retry_or_fallback_allowed") is not False:
        errors.append("receipt.retry")
    auth = contract.get("authorization") or {}
    if any(auth.get(field) is not False for field in (
        "current_real_activation", "current_formal_model_execution",
        "current_target_outcome_access", "current_formal_scoring",
        "current_formal_result_claim", "synthetic_rehearsal_authorizes_formal_execution",
        "production_memory_write", "external_deployment",
    )):
        errors.append("authorization.current_boundary")
    public_signature = inspect.signature(build_live_activation_audit)
    if "readiness" in public_signature.parameters:
        errors.append("api.caller_readiness_parameter")
    return {
        "valid": not errors,
        "errors": errors,
        "binding_count": len(bindings or {}),
        "contract_hash": digest(contract),
        "dependency_set_hash": digest(bindings or {}),
    }


def _run_text(command: list[str]) -> str:
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return completed.stdout.strip() or completed.stderr.strip()


def _sysctl(name: str) -> str:
    try:
        return _run_text(["sysctl", "-n", name])
    except (FileNotFoundError, subprocess.CalledProcessError):
        return "unavailable"


def capture_runtime_snapshot(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    runtime = contract["runtime_snapshot"]
    manifest_path = Path(runtime["model_manifest_path"])
    if not manifest_path.is_file():
        raise FileNotFoundError(f"local model manifest missing: {manifest_path}")
    try:
        ollama_version = _run_text(["ollama", "--version"])
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("ollama version unavailable") from exc
    hardware = {
        "os": platform.system(),
        "os_release": platform.release(),
        "machine_architecture": platform.machine(),
        "cpu_brand": _sysctl("machdep.cpu.brand_string"),
        "logical_cpu_count": os.cpu_count(),
        "physical_memory_bytes": _sysctl("hw.memsize"),
    }
    snapshot = {
        "schema": "uruha_m56_local_runtime_snapshot_v1",
        "provider": runtime["provider"],
        "model_name": runtime["model_name"],
        "model_manifest_sha256": sha256_file(manifest_path),
        "ollama_version": ollama_version,
        "hardware": hardware,
        "hardware_fingerprint": digest(hardware),
        "model_calls": 0,
        "target_outcome_access_count": 0,
    }
    snapshot["runtime_snapshot_hash"] = digest(snapshot)
    return snapshot


def validate_runtime_snapshot(
    snapshot: dict[str, Any], contract: dict[str, Any] | None = None, *, compare_live: bool = False
) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    runtime = contract["runtime_snapshot"]
    errors: list[str] = []
    expected_fields = {
        "schema", "provider", "model_name", "model_manifest_sha256", "ollama_version",
        "hardware", "hardware_fingerprint", "model_calls", "target_outcome_access_count",
        "runtime_snapshot_hash",
    }
    if not isinstance(snapshot, dict) or set(snapshot) != expected_fields:
        errors.append("snapshot.fields")
        snapshot = snapshot if isinstance(snapshot, dict) else {}
    if snapshot.get("schema") != "uruha_m56_local_runtime_snapshot_v1":
        errors.append("snapshot.schema")
    if snapshot.get("provider") != runtime["provider"] or snapshot.get("model_name") != runtime["model_name"]:
        errors.append("snapshot.model")
    manifest_path = Path(runtime["model_manifest_path"])
    expected_model_hash = sha256_file(manifest_path) if manifest_path.is_file() else None
    if snapshot.get("model_manifest_sha256") != expected_model_hash:
        errors.append("snapshot.model_manifest_sha256")
    hardware = snapshot.get("hardware")
    if not isinstance(hardware, dict) or snapshot.get("hardware_fingerprint") != digest(hardware):
        errors.append("snapshot.hardware_fingerprint")
    if not str(snapshot.get("ollama_version") or ""):
        errors.append("snapshot.ollama_version")
    if snapshot.get("model_calls") != 0 or snapshot.get("target_outcome_access_count") != 0:
        errors.append("snapshot.execution_boundary")
    unhashed = {key: value for key, value in snapshot.items() if key != "runtime_snapshot_hash"}
    if snapshot.get("runtime_snapshot_hash") != digest(unhashed):
        errors.append("snapshot.hash")
    if compare_live and not errors:
        live = capture_runtime_snapshot(contract)
        if snapshot != live:
            errors.append("snapshot.live_drift")
    return {"valid": not errors, "errors": errors, "runtime_snapshot_hash": snapshot.get("runtime_snapshot_hash")}


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _git_ignored(path: Path) -> bool:
    relative = os.path.relpath(path, ROOT)
    completed = subprocess.run(
        ["git", "check-ignore", "-q", relative], cwd=ROOT, capture_output=True
    )
    return completed.returncode == 0


def validate_private_layout(
    run_root: str | Path, contract: dict[str, Any] | None = None, *, require_exists: bool = False
) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    root = Path(run_root).expanduser()
    resolved_private = DEFAULT_PRIVATE_ROOT.resolve()
    resolved = root.resolve(strict=False)
    errors: list[str] = []
    if resolved == resolved_private or not _is_relative_to(resolved, resolved_private):
        errors.append("layout.run_root_must_be_direct_child_of_private_root")
    elif resolved.parent != resolved_private:
        errors.append("layout.run_root_must_not_be_nested_or_shared")
    if root.name in ("", ".", ".."):
        errors.append("layout.run_id")
    if root.exists() and root.is_symlink():
        errors.append("layout.symlink")
    if require_exists and not root.is_dir():
        errors.append("layout.run_root_missing")
    if not _git_ignored(resolved):
        errors.append("layout.not_gitignored")
    dirs = {name: resolved / name for name in REQUIRED_LAYOUT_DIRS}
    if require_exists:
        for name, path in dirs.items():
            if not path.is_dir() or path.is_symlink():
                errors.append(f"layout.directory:{name}")
    layout_descriptor = {
        "private_root_contract": contract["private_layout"]["root"],
        "run_id": root.name,
        "directories": list(REQUIRED_LAYOUT_DIRS),
        "outcome_key_compartment": "scoring",
        "generation_can_read_outcome_key": False,
        "git_tracked": False,
    }
    return {
        "valid": not errors,
        "errors": errors,
        "run_id": root.name,
        "layout": layout_descriptor,
        "layout_hash": digest(layout_descriptor),
        "paths": dirs,
    }


def _atomic_write_json(path: Path, value: dict[str, Any], *, exclusive: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        if exclusive:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
        else:
            temp_path = path.with_name(path.name + f".tmp-{os.getpid()}-{secrets.token_hex(4)}")
            with temp_path.open("x", encoding="utf-8") as handle:
                handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp_path, 0o600)
            os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def _live_readiness(compiled_temporal_result: dict[str, Any] | None = None) -> dict[str, Any]:
    return readiness_m55.build_readiness_m55(compiled_temporal_result=compiled_temporal_result)


def build_live_activation_audit(
    *, compiled_temporal_result: dict[str, Any] | None = None, run_root: str | Path | None = None
) -> dict[str, Any]:
    """Build the only public readiness audit; no readiness object can be injected."""

    contract = load_contract()
    contract_report = validate_contract(contract)
    live = _live_readiness(compiled_temporal_result)
    snapshot = capture_runtime_snapshot(contract)
    snapshot_report = validate_runtime_snapshot(snapshot, contract)
    candidate_root = Path(run_root) if run_root is not None else DEFAULT_PRIVATE_ROOT / "pending-real-run"
    layout = validate_private_layout(candidate_root, contract)
    counts = deepcopy(live.get("counts") or {})
    v7_slots = list(counts.get("v7_completed_slots_by_ledger") or [0, 0])
    while len(v7_slots) < 2:
        v7_slots.append(0)
    gates = {
        "activation_contract_and_dependencies_valid": contract_report["valid"],
        "two_distinct_v7_ledgers_complete": live.get("gates", {}).get("two_independent_v7_ledgers_complete") is True,
        "v7_reliability_passed": live.get("gates", {}).get("v7_reliability_passed") is True,
        "v9_thirty_events_two_humans": (
            live.get("gates", {}).get("target_events_independently_coded") is True
            and live.get("gates", {}).get("target_human_coder_count_is_two") is True
        ),
        "real_temporal_rows_thirty_and_leakage_free": live.get("gates", {}).get("thirty_temporally_valid_prediction_rows") is True,
        "m55_live_authorizes_m56": live.get("m56_authorized") is True,
        "private_execution_layout_valid": layout["valid"],
        "local_model_and_hardware_snapshot_valid": snapshot_report["valid"],
    }
    authorized = all(gates.values())
    blockers = [name for name, passed in gates.items() if not passed]
    audit = {
        "schema": AUDIT_SCHEMA,
        "version": "1.0.0",
        "status": "eligible_to_prepare_private_activation" if authorized else "formal_activation_denied",
        "contract_hash": contract_report["contract_hash"],
        "dependency_set_hash": contract_report["dependency_set_hash"],
        "gates": gates,
        "blocking_gates": blockers,
        "counts": {
            "v7_slots_by_ledger": v7_slots[:2],
            "v9_independently_reviewed_events": int(counts.get("v9_independently_reviewed_event_count") or 0),
            "v9_human_coders": int(counts.get("v9_human_coder_count") or 0),
            "real_temporal_rows": int(counts.get("temporally_valid_prediction_row_count") or 0),
        },
        "runtime_snapshot": snapshot,
        "private_layout": layout["layout"],
        "current_execution_authorized": authorized,
        "formal_activation_receipt_created": False,
        "formal_model_calls": 0,
        "generation_target_outcome_access_count": 0,
        "formal_scoring_started": False,
        "formal_result_created": False,
        "caller_supplied_readiness_used": False,
        "synthetic_or_model_labels_counted_as_human": False,
        "claim_boundary": contract["claim_boundary"],
    }
    audit["audit_hash"] = digest(audit)
    return audit


def build_real_run_manifest(packet: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    packet_report = preflight_m56.validate_prediction_packet(packet)
    snapshot_report = validate_runtime_snapshot(snapshot)
    if not packet_report["valid"]:
        raise ValueError("invalid real prediction packet: " + "; ".join(packet_report["errors"]))
    if packet.get("data_kind") != temporal_m55.REAL_KIND or packet.get("sample_count") != 30:
        raise PermissionError("formal manifest requires exactly 30 real-public-observation rows")
    if not snapshot_report["valid"]:
        raise ValueError("invalid runtime snapshot: " + "; ".join(snapshot_report["errors"]))
    controls = preflight_m56.load_contract()["model_and_resource_controls"]
    sample_ids = [row["sample_id"] for row in packet["model_inputs"]]
    runs = []
    for condition in preflight_m56.CONDITION_IDS:
        model_used = condition != "B0_PRIOR"
        runs.append({
            "condition_id": condition,
            "model_used": model_used,
            "model_name": controls["model_name"] if model_used else "deterministic_prior",
            "model_artifact_digest": snapshot["model_manifest_sha256"] if model_used else "deterministic_prior",
            "hardware_fingerprint": snapshot["hardware_fingerprint"],
            "provider_options": deepcopy(controls["provider_options"]) if model_used else {},
            "input_token_budget": controls["per_sample_input_token_budget"] if model_used else 0,
            "output_token_budget": controls["per_sample_output_token_budget"] if model_used else 0,
            "model_call_cap_per_sample": 1 if model_used else 0,
            "source_sample_ids": sample_ids,
            "outcome_key_visible": False,
            "retry_count": 0,
            "fallback_count": 0,
        })
    manifest = {
        "schema": preflight_m56.RUN_MANIFEST_SCHEMA,
        "version": "1.0.0",
        "status": FORMAL_MANIFEST_STATUS,
        "contract_hash": preflight_m56.validate_contract()["contract_hash"],
        "data_kind": packet["data_kind"],
        "dataset_hash": packet["dataset_hash"],
        "prediction_packet_hash": digest(packet),
        "runtime_snapshot_hash": snapshot["runtime_snapshot_hash"],
        "condition_runs": runs,
        "prediction_commitment_hash": None,
        "scoring_started": False,
        "model_call_count": 0,
    }
    report = preflight_m56.validate_run_manifest(manifest, packet)
    if not report["valid"]:
        raise ValueError("invalid real run manifest: " + "; ".join(report["errors"]))
    return manifest


def _build_formal_capsule_unchecked(
    packet: dict[str, Any], manifest: dict[str, Any], contract: dict[str, Any]
) -> dict[str, Any]:
    summaries: list[dict[str, Any]] = []
    summary_by_signature: dict[str, dict[str, Any]] = {}
    tasks: list[dict[str, Any]] = []
    for packet_row in packet["model_inputs"]:
        model_input = packet_row["model_input"]
        history = deepcopy(model_input["available_history"])
        history_signature = digest(history)
        if history_signature not in summary_by_signature:
            empty = not history
            summary = {
                "summary_task_id": capsule_m56._summary_task_id(history_signature),
                "history_signature": history_signature,
                "source_history": history,
                "source_history_ids": [row["history_id"] for row in history],
                "model_call_required": not empty,
                "empty_history_artifact": empty,
            }
            summary["summary_view_hash"] = digest(summary)
            summary_by_signature[history_signature] = summary
            summaries.append(summary)
        common = capsule_m56._common(model_input)
        source = capsule_m56._source_information(model_input)
        source_hash = digest(source)
        for condition in packet_row["condition_order"]:
            view = deepcopy(common)
            if condition == "B0_PRIOR":
                view["pre_cutoff_historical_behavior_counts"] = capsule_m56._history_counts(model_input)
            elif condition == "B1_BASE_LLM":
                view.update(current_pre_cutoff_event=deepcopy(model_input["event_context"]), minimal_target_identity=capsule_m56._minimal_identity(model_input))
            elif condition == "B2_PERSONA_PROMPT":
                view.update(current_pre_cutoff_event=deepcopy(model_input["event_context"]), minimal_target_identity=capsule_m56._minimal_identity(model_input), frozen_pre_target_persona_summary=capsule_m56._persona_summary(model_input))
            elif condition == "B3_RAG":
                view.update(current_pre_cutoff_event=deepcopy(model_input["event_context"]), minimal_target_identity=capsule_m56._minimal_identity(model_input), frozen_pre_target_persona_summary=capsule_m56._persona_summary(model_input), deterministic_top4_pre_cutoff_history=capsule_m56._retrieve_history(model_input))
            elif condition == "B4_FULL_HISTORY_SUMMARY":
                view.update(current_pre_cutoff_event=deepcopy(model_input["event_context"]), minimal_target_identity=capsule_m56._minimal_identity(model_input), summary_task_id=summary_by_signature[history_signature]["summary_task_id"], summary_artifact_hash_required=True)
            elif condition == capsule_m56.PRIMARY_CONTROL:
                view.update(source_information=deepcopy(source), source_information_hash=source_hash)
            elif condition == capsule_m56.PRIMARY_SYSTEM:
                view.update(
                    source_information=deepcopy(source),
                    source_information_hash=source_hash,
                    equation_definition_binding=deepcopy(capsule_m56.load_contract()["bindings"]["equation_v1_contract"]),
                    required_pre_outcome_artifacts=["fit_artifact_hash", "state_snapshot_hash", "transition_trace_hash"],
                )
            else:
                raise ValueError(f"unsupported condition {condition}")
            task = {
                "task_id": capsule_m56._prediction_task_id(model_input["sample_id"], condition),
                "sample_id": model_input["sample_id"],
                "condition_id": condition,
                "source_model_input_hash": packet_row["model_input_hash"],
                "view": view,
            }
            task["view_hash"] = digest(view)
            tasks.append(task)
    value = {
        "schema": FORMAL_CAPSULE_SCHEMA,
        "version": "1.0.0",
        "status": FORMAL_CAPSULE_STATUS,
        "data_kind": packet["data_kind"],
        "activation_contract_hash": validate_contract(contract)["contract_hash"],
        "frozen_capsule_contract_hash": capsule_m56.validate_contract()["contract_hash"],
        "preflight_contract_hash": preflight_m56.validate_contract()["contract_hash"],
        "dataset_hash": packet["dataset_hash"],
        "prediction_packet_hash": digest(packet),
        "run_manifest_hash": digest(manifest),
        "sample_count": packet["sample_count"],
        "condition_count": len(preflight_m56.CONDITION_IDS),
        "summary_tasks": summaries,
        "prediction_tasks": tasks,
        "outcome_access_count": 0,
        "model_call_count": 0,
        "formal_execution_authorized": False,
    }
    value["capsule_hash"] = digest(value)
    return value


def build_formal_capsule(packet: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    if packet.get("data_kind") != temporal_m55.REAL_KIND or packet.get("sample_count") != 30:
        raise PermissionError("formal capsule requires exactly 30 real-public-observation rows")
    if not preflight_m56.validate_prediction_packet(packet)["valid"]:
        raise ValueError("prediction packet is invalid")
    if not preflight_m56.validate_run_manifest(manifest, packet)["valid"]:
        raise ValueError("run manifest is invalid")
    capsule = _build_formal_capsule_unchecked(packet, manifest, load_contract())
    report = validate_formal_capsule(capsule, packet, manifest)
    if not report["valid"]:
        raise ValueError("formal capsule invalid: " + "; ".join(report["errors"]))
    return capsule


def validate_formal_capsule(
    capsule: dict[str, Any], packet: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, Any]:
    errors: list[str] = []
    if packet.get("data_kind") != temporal_m55.REAL_KIND or packet.get("sample_count") != 30:
        errors.append("packet.not_thirty_real_rows")
    packet_report = preflight_m56.validate_prediction_packet(packet)
    manifest_report = preflight_m56.validate_run_manifest(manifest, packet)
    errors.extend(f"packet:{e}" for e in packet_report["errors"])
    errors.extend(f"manifest:{e}" for e in manifest_report["errors"])
    try:
        expected = _build_formal_capsule_unchecked(packet, manifest, load_contract())
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"capsule.source:{exc}")
        expected = None
    if expected is not None and capsule != expected:
        errors.append("capsule.content_or_hash_mismatch")
    forbidden = _find_keys(capsule, capsule_m56.OUTCOME_KEYS)
    errors.extend(f"capsule.outcome_key:{path}" for path in forbidden)
    tasks = capsule.get("prediction_tasks") if isinstance(capsule, dict) else []
    source_hashes: dict[str, dict[str, str]] = {}
    for task in tasks or []:
        if task.get("condition_id") in (capsule_m56.PRIMARY_CONTROL, capsule_m56.PRIMARY_SYSTEM):
            source_hashes.setdefault(task.get("sample_id"), {})[task["condition_id"]] = task.get("view", {}).get("source_information_hash")
    if any(row.get(capsule_m56.PRIMARY_CONTROL) != row.get(capsule_m56.PRIMARY_SYSTEM) for row in source_hashes.values()):
        errors.append("capsule.primary_source_hash_mismatch")
    return {
        "valid": not errors,
        "errors": errors,
        "task_count": len(tasks or []),
        "forbidden_key_count": len(forbidden),
        "capsule_hash": capsule.get("capsule_hash") if isinstance(capsule, dict) else None,
    }


def _build_formal_bundle_unchecked(
    packet: dict[str, Any], capsule: dict[str, Any], contract: dict[str, Any]
) -> dict[str, Any]:
    bundle = artifacts_m56._materialize_bundle_unchecked(packet, capsule, artifacts_m56.load_contract())
    bundle["schema"] = FORMAL_BUNDLE_SCHEMA
    bundle["status"] = FORMAL_BUNDLE_STATUS
    bundle["data_kind"] = temporal_m55.REAL_KIND
    bundle["activation_contract_hash"] = validate_contract(contract)["contract_hash"]
    bundle["authorization"] = {
        "formal_model_execution": False,
        "formal_scoring": False,
        "formal_claim": False,
        "activation_receipt_required": True,
    }
    bundle.pop("artifact_bundle_hash", None)
    bundle["artifact_bundle_hash"] = digest(bundle)
    return bundle


def build_formal_artifact_bundle(
    packet: dict[str, Any], capsule: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, Any]:
    capsule_report = validate_formal_capsule(capsule, packet, manifest)
    if not capsule_report["valid"]:
        raise ValueError("formal capsule invalid: " + "; ".join(capsule_report["errors"]))
    bundle = _build_formal_bundle_unchecked(packet, capsule, load_contract())
    report = validate_formal_artifact_bundle(bundle, packet, capsule, manifest)
    if not report["valid"]:
        raise ValueError("formal artifact bundle invalid: " + "; ".join(report["errors"]))
    return bundle


def validate_formal_artifact_bundle(
    bundle: dict[str, Any], packet: dict[str, Any], capsule: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, Any]:
    capsule_report = validate_formal_capsule(capsule, packet, manifest)
    errors = [f"capsule:{e}" for e in capsule_report["errors"]]
    try:
        expected = _build_formal_bundle_unchecked(packet, capsule, load_contract())
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"bundle.source:{exc}")
        expected = None
    if expected is not None and bundle != expected:
        errors.append("bundle.content_or_hash_mismatch")
    forbidden = _find_keys(bundle, capsule_m56.OUTCOME_KEYS)
    errors.extend(f"bundle.outcome_key:{path}" for path in forbidden)
    rows = bundle.get("sample_artifacts") if isinstance(bundle, dict) else []
    if len(rows or []) != 30:
        errors.append("bundle.sample_count")
    private_fabrication = sum(
        int(((row.get("state_snapshot") or {}).get("coverage") or {}).get("private_state_fabrication_count") or 0)
        for row in (rows or []) if isinstance(row, dict)
    )
    if private_fabrication:
        errors.append("bundle.private_state_fabrication")
    return {
        "valid": not errors,
        "errors": errors,
        "sample_count": len(rows or []),
        "artifact_count": len(rows or []) * 3,
        "private_state_fabrication_count": private_fabrication,
        "forbidden_key_count": len(forbidden),
        "artifact_bundle_hash": bundle.get("artifact_bundle_hash") if isinstance(bundle, dict) else None,
    }


def build_synthetic_rehearsal() -> dict[str, Any]:
    packet, manifest, capsule = artifacts_m56.build_demo_packet()
    bundle = artifacts_m56.materialize_artifact_bundle(packet, capsule, manifest)
    snapshot = capture_runtime_snapshot()
    rehearsal = {
        "schema": REHEARSAL_SCHEMA,
        "version": "1.0.0",
        "status": "synthetic_hash_and_compartment_rehearsal_only",
        "data_kind": packet["data_kind"],
        "prediction_packet_hash": digest(packet),
        "run_manifest_hash": digest(manifest),
        "capsule_hash": capsule["capsule_hash"],
        "equation_artifact_bundle_hash": bundle["artifact_bundle_hash"],
        "runtime_snapshot_hash": snapshot["runtime_snapshot_hash"],
        "formal_execution_authorized": False,
        "formal_receipt_created": False,
        "model_calls": 0,
        "target_outcome_access_count": 0,
        "human_evidence_count": 0,
        "claim_boundary": "hash/layout rehearsal only; cannot be converted into a formal activation receipt",
    }
    rehearsal["rehearsal_hash"] = digest(rehearsal)
    return rehearsal


def _prepare_directories(run_root: Path) -> dict[str, Path]:
    layout = validate_private_layout(run_root)
    if not layout["valid"]:
        raise ValueError("invalid private layout: " + "; ".join(layout["errors"]))
    if run_root.exists():
        raise FileExistsError("formal run root already exists; no overwrite or retry is allowed")
    run_root.mkdir(parents=True, mode=0o700)
    for path in layout["paths"].values():
        path.mkdir(mode=0o700)
    return layout["paths"]


def prepare_real_activation(
    compiled_temporal_result: dict[str, Any], *, run_id: str
) -> dict[str, Any]:
    """Prepare private artifacts only if the standard live M55 gate passes now."""

    run_root = DEFAULT_PRIVATE_ROOT / run_id
    audit = build_live_activation_audit(compiled_temporal_result=compiled_temporal_result, run_root=run_root)
    if audit["current_execution_authorized"] is not True:
        raise PermissionError("formal M56 activation denied: " + ",".join(audit["blocking_gates"]))
    live = _live_readiness(compiled_temporal_result)
    split = preflight_m56.build_blinded_artifacts(compiled_temporal_result, readiness=live)
    packet = split["prediction_packet"]
    outcome_key = split["outcome_key"]
    split_report = split["split_report"]
    snapshot = capture_runtime_snapshot()
    manifest = build_real_run_manifest(packet, snapshot)
    capsule = build_formal_capsule(packet, manifest)
    bundle = build_formal_artifact_bundle(packet, capsule, manifest)
    layout = validate_private_layout(run_root)
    request = {
        "schema": REQUEST_SCHEMA,
        "version": "1.0.0",
        "status": "private_real_activation_request_pending_receipt",
        "run_id": run_id,
        "contract_hash": audit["contract_hash"],
        "dependency_set_hash": audit["dependency_set_hash"],
        "dataset_hash": packet["dataset_hash"],
        "prediction_packet_hash": digest(packet),
        "outcome_key_hash": digest(outcome_key),
        "split_report_hash": digest(split_report),
        "run_manifest_hash": digest(manifest),
        "capsule_hash": capsule["capsule_hash"],
        "equation_artifact_bundle_hash": bundle["artifact_bundle_hash"],
        "runtime_snapshot_hash": snapshot["runtime_snapshot_hash"],
        "private_layout_hash": layout["layout_hash"],
        "sample_count": packet["sample_count"],
        "condition_count": len(preflight_m56.CONDITION_IDS),
        "generation_target_outcome_access_count": 0,
        "model_calls_before_activation": 0,
        "formal_execution_authorized": False,
        "formal_scoring_authorized": False,
    }
    request["activation_request_hash"] = digest(request)
    paths = _prepare_directories(run_root)
    _atomic_write_json(paths["generation"] / "prediction_packet.json", packet, exclusive=True)
    _atomic_write_json(paths["generation"] / "run_manifest.json", manifest, exclusive=True)
    _atomic_write_json(paths["generation"] / "execution_capsule.json", capsule, exclusive=True)
    _atomic_write_json(paths["generation"] / "equation_artifacts.json", bundle, exclusive=True)
    _atomic_write_json(paths["generation"] / "runtime_snapshot.json", snapshot, exclusive=True)
    _atomic_write_json(paths["scoring"] / "private_outcome_key.json", outcome_key, exclusive=True)
    _atomic_write_json(paths["scoring"] / "split_report.json", split_report, exclusive=True)
    _atomic_write_json(paths["commitments"] / "activation_request.json", request, exclusive=True)
    return request


def _load_prepared(run_root: Path) -> dict[str, dict[str, Any]]:
    layout = validate_private_layout(run_root, require_exists=True)
    if not layout["valid"]:
        raise ValueError("invalid private layout: " + "; ".join(layout["errors"]))
    paths = layout["paths"]
    return {
        "request": load_json(paths["commitments"] / "activation_request.json"),
        "packet": load_json(paths["generation"] / "prediction_packet.json"),
        "manifest": load_json(paths["generation"] / "run_manifest.json"),
        "capsule": load_json(paths["generation"] / "execution_capsule.json"),
        "bundle": load_json(paths["generation"] / "equation_artifacts.json"),
        "snapshot": load_json(paths["generation"] / "runtime_snapshot.json"),
        "outcome_key": load_json(paths["scoring"] / "private_outcome_key.json"),
        "split_report": load_json(paths["scoring"] / "split_report.json"),
    }


def validate_prepared_activation(
    compiled_temporal_result: dict[str, Any], *, run_id: str
) -> dict[str, Any]:
    run_root = DEFAULT_PRIVATE_ROOT / run_id
    audit = build_live_activation_audit(compiled_temporal_result=compiled_temporal_result, run_root=run_root)
    errors: list[str] = []
    if audit["current_execution_authorized"] is not True:
        errors.extend(f"live_gate:{name}" for name in audit["blocking_gates"])
    try:
        prepared = _load_prepared(run_root)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        return {"valid": False, "errors": errors + [f"prepared:{exc}"]}
    request = prepared["request"]
    packet = prepared["packet"]
    manifest = prepared["manifest"]
    capsule = prepared["capsule"]
    bundle = prepared["bundle"]
    snapshot = prepared["snapshot"]
    outcome_key = prepared["outcome_key"]
    split_report = prepared["split_report"]
    capsule_report = validate_formal_capsule(capsule, packet, manifest)
    bundle_report = validate_formal_artifact_bundle(bundle, packet, capsule, manifest)
    snapshot_report = validate_runtime_snapshot(snapshot, compare_live=True)
    errors.extend(f"capsule:{e}" for e in capsule_report["errors"])
    errors.extend(f"bundle:{e}" for e in bundle_report["errors"])
    errors.extend(f"runtime:{e}" for e in snapshot_report["errors"])
    expected = {
        "schema": REQUEST_SCHEMA,
        "version": "1.0.0",
        "status": "private_real_activation_request_pending_receipt",
        "run_id": run_id,
        "contract_hash": audit["contract_hash"],
        "dependency_set_hash": audit["dependency_set_hash"],
        "dataset_hash": packet.get("dataset_hash"),
        "prediction_packet_hash": digest(packet),
        "outcome_key_hash": digest(outcome_key),
        "split_report_hash": digest(split_report),
        "run_manifest_hash": digest(manifest),
        "capsule_hash": capsule.get("capsule_hash"),
        "equation_artifact_bundle_hash": bundle.get("artifact_bundle_hash"),
        "runtime_snapshot_hash": snapshot.get("runtime_snapshot_hash"),
        "private_layout_hash": validate_private_layout(run_root, require_exists=True)["layout_hash"],
        "sample_count": packet.get("sample_count"),
        "condition_count": len(preflight_m56.CONDITION_IDS),
        "generation_target_outcome_access_count": 0,
        "model_calls_before_activation": 0,
        "formal_execution_authorized": False,
        "formal_scoring_authorized": False,
    }
    expected["activation_request_hash"] = digest(expected)
    if request != expected:
        errors.append("request.content_or_hash_mismatch")
    forbidden_generation = set(preflight_m56.FORBIDDEN_PACKET_KEYS) | capsule_m56.OUTCOME_KEYS
    for name in ("packet", "manifest", "capsule", "bundle", "snapshot"):
        found = _find_keys(prepared[name], forbidden_generation)
        errors.extend(f"generation.{name}.forbidden:{path}" for path in found)
    outcome_report = capsule_m56.validate_outcome_key(outcome_key, packet, split_report)
    errors.extend(f"outcome:{e}" for e in outcome_report["errors"])
    return {
        "valid": not errors,
        "errors": errors,
        "activation_request_hash": request.get("activation_request_hash"),
        "runtime_snapshot_hash": snapshot.get("runtime_snapshot_hash"),
        "equation_artifact_bundle_hash": bundle.get("artifact_bundle_hash"),
        "generation_target_outcome_access_count": 0,
        "model_calls_before_activation": 0,
    }


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed.astimezone(timezone.utc)


def issue_activation_receipt(
    compiled_temporal_result: dict[str, Any], *, run_id: str, now: datetime | None = None
) -> dict[str, Any]:
    report = validate_prepared_activation(compiled_temporal_result, run_id=run_id)
    if not report["valid"]:
        raise PermissionError("prepared activation invalid: " + "; ".join(report["errors"]))
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    expires = now + timedelta(seconds=int(load_contract()["receipt"]["ttl_seconds"]))
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "version": "1.0.0",
        "status": "issued_unconsumed",
        "run_id": run_id,
        "activation_request_hash": report["activation_request_hash"],
        "runtime_snapshot_hash": report["runtime_snapshot_hash"],
        "equation_artifact_bundle_hash": report["equation_artifact_bundle_hash"],
        "execution_nonce": secrets.token_hex(24),
        "issued_at": now.isoformat(),
        "expires_at": expires.isoformat(),
        "consumed_at": None,
        "formal_generation_authorized": True,
        "formal_scoring_authorized": False,
        "formal_result_claim_authorized": False,
        "production_memory_write_authorized": False,
        "external_deployment_authorized": False,
        "retry_or_fallback_authorized": False,
        "generation_target_outcome_access_count": 0,
    }
    receipt["receipt_hash"] = digest(receipt)
    path = DEFAULT_PRIVATE_ROOT / run_id / "commitments" / FORMAL_RECEIPT_FILENAME
    _atomic_write_json(path, receipt, exclusive=True)
    return receipt


def validate_activation_receipt(
    receipt: dict[str, Any], request: dict[str, Any], *, now: datetime | None = None
) -> dict[str, Any]:
    errors: list[str] = []
    expected_fields = {
        "schema", "version", "status", "run_id", "activation_request_hash",
        "runtime_snapshot_hash", "equation_artifact_bundle_hash", "execution_nonce",
        "issued_at", "expires_at", "consumed_at", "formal_generation_authorized",
        "formal_scoring_authorized", "formal_result_claim_authorized",
        "production_memory_write_authorized", "external_deployment_authorized",
        "retry_or_fallback_authorized", "generation_target_outcome_access_count", "receipt_hash",
    }
    if not isinstance(receipt, dict) or set(receipt) != expected_fields:
        errors.append("receipt.fields")
        receipt = receipt if isinstance(receipt, dict) else {}
    if receipt.get("schema") != RECEIPT_SCHEMA or receipt.get("version") != "1.0.0":
        errors.append("receipt.schema_or_version")
    if receipt.get("status") != "issued_unconsumed" or receipt.get("consumed_at") is not None:
        errors.append("receipt.state")
    if receipt.get("activation_request_hash") != request.get("activation_request_hash"):
        errors.append("receipt.activation_request_hash")
    if receipt.get("runtime_snapshot_hash") != request.get("runtime_snapshot_hash"):
        errors.append("receipt.runtime_snapshot_hash")
    if receipt.get("equation_artifact_bundle_hash") != request.get("equation_artifact_bundle_hash"):
        errors.append("receipt.equation_artifact_bundle_hash")
    if not isinstance(receipt.get("execution_nonce"), str) or len(receipt.get("execution_nonce")) != 48:
        errors.append("receipt.execution_nonce")
    if receipt.get("formal_generation_authorized") is not True:
        errors.append("receipt.generation_authorization")
    if any(receipt.get(field) is not False for field in (
        "formal_scoring_authorized", "formal_result_claim_authorized",
        "production_memory_write_authorized", "external_deployment_authorized",
        "retry_or_fallback_authorized",
    )):
        errors.append("receipt.excess_authorization")
    if receipt.get("generation_target_outcome_access_count") != 0:
        errors.append("receipt.outcome_access")
    try:
        issued = _parse_time(str(receipt.get("issued_at") or ""))
        expires = _parse_time(str(receipt.get("expires_at") or ""))
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        ttl = int(load_contract()["receipt"]["ttl_seconds"])
        if expires <= issued or (expires - issued).total_seconds() != ttl:
            errors.append("receipt.ttl")
        if current > expires:
            errors.append("receipt.expired")
    except (TypeError, ValueError):
        errors.append("receipt.time")
    unhashed = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    if receipt.get("receipt_hash") != digest(unhashed):
        errors.append("receipt.hash")
    return {"valid": not errors, "errors": errors, "receipt_hash": receipt.get("receipt_hash")}


def consume_activation_receipt(
    compiled_temporal_result: dict[str, Any], *, run_id: str, now: datetime | None = None
) -> dict[str, Any]:
    run_root = DEFAULT_PRIVATE_ROOT / run_id
    validation = validate_prepared_activation(compiled_temporal_result, run_id=run_id)
    if not validation["valid"]:
        raise PermissionError("prepared activation invalid before consumption")
    request = load_json(run_root / "commitments/activation_request.json")
    receipt_path = run_root / "commitments" / FORMAL_RECEIPT_FILENAME
    receipt = load_json(receipt_path)
    report = validate_activation_receipt(receipt, request, now=now)
    if not report["valid"]:
        raise PermissionError("activation receipt invalid: " + "; ".join(report["errors"]))
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    consumed = deepcopy(receipt)
    consumed["status"] = "consumed"
    consumed["consumed_at"] = current.isoformat()
    consumed.pop("receipt_hash", None)
    consumed["receipt_hash"] = digest(consumed)
    lease = {
        "schema": LEASE_SCHEMA,
        "version": "1.0.0",
        "status": "single_formal_generation_run_in_progress",
        "run_id": run_id,
        "consumed_receipt_hash": consumed["receipt_hash"],
        "activation_request_hash": request["activation_request_hash"],
        "execution_nonce_hash": sha256(receipt["execution_nonce"].encode("utf-8")).hexdigest(),
        "started_at": current.isoformat(),
        "formal_generation_authorized": True,
        "formal_scoring_authorized": False,
        "retry_or_fallback_authorized": False,
        "generation_target_outcome_access_count": 0,
    }
    lease["lease_hash"] = digest(lease)
    lease_path = run_root / "commitments" / FORMAL_LEASE_FILENAME
    _atomic_write_json(lease_path, lease, exclusive=True)
    _atomic_write_json(receipt_path, consumed)
    return lease


def build_live_report() -> dict[str, Any]:
    audit = build_live_activation_audit()
    rehearsal = build_synthetic_rehearsal()
    return {
        "schema": "uruha_m56_real_data_activation_live_report_v1",
        "status": audit["status"],
        "audit": audit,
        "synthetic_rehearsal": rehearsal,
        "formal_receipt_created": False,
        "formal_model_calls": 0,
        "formal_result_created": False,
    }


def render_dashboard(report: dict[str, Any] | None = None) -> str:
    report = deepcopy(report or build_live_report())
    audit = report["audit"]
    counts = audit["counts"]
    gates = audit["gates"]
    gate_rows = [
        ("兩位真人先獨立標註", f"{counts['v7_slots_by_ledger'][0]}/18 + {counts['v7_slots_by_ledger'][1]}/18", gates["two_distinct_v7_ledgers_complete"]),
        ("標註可靠度通過", "同一規則能否被兩人一致使用", gates["v7_reliability_passed"]),
        ("30 個公開行為事件", f"{counts['v9_independently_reviewed_events']}/30 · {counts['v9_human_coders']} 位真人", gates["v9_thirty_events_two_humans"]),
        ("30 條 cutoff→future", f"{counts['real_temporal_rows']}/30 · future leakage 必須為 0", gates["real_temporal_rows_thirty_and_leakage_free"]),
        ("模型與電腦指紋", "qwen3.5:9b · 同 artifact · 同硬體", gates["local_model_and_hardware_snapshot_valid"]),
        ("私有四分艙", "generation / commitments / scoring / telemetry", gates["private_execution_layout_valid"]),
    ]
    cards = "".join(
        f'<article class="gate {"pass" if passed else "blocked"}"><span>{"PASS" if passed else "WAIT"}</span><h3>{html.escape(label)}</h3><p>{html.escape(detail)}</p></article>'
        for label, detail, passed in gate_rows
    )
    snapshot = audit["runtime_snapshot"]
    model_hash = str(snapshot["model_manifest_sha256"])
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M56.2 正式執行啟用閘門</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#07101d;color:#eef5ff;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}main{{max-width:1280px;margin:auto;padding:32px}}h1{{margin:.25em 0;font-size:clamp(30px,5vw,48px)}}h2{{margin-top:0}}p{{line-height:1.55}}.hero,.panel{{border:1px solid #314968;border-radius:22px;padding:24px;margin-bottom:18px;background:#101b2d}}.hero{{background:linear-gradient(135deg,#122e48,#24162f)}}.status{{display:inline-block;padding:7px 11px;border-radius:999px;background:#541b2d;color:#ffc1ce;font-weight:800}}.headline{{font-size:22px;color:#ff9fb4;font-weight:800}}.gates{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}}.gate{{border:1px solid #304866;border-radius:16px;padding:16px;background:#0a1425;min-height:126px}}.gate span{{font-weight:800;color:#f5a4b7}}.gate.pass span{{color:#67dfc8}}.gate h3{{margin:10px 0 6px}}.gate p{{margin:0;color:#c8d5e7}}.flow{{display:grid;grid-template-columns:1fr auto 1fr auto 1fr;align-items:center;gap:12px}}.node{{padding:18px;border-radius:16px;background:#081426;border:1px solid #385779;text-align:center;min-height:120px}}.node strong,.node small{{display:block}}.node small{{margin-top:10px;color:#aebed3}}.arrow{{font-size:30px;color:#66dec7}}.compartments{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}}.comp{{padding:15px;border-radius:15px;background:#0a1425;border:1px solid #314967;min-height:120px}}.comp.private{{border-color:#af5269}}.hash{{font-family:ui-monospace,monospace;word-break:break-all;color:#9fc2e8}}.boundary{{border-left:5px solid #ff7f9b}}@media(max-width:850px){{.gates,.compartments,.flow{{grid-template-columns:1fr}}.arrow{{transform:rotate(90deg);text-align:center}}}} </style></head><body><main>
<section class="hero"><span class="status">M56 FORMAL RUN · DENIED NOW</span><h1>不是有資料就直接跑：假的 readiness 不能自行開綠燈</h1><p class="headline">目前正確結果：真人 gate 未完成，所以 0 次正式模型呼叫、0 個正式結果。</p><p>這一層不提高分數；它在凍結程式邊界內阻止 synthetic fixture、假的 readiness、偷看的答案或換過的模型冒充正式實驗；它不是數位簽章或同機攻擊防護。</p></section>
<section class="panel"><h2>六道門全部通過，才會產生一次性 receipt</h2><div class="gates">{cards}</div></section>
<section class="panel"><h2>正式資料只走這條路</h2><div class="flow"><div class="node"><strong>M55 真人時間列</strong><small>兩人 → 裁決 → 30 rows</small></div><div class="arrow">→</div><div class="node"><strong>M56.2 Activation</strong><small>即時重驗 hashes、模型、硬體、分艙</small></div><div class="arrow">→</div><div class="node"><strong>一次正式 M56 run</strong><small>先完成七組 commitment，之後 scorer 才碰答案</small></div></div></section>
<section class="panel"><h2>答案不能混進生成</h2><div class="compartments"><div class="comp"><strong>generation</strong><p>packet、B0–B5/Ours views、Equation artifacts</p></div><div class="comp"><strong>commitments</strong><p>activation request、短效 receipt、prediction SHA</p></div><div class="comp private"><strong>scoring · PRIVATE</strong><p>outcome key；模型生成端不可取得</p></div><div class="comp"><strong>telemetry</strong><p>CPU、tokens、latency、peak memory、sensitivity</p></div></div></section>
<section class="panel"><h2>此機器已綁定的模型</h2><p><b>{html.escape(snapshot['model_name'])}</b> · {html.escape(snapshot['hardware']['machine_architecture'])} · Ollama {html.escape(snapshot['ollama_version'])}</p><p class="hash">manifest SHA-256 · {html.escape(model_hash)}</p></section>
<section class="panel boundary"><h2>證據邊界</h2><p>synthetic rehearsal hash：<span class="hash">{html.escape(report['synthetic_rehearsal']['rehearsal_hash'])}</span></p><p>它只能證明 hash 與分艙接線，不會也不能變成正式 receipt。目前尚未測 M56 模型勝負，未證明 Equation V1 有效，也未得出人類方程式。</p></section>
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
    parser.add_argument("--port", type=int, default=7910)
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
