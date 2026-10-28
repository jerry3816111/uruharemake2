#!/usr/bin/env python3
"""M56.4 post-commit, resource-gated separate formal scorer.

The public formal entry point accepts only a run id.  It revalidates the
outcome-blind M56.3 prediction commitment and actual-resource ledger before it
opens the private scoring compartment.  It performs no model calls and cannot
change predictions, outcomes, metrics, thresholds, or the primary contrast.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import random
from typing import Any

import m55_temporal_row_contract as temporal_m55
import m56_2_real_data_activation_envelope as activation_m56
import m56_3_lease_gated_generation_runner as runner_m56
import m56_blinded_execution_capsule as capsule_m56
import m56_fair_comparison_preflight as preflight_m56
from longitudinal_human_model.metrics import evaluate_predictions
from longitudinal_human_model.statistical_evaluation import (
    exact_mcnemar_pvalue,
    exact_sign_flip_pvalue,
    percentile_bootstrap_ci,
    probability_losses,
)


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/m56_4_separate_formal_scorer_v1.json"
PRIVATE_ROOT = activation_m56.DEFAULT_PRIVATE_ROOT

ACCESS_RECEIPT_SCHEMA = "uruha_m56_formal_scoring_access_receipt_v1"
SCORE_REPORT_SCHEMA = "uruha_m56_formal_separate_score_report_v1"
RESULT_COMMITMENT_SCHEMA = "uruha_m56_formal_score_commitment_v1"
PRESCORE_AUDIT_SCHEMA = "uruha_m56_formal_prescore_audit_v1"
AUDIT_SCHEMA = "uruha_m56_separate_formal_scorer_audit_v1"
REHEARSAL_SCHEMA = "uruha_m56_separate_scorer_synthetic_rehearsal_v1"

SCORE_REPORT_FILENAME = "formal_score_report.json"
RESULT_COMMITMENT_FILENAME = "formal_score_commitment.json"
ACCESS_RECEIPT_FILENAME = "formal_scoring_access_receipt.json"
PRESCORE_AUDIT_FILENAME = "formal_prescore_audit.json"

PRIMARY_CONTROL = capsule_m56.PRIMARY_CONTROL
PRIMARY_SYSTEM = capsule_m56.PRIMARY_SYSTEM
CONDITION_IDS = tuple(preflight_m56.CONDITION_IDS)

FORBIDDEN_REPORT_KEYS = {
    "raw_response",
    "raw_response_text",
    "response_text",
    "reasoning_trace",
    "chain_of_thought",
    "private_mental_state",
    "observable_input_paraphrase",
    "completed_event_summary",
    "source_text",
    "verbatim_text",
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
    if not isinstance(binding, dict) or set(binding) != {"path", "sha256"}:
        return False
    path = ROOT / str(binding.get("path") or "")
    expected = str(binding.get("sha256") or "")
    return path.is_file() and len(expected) == 64 and sha256_file(path) == expected


def validate_contract(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors: list[str] = []
    if set(contract) != {
        "schema", "version", "status", "single_changed_variable", "bindings", "schemas",
        "state_machine", "public_api", "prescore_boundary", "scoring", "result_boundary",
        "authorization", "claim_boundary",
    }:
        errors.append("contract.fields")
    if contract.get("schema") != "uruha_m56_separate_formal_scorer_contract_v1":
        errors.append("contract.schema")
    if contract.get("version") != "1.0.0":
        errors.append("contract.version")
    if contract.get("status") != "frozen_before_any_formal_m56_target_outcome_access_or_score":
        errors.append("contract.status")
    bindings = contract.get("bindings") or {}
    if set(bindings) != {
        "m56_preflight_freeze", "m56_preflight_contract", "m56_capsule_freeze",
        "m56_capsule_contract", "m56_3_runner_freeze", "m56_3_runner_contract", "m56_4_plan",
    }:
        errors.append("bindings.names")
    for name, binding in bindings.items():
        if not _binding_valid(binding):
            errors.append(f"binding:{name}")
    schemas = contract.get("schemas") or {}
    expected_schemas = {
        "scoring_access_receipt": ACCESS_RECEIPT_SCHEMA,
        "score_report": SCORE_REPORT_SCHEMA,
        "result_commitment": RESULT_COMMITMENT_SCHEMA,
        "prescore_audit": PRESCORE_AUDIT_SCHEMA,
        "scorer_audit": AUDIT_SCHEMA,
        "synthetic_rehearsal": REHEARSAL_SCHEMA,
    }
    if schemas != expected_schemas:
        errors.append("schemas")
    expected_states = [
        "prediction_release_revalidated",
        "resource_comparability_checked_before_outcome",
        "scoring_access_receipt_committed",
        "withheld_outcome_key_opened",
        "all_seven_conditions_scored",
        "frozen_primary_contrast_evaluated",
        "private_score_report_written",
        "result_sha256_committed",
    ]
    if contract.get("state_machine") != expected_states:
        errors.append("state_machine")
    public = contract.get("public_api") or {}
    if public.get("entry_point") != "execute_formal_scoring" or public.get("only_parameter") != "run_id":
        errors.append("public_api.entry")
    if any(public.get(name) is not False for name in (
        "prediction_injection_allowed", "outcome_injection_allowed",
        "metric_or_threshold_injection_allowed", "sensitivity_pass_injection_allowed",
        "result_or_readiness_injection_allowed",
    )):
        errors.append("public_api.injection")
    boundary = contract.get("prescore_boundary") or {}
    if boundary.get("required_prediction_rows") != 210 or boundary.get("required_conditions") != 7:
        errors.append("prescore.counts")
    if boundary.get("B5_Ours_prompt_difference_fraction_threshold") != 0.05:
        errors.append("prescore.token_threshold")
    if not all(boundary.get(name) is True for name in (
        "token_sensitivity_required_above_threshold",
        "missing_required_sensitivity_blocks_before_outcome",
    )):
        errors.append("prescore.required")
    if any(boundary.get(name) is not False for name in (
        "outcome_compartment_opened_before_release_validation",
        "outcome_compartment_opened_before_resource_gate",
    )):
        errors.append("prescore.outcome_order")
    if boundary.get("retry_count_required") != 0 or boundary.get("fallback_count_required") != 0:
        errors.append("prescore.retry")
    if boundary.get("generation_outcome_access_count_required") != 0:
        errors.append("prescore.generation_outcome")
    scoring = contract.get("scoring") or {}
    frozen = capsule_m56.load_contract().get("scoring") or {}
    expected_scoring = {
        "all_conditions_reported": True,
        "primary_control": PRIMARY_CONTROL,
        "primary_system": PRIMARY_SYSTEM,
        "proper_target": frozen.get("proper_target"),
        "acceptable_labels_apply_to": frozen.get("acceptable_labels_apply_to"),
        "co_primary": frozen.get("co_primary"),
        "paired_bootstrap_repetitions": frozen.get("bootstrap_repetitions"),
        "paired_bootstrap_seed": frozen.get("bootstrap_seed"),
        "sign_flip_exact_pair_limit": frozen.get("sign_flip_exact_pair_limit"),
        "sign_flip_monte_carlo_draws": frozen.get("sign_flip_monte_carlo_draws"),
        "sign_flip_seed": frozen.get("sign_flip_seed"),
        "top1_delta_minimum": frozen.get("top1_delta_minimum"),
        "ece_role": frozen.get("ece_role"),
        "negative_result_retained": True,
        "post_result_control_or_metric_selection_allowed": False,
    }
    if scoring != expected_scoring:
        errors.append("scoring.frozen_mismatch")
    result = contract.get("result_boundary") or {}
    if not all(result.get(name) is True for name in (
        "atomic_private_score_report", "sha256_result_commitment_required",
        "identical_finalize_only_after_partial_commit",
    )):
        errors.append("result.required")
    if any(result.get(name) is not False for name in (
        "report_contains_raw_source_or_model_response", "report_contains_reasoning_trace",
        "production_memory_write", "external_deployment", "broad_human_equation_claim",
    )):
        errors.append("result.excess")
    authorization = contract.get("authorization") or {}
    if any(authorization.get(name) is not False for name in (
        "current_formal_scoring", "current_target_outcome_access", "current_formal_result",
        "synthetic_rehearsal_authorizes_formal_result", "production_memory_write",
        "external_deployment",
    )):
        errors.append("authorization")
    return {
        "valid": not errors,
        "errors": errors,
        "binding_count": len(bindings),
        "contract_hash": digest(contract),
    }


def _run_root(run_id: str) -> Path:
    if not isinstance(run_id, str) or not run_id or run_id in (".", "..") or "/" in run_id or "\\" in run_id:
        raise ValueError("run_id must be one safe path component")
    root = (PRIVATE_ROOT / run_id).resolve()
    if root.parent != PRIVATE_ROOT.resolve():
        raise ValueError("run root escapes private root")
    return root


def _paths(run_id: str) -> dict[str, Path]:
    root = _run_root(run_id)
    return {
        "root": root,
        "generation": root / "generation",
        "commitments": root / "commitments",
        "scoring": root / "scoring",
        "telemetry": root / "telemetry",
    }


def _atomic_write_json(path: Path, value: dict[str, Any], *, exclusive: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if exclusive:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
        except Exception:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            raise
        return
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temp.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def _write_or_validate_identical(path: Path, value: dict[str, Any]) -> str:
    if path.exists():
        existing = load_json(path)
        if existing != value:
            raise ValueError(f"existing immutable artifact differs: {path.name}")
        return "validated_existing_identical"
    _atomic_write_json(path, value, exclusive=True)
    return "created"


def _find_forbidden_keys(value: Any, *, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if key in FORBIDDEN_REPORT_KEYS:
                found.append(path)
            found.extend(_find_forbidden_keys(child, prefix=path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_find_forbidden_keys(child, prefix=f"{prefix}[{index}]"))
    return found


def load_prescore_inputs(run_id: str) -> dict[str, dict[str, Any]]:
    """Load every required artifact except the private scoring compartment."""

    paths = _paths(run_id)
    for name in ("generation", "commitments", "telemetry"):
        if not paths[name].is_dir():
            raise FileNotFoundError(f"missing pre-score compartment: {name}")
    generation = paths["generation"]
    commitments = paths["commitments"]
    base = {
        "request": load_json(commitments / "activation_request.json"),
        "receipt": load_json(commitments / activation_m56.FORMAL_RECEIPT_FILENAME),
        "lease": load_json(commitments / activation_m56.FORMAL_LEASE_FILENAME),
        "packet": load_json(generation / "prediction_packet.json"),
        "manifest": load_json(generation / "run_manifest.json"),
        "capsule": load_json(generation / "execution_capsule.json"),
        "bundle": load_json(generation / "equation_artifacts.json"),
        "snapshot": load_json(generation / "runtime_snapshot.json"),
    }
    return {
        **base,
        "schedule": load_json(paths["generation"] / runner_m56.SCHEDULE_FILENAME),
        "submission": load_json(paths["generation"] / runner_m56.SUBMISSION_FILENAME),
        "commitment": load_json(paths["commitments"] / runner_m56.COMMITMENT_FILENAME),
        "release": load_json(paths["commitments"] / runner_m56.SCORING_RELEASE_FILENAME),
        "call_ledger": load_json(paths["telemetry"] / runner_m56.CALL_LEDGER_FILENAME),
    }


_CALL_FIELDS = {
    "schema", "phase", "step_id", "prompt_hash", "raw_response_hash",
    "prompt_tokens", "completion_tokens", "latency_seconds", "process_cpu_seconds",
    "process_peak_rss_bytes", "ollama_rss_bytes", "total_duration_ns", "load_duration_ns",
    "prompt_eval_duration_ns", "eval_duration_ns", "model_reported",
    "transport_attempt_count", "retry_count", "fallback_count",
}

_RESOURCE_FIELDS = (
    "prompt_hash", "raw_response_hash", "prompt_tokens", "completion_tokens",
    "latency_seconds", "process_cpu_seconds", "process_peak_rss_bytes", "ollama_rss_bytes",
    "total_duration_ns", "load_duration_ns", "prompt_eval_duration_ns", "eval_duration_ns",
    "transport_attempt_count", "retry_count", "fallback_count",
)


def validate_call_ledger(
    ledger: dict[str, Any], schedule: dict[str, Any], submission: dict[str, Any],
    commitment: dict[str, Any], lease: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    expected_fields = {
        "schema", "version", "status", "lease_hash", "schedule_hash", "call_count",
        "required_call_count", "calls", "equation_artifact_rematerialization_cpu_seconds",
        "retry_count", "fallback_count", "generation_target_outcome_access_count", "ledger_hash",
    }
    if not isinstance(ledger, dict) or set(ledger) != expected_fields:
        return {"valid": False, "errors": ["ledger.fields"], "call_count": 0}
    unhashed = {key: value for key, value in ledger.items() if key != "ledger_hash"}
    if ledger.get("ledger_hash") != digest(unhashed):
        errors.append("ledger.hash")
    if ledger.get("schema") != "uruha_m56_formal_call_ledger_v1" or ledger.get("version") != "1.0.0":
        errors.append("ledger.schema_or_version")
    if ledger.get("status") != "complete_before_prediction_commitment":
        errors.append("ledger.status")
    for name, expected in (
        ("lease_hash", lease.get("lease_hash")),
        ("schedule_hash", schedule.get("schedule_hash")),
        ("required_call_count", schedule.get("required_model_call_count")),
        ("call_count", commitment.get("model_call_count")),
    ):
        if ledger.get(name) != expected:
            errors.append(f"ledger.{name}")
    if ledger.get("retry_count") != 0 or ledger.get("fallback_count") != 0:
        errors.append("ledger.retry")
    if ledger.get("generation_target_outcome_access_count") != 0:
        errors.append("ledger.outcome_access")
    if ledger.get("equation_artifact_rematerialization_cpu_seconds") != submission.get("equation_artifact_rematerialization_cpu_seconds"):
        errors.append("ledger.equation_cpu")
    calls = ledger.get("calls")
    if not isinstance(calls, list):
        calls = []
        errors.append("ledger.calls")
    expected_steps = [
        ("b4_summary", row["step_id"])
        for row in schedule.get("summary_steps") or [] if row.get("model_call_required")
    ] + [
        ("prediction", row["step_id"])
        for row in schedule.get("prediction_steps") or [] if row.get("model_call_required")
    ]
    if [(row.get("phase"), row.get("step_id")) for row in calls if isinstance(row, dict)] != expected_steps:
        errors.append("ledger.call_order")
    summaries = {row["summary_task_id"]: row for row in submission.get("summary_artifacts") or [] if isinstance(row, dict)}
    predictions = {row["task_id"]: row for row in submission.get("prediction_rows") or [] if isinstance(row, dict)}
    for index, call in enumerate(calls):
        scope = f"call[{index}]"
        if not isinstance(call, dict) or set(call) != _CALL_FIELDS:
            errors.append(f"{scope}.fields")
            continue
        if call.get("schema") != runner_m56.CALL_SCHEMA:
            errors.append(f"{scope}.schema")
        source = summaries.get(call.get("step_id")) if call.get("phase") == "b4_summary" else predictions.get(call.get("step_id"))
        if not source:
            errors.append(f"{scope}.source")
            continue
        for name in _RESOURCE_FIELDS:
            if call.get(name) != source.get(name):
                errors.append(f"{scope}.{name}")
        if call.get("model_reported") != source.get("model_name"):
            errors.append(f"{scope}.model")
    if ledger.get("call_count") != len(calls) or len(calls) != len(expected_steps):
        errors.append("ledger.call_count_exact")
    if _find_forbidden_keys(ledger):
        errors.append("ledger.raw_or_reasoning_content")
    return {
        "valid": not errors,
        "errors": errors,
        "call_count": len(calls),
        "ledger_hash": ledger.get("ledger_hash"),
    }


def _resource_totals(submission: dict[str, Any]) -> dict[str, Any]:
    totals = {
        condition: {
            "prediction_model_calls": 0,
            "semantic_model_calls": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "latency_seconds": 0.0,
            "process_cpu_seconds": 0.0,
            "peak_process_rss_bytes": 0,
            "peak_ollama_rss_bytes": 0,
            "total_duration_ns": 0,
            "load_duration_ns": 0,
            "prompt_eval_duration_ns": 0,
            "eval_duration_ns": 0,
        }
        for condition in CONDITION_IDS
    }
    for row in submission.get("prediction_rows") or []:
        target = totals[row["condition_id"]]
        target["prediction_model_calls"] += int(row["prediction_model_call_count"])
        target["semantic_model_calls"] += int(row["semantic_model_call_count"])
        target["prompt_tokens"] += int(row["prompt_tokens"])
        target["completion_tokens"] += int(row["completion_tokens"])
        target["latency_seconds"] += float(row["latency_seconds"])
        target["process_cpu_seconds"] += float(row["process_cpu_seconds"])
        target["peak_process_rss_bytes"] = max(target["peak_process_rss_bytes"], int(row["process_peak_rss_bytes"]))
        target["peak_ollama_rss_bytes"] = max(target["peak_ollama_rss_bytes"], int(row["ollama_rss_bytes"]))
        for name in ("total_duration_ns", "load_duration_ns", "prompt_eval_duration_ns", "eval_duration_ns"):
            target[name] += int(row[name])
    summary = {
        "model_calls": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "latency_seconds": 0.0,
        "process_cpu_seconds": 0.0,
        "peak_process_rss_bytes": 0,
        "peak_ollama_rss_bytes": 0,
        "total_duration_ns": 0,
        "load_duration_ns": 0,
        "prompt_eval_duration_ns": 0,
        "eval_duration_ns": 0,
    }
    for row in submission.get("summary_artifacts") or []:
        summary["model_calls"] += int(row["model_call_count"])
        summary["prompt_tokens"] += int(row["prompt_tokens"])
        summary["completion_tokens"] += int(row["completion_tokens"])
        summary["latency_seconds"] += float(row["latency_seconds"])
        summary["process_cpu_seconds"] += float(row["process_cpu_seconds"])
        summary["peak_process_rss_bytes"] = max(summary["peak_process_rss_bytes"], int(row["process_peak_rss_bytes"]))
        summary["peak_ollama_rss_bytes"] = max(summary["peak_ollama_rss_bytes"], int(row["ollama_rss_bytes"]))
        for name in ("total_duration_ns", "load_duration_ns", "prompt_eval_duration_ns", "eval_duration_ns"):
            summary[name] += int(row[name])
    return {
        "condition_resource_totals": totals,
        "b4_summary_build_resource_totals": summary,
        "equation_artifact_rematerialization_cpu_seconds": submission["equation_artifact_rematerialization_cpu_seconds"],
    }


def validate_prescore_inputs(run_id: str, rows: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    errors: list[str] = []
    contract_report = validate_contract()
    errors.extend(f"contract:{name}" for name in contract_report["errors"])
    try:
        rows = deepcopy(rows or load_prescore_inputs(run_id))
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        return {"valid": False, "scoring_ready": False, "errors": errors + [f"inputs:{exc}"], "blockers": []}
    base_names = ("request", "receipt", "lease", "packet", "manifest", "capsule", "bundle", "snapshot")
    base = {name: rows[name] for name in base_names}
    runner_report = runner_m56.validate_runner_inputs(run_id, base)
    errors.extend(f"runner:{name}" for name in runner_report["errors"])
    schedule = rows["schedule"]
    submission = rows["submission"]
    commitment = rows["commitment"]
    release = rows["release"]
    lease = rows["lease"]
    schedule_report = runner_m56.validate_generation_schedule(
        schedule, rows["packet"], rows["manifest"], rows["capsule"], rows["bundle"], lease.get("lease_hash")
    )
    errors.extend(f"schedule:{name}" for name in schedule_report["errors"])
    submission_report = runner_m56.validate_formal_submission(
        submission, schedule, rows["packet"], rows["manifest"], rows["capsule"], rows["bundle"], lease
    )
    errors.extend(f"submission:{name}" for name in submission_report["errors"])
    commitment_report = runner_m56.validate_prediction_commitment(
        commitment, submission, schedule, lease, submission_report
    )
    errors.extend(f"commitment:{name}" for name in commitment_report["errors"])
    release_report = runner_m56.validate_scoring_release(
        release, commitment, submission, schedule, lease, submission_report
    )
    errors.extend(f"release:{name}" for name in release_report["errors"])
    ledger_report = validate_call_ledger(rows["call_ledger"], schedule, submission, commitment, lease)
    errors.extend(f"ledger:{name}" for name in ledger_report["errors"])
    request = rows["request"]
    for name in ("outcome_key_hash", "split_report_hash"):
        if not isinstance(request.get(name), str) or len(request[name]) != 64:
            errors.append(f"request.{name}")
    max_difference = float(submission_report.get("max_primary_prompt_token_difference_fraction") or 0.0)
    threshold = float(load_contract()["prescore_boundary"]["B5_Ours_prompt_difference_fraction_threshold"])
    sensitivity_required = max_difference > threshold
    blockers = ["exact_token_sensitivity_required_before_outcome_access"] if sensitivity_required else []
    return {
        "valid": not errors,
        "scoring_ready": not errors and not blockers,
        "errors": errors,
        "blockers": blockers,
        "prediction_row_count": submission_report.get("row_count", 0),
        "condition_count": len(CONDITION_IDS),
        "model_call_count": ledger_report.get("call_count", 0),
        "generation_target_outcome_access_count": 0,
        "max_primary_prompt_token_difference_fraction": max_difference,
        "token_difference_threshold": threshold,
        "exact_token_sensitivity_required": sensitivity_required,
        "prescore_hash": digest({
            "contract_hash": contract_report["contract_hash"],
            "run_id": run_id,
            "release_hash": release.get("release_hash"),
            "submission_hash": submission.get("submission_hash"),
            "ledger_hash": rows["call_ledger"].get("ledger_hash"),
            "max_primary_prompt_token_difference_fraction": max_difference,
            "exact_token_sensitivity_required": sensitivity_required,
        }),
    }


def build_prescore_audit(run_id: str, rows: dict[str, dict[str, Any]], report: dict[str, Any]) -> dict[str, Any]:
    value = {
        "schema": PRESCORE_AUDIT_SCHEMA,
        "version": "1.0.0",
        "status": "ready_for_private_outcome_join" if report["scoring_ready"] else "blocked_before_private_outcome_access",
        "run_id": run_id,
        "scorer_contract_hash": validate_contract()["contract_hash"],
        "lease_hash": rows["lease"]["lease_hash"],
        "schedule_hash": rows["schedule"]["schedule_hash"],
        "submission_hash": rows["submission"]["submission_hash"],
        "prediction_commitment_hash": rows["commitment"]["commitment_hash"],
        "scoring_release_hash": rows["release"]["release_hash"],
        "call_ledger_hash": rows["call_ledger"]["ledger_hash"],
        "prediction_row_count": report["prediction_row_count"],
        "condition_count": report["condition_count"],
        "generation_model_call_count": report["model_call_count"],
        "scorer_model_call_count": 0,
        "generation_target_outcome_access_count": 0,
        "scorer_target_outcome_access_before_gate": 0,
        "max_primary_prompt_token_difference_fraction": report["max_primary_prompt_token_difference_fraction"],
        "token_difference_threshold": report["token_difference_threshold"],
        "exact_token_sensitivity_required": report["exact_token_sensitivity_required"],
        "blockers": deepcopy(report["blockers"]),
    }
    value["prescore_audit_hash"] = digest(value)
    return value


def build_scoring_access_receipt(run_id: str, rows: dict[str, dict[str, Any]], prescore: dict[str, Any]) -> dict[str, Any]:
    if prescore.get("status") != "ready_for_private_outcome_join":
        raise PermissionError("outcome access receipt requires a passed pre-score gate")
    value = {
        "schema": ACCESS_RECEIPT_SCHEMA,
        "version": "1.0.0",
        "status": "single_logical_private_outcome_join_authorized",
        "run_id": run_id,
        "scorer_contract_hash": validate_contract()["contract_hash"],
        "prescore_audit_hash": prescore["prescore_audit_hash"],
        "scoring_release_hash": rows["release"]["release_hash"],
        "prediction_commitment_hash": rows["commitment"]["commitment_hash"],
        "expected_outcome_key_hash": rows["request"]["outcome_key_hash"],
        "expected_split_report_hash": rows["request"]["split_report_hash"],
        "generation_outcome_access_authorized": False,
        "scorer_outcome_join_authorization_count": 1,
        "model_call_authorized": False,
        "production_memory_write_authorized": False,
        "external_deployment_authorized": False,
    }
    value["access_receipt_hash"] = digest(value)
    return value


def load_outcome_inputs(run_id: str) -> dict[str, dict[str, Any]]:
    """Open the private scoring compartment only after the pre-score gate."""

    paths = _paths(run_id)
    if not paths["scoring"].is_dir():
        raise FileNotFoundError("missing private scoring compartment")
    return {
        "outcome_key": load_json(paths["scoring"] / "private_outcome_key.json"),
        "split_report": load_json(paths["scoring"] / "split_report.json"),
    }


def _parse_time(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed.astimezone(timezone.utc)


def validate_outcome_inputs(
    outcome_key: dict[str, Any], split_report: dict[str, Any], packet: dict[str, Any], request: dict[str, Any]
) -> dict[str, Any]:
    errors = list(capsule_m56.validate_outcome_key(outcome_key, packet, split_report)["errors"])
    expected_outcome_key_fields = {
        "schema", "version", "status", "data_kind", "contract_hash", "dataset_hash",
        "sample_count", "outcomes", "generation_process_access_allowed",
    }
    if set(outcome_key) != expected_outcome_key_fields:
        errors.append("outcome_key.fields")
    if outcome_key.get("version") != "1.0.0" or outcome_key.get("status") != "private_withheld_until_prediction_commitment":
        errors.append("outcome_key.version_or_status")
    expected_split_fields = {
        "schema", "data_kind", "sample_count", "prediction_packet_hash", "outcome_key_hash",
        "outcome_key_exposed_to_generation", "future_leakage_violations", "model_call_count",
        "m56_result_created", "formal_target_claim", "report_hash",
    }
    if set(split_report) != expected_split_fields:
        errors.append("split_report.fields")
    unhashed = {key: value for key, value in split_report.items() if key != "report_hash"}
    if split_report.get("report_hash") != digest(unhashed):
        errors.append("split_report.hash")
    if digest(outcome_key) != request.get("outcome_key_hash"):
        errors.append("outcome_key.activation_binding")
    if digest(split_report) != request.get("split_report_hash"):
        errors.append("split_report.activation_binding")
    if split_report.get("model_call_count") != 0 or split_report.get("m56_result_created") is not False:
        errors.append("split_report.pre_result_boundary")
    if split_report.get("formal_target_claim") is not False:
        errors.append("split_report.formal_claim")
    packet_rows = {row["sample_id"]: row for row in packet.get("model_inputs") or []}
    label_orders = []
    for index, outcome in enumerate(outcome_key.get("outcomes") or []):
        scope = f"outcome[{index}]"
        packet_row = packet_rows.get(outcome.get("sample_id")) or {}
        model_input = packet_row.get("model_input") or {}
        labels = model_input.get("candidate_behavior_labels") or []
        label_orders.append(labels)
        try:
            prediction_time = _parse_time(model_input.get("prediction_time"))
            observed = _parse_time(outcome.get("actual_observed_at"))
            source = _parse_time(outcome.get("source_timestamp"))
            if not prediction_time < observed < source:
                errors.append(f"{scope}.temporal_order")
        except (TypeError, ValueError):
            errors.append(f"{scope}.timestamps")
    if not label_orders or any(labels != label_orders[0] for labels in label_orders):
        errors.append("outcome.label_order")
    return {
        "valid": not errors,
        "errors": errors,
        "outcome_count": len(outcome_key.get("outcomes") or []),
        "label_order": deepcopy(label_orders[0]) if label_orders else [],
        "outcome_key_hash": digest(outcome_key),
        "split_report_hash": digest(split_report),
    }


def _monte_carlo_sign_flip(values: list[float], *, draws: int, seed: int) -> float:
    observed = abs(sum(values) / len(values))
    rng = random.Random(seed)
    extreme = 0
    for _ in range(draws):
        statistic = abs(sum(value if rng.randrange(2) else -value for value in values) / len(values))
        extreme += int(statistic >= observed - 1e-15)
    return (extreme + 1) / (draws + 1)


def _paired_primary(joined: list[dict[str, Any]], scoring: dict[str, Any]) -> dict[str, Any]:
    controls = {row["sample_id"]: row for row in joined if row["condition_id"] == PRIMARY_CONTROL}
    systems = {row["sample_id"]: row for row in joined if row["condition_id"] == PRIMARY_SYSTEM}
    if set(controls) != set(systems) or len(controls) != 30:
        raise ValueError("primary conditions require the same 30 samples")
    brier_deltas: list[float] = []
    nll_deltas: list[float] = []
    top1_deltas: list[float] = []
    system_only = control_only = 0
    pairs = []
    for sample_id in sorted(controls):
        control = probability_losses(controls[sample_id])
        system = probability_losses(systems[sample_id])
        brier_delta = system["brier"] - control["brier"]
        nll_delta = system["nll"] - control["nll"]
        top1_delta = system["top1"] - control["top1"]
        brier_deltas.append(brier_delta)
        nll_deltas.append(nll_delta)
        top1_deltas.append(top1_delta)
        system_only += int(top1_delta > 0)
        control_only += int(top1_delta < 0)
        pairs.append({
            "sample_id": sample_id,
            "brier_delta_ours_minus_b5": brier_delta,
            "nll_delta_ours_minus_b5": nll_delta,
            "top1_delta_ours_minus_b5": top1_delta,
        })
    repetitions = int(scoring["paired_bootstrap_repetitions"])
    seed = int(scoring["paired_bootstrap_seed"])
    brier_ci = percentile_bootstrap_ci(brier_deltas, repetitions=repetitions, seed=seed)
    nll_ci = percentile_bootstrap_ci(nll_deltas, repetitions=repetitions, seed=seed + 1)

    def sign_flip(values: list[float], metric_seed: int) -> tuple[float, str]:
        if len(values) <= int(scoring["sign_flip_exact_pair_limit"]):
            return exact_sign_flip_pvalue(values), "exact"
        return _monte_carlo_sign_flip(
            values, draws=int(scoring["sign_flip_monte_carlo_draws"]), seed=metric_seed
        ), "prospective_deterministic_monte_carlo"

    brier_p, brier_method = sign_flip(brier_deltas, int(scoring["sign_flip_seed"]))
    nll_p, nll_method = sign_flip(nll_deltas, int(scoring["sign_flip_seed"]) + 1)
    top1_delta = sum(top1_deltas) / len(top1_deltas)
    proper_gate = brier_ci[1] < 0 and nll_ci[1] < 0
    top1_gate = top1_delta >= float(scoring["top1_delta_minimum"])
    return {
        "control": PRIMARY_CONTROL,
        "system": PRIMARY_SYSTEM,
        "sample_count": len(pairs),
        "delta_definition": "Ours minus B5; negative Brier/NLL is better",
        "brier": {
            "mean_delta": sum(brier_deltas) / len(brier_deltas),
            "bootstrap_95_ci": brier_ci,
            "sign_flip_two_sided_p": brier_p,
            "sign_flip_method": brier_method,
        },
        "nll": {
            "mean_delta": sum(nll_deltas) / len(nll_deltas),
            "bootstrap_95_ci": nll_ci,
            "sign_flip_two_sided_p": nll_p,
            "sign_flip_method": nll_method,
        },
        "top1": {
            "mean_delta": top1_delta,
            "system_only_correct": system_only,
            "control_only_correct": control_only,
            "exact_mcnemar_two_sided_p": exact_mcnemar_pvalue(system_only, control_only),
        },
        "gates": {
            "both_proper_score_upper_bounds_below_zero": proper_gate,
            "top1_delta_at_least_minus_0_05": top1_gate,
            "formal_success": proper_gate and top1_gate,
        },
        "pairs": pairs,
    }


def build_score_report(
    run_id: str, rows: dict[str, dict[str, Any]], prescore: dict[str, Any],
    access_receipt: dict[str, Any], outcome_key: dict[str, Any], split_report: dict[str, Any],
) -> dict[str, Any]:
    if not prescore.get("scoring_ready"):
        raise PermissionError("score report requires a passed pre-score gate")
    outcome_report = validate_outcome_inputs(outcome_key, split_report, rows["packet"], rows["request"])
    if not outcome_report["valid"]:
        raise ValueError("private outcome inputs invalid: " + "; ".join(outcome_report["errors"]))
    outcomes = {row["sample_id"]: row for row in outcome_key["outcomes"]}
    joined = [
        {
            "sample_id": row["sample_id"],
            "condition_id": row["condition_id"],
            "probabilities": deepcopy(row["probabilities"]),
            "actual_observed_behavior": outcomes[row["sample_id"]]["actual_observed_behavior"],
            "acceptable_behavior_labels": deepcopy(outcomes[row["sample_id"]]["acceptable_behavior_labels"]),
        }
        for row in rows["submission"]["prediction_rows"]
    ]
    labels = outcome_report["label_order"]
    condition_metrics = {
        condition: evaluate_predictions(
            [row for row in joined if row["condition_id"] == condition], labels
        )
        for condition in CONDITION_IDS
    }
    comparison = _paired_primary(joined, load_contract()["scoring"])
    formal_success = comparison["gates"]["formal_success"]
    resources = _resource_totals(rows["submission"])
    value = {
        "schema": SCORE_REPORT_SCHEMA,
        "version": "1.0.0",
        "status": "formal_m56_score_complete",
        "data_kind": temporal_m55.REAL_KIND,
        "run_id": run_id,
        "scorer_contract_hash": validate_contract()["contract_hash"],
        "activation_contract_hash": rows["capsule"]["activation_contract_hash"],
        "runner_contract_hash": rows["submission"]["runner_contract_hash"],
        "lease_hash": rows["lease"]["lease_hash"],
        "dataset_hash": rows["packet"]["dataset_hash"],
        "prediction_packet_hash": digest(rows["packet"]),
        "run_manifest_hash": digest(rows["manifest"]),
        "capsule_hash": rows["capsule"]["capsule_hash"],
        "equation_artifact_bundle_hash": rows["bundle"]["artifact_bundle_hash"],
        "schedule_hash": rows["schedule"]["schedule_hash"],
        "submission_hash": rows["submission"]["submission_hash"],
        "prediction_commitment_hash": rows["commitment"]["commitment_hash"],
        "scoring_release_hash": rows["release"]["release_hash"],
        "call_ledger_hash": rows["call_ledger"]["ledger_hash"],
        "prescore_audit_hash": access_receipt["prescore_audit_hash"],
        "scoring_access_receipt_hash": access_receipt["access_receipt_hash"],
        "outcome_key_hash": outcome_report["outcome_key_hash"],
        "split_report_hash": outcome_report["split_report_hash"],
        "sample_count": 30,
        "condition_count": 7,
        "prediction_row_count": 210,
        "condition_metrics": condition_metrics,
        "primary_comparison": comparison,
        "evidence_audit": {
            "unauthorized_or_post_cutoff_evidence_count": 0,
            "future_leakage_violations": 0,
            "generation_target_outcome_access_count": 0,
            "scorer_outcome_join_authorization_count": 1,
            "semantic_irrelevant_memory_ground_truth": "unavailable_without_separate_human_annotation",
        },
        "resource_audit": {
            "max_primary_prompt_token_difference_fraction": prescore["max_primary_prompt_token_difference_fraction"],
            "token_difference_threshold": prescore["token_difference_threshold"],
            "exact_token_sensitivity_required": False,
            "resource_gate_passed_before_outcome_access": True,
            **resources,
        },
        "scorer_model_call_count": 0,
        "formal_result_created": True,
        "decision": "formal_gate_pass" if formal_success else "formal_gate_fail_retained",
        "claim_scope": "frozen_M55_M56_dataset_conditions_model_hardware_only",
        "production_memory_write_authorized": False,
        "external_deployment_authorized": False,
        "broad_human_equation_claim_authorized": False,
        "claim_boundary": "The decision applies only to the frozen M55/M56 dataset, conditions, model and hardware; it is not private-state truth, a solved human-brain equation, full-pipeline readiness or production authorization.",
    }
    forbidden = _find_forbidden_keys(value)
    if forbidden:
        raise ValueError("score report contains forbidden content: " + "; ".join(forbidden))
    value["score_report_hash"] = digest(value)
    return value


def validate_score_report(report: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(report, dict):
        return {"valid": False, "errors": ["report.object"]}
    expected_fields = {
        "schema", "version", "status", "data_kind", "run_id", "scorer_contract_hash",
        "activation_contract_hash", "runner_contract_hash", "lease_hash", "dataset_hash",
        "prediction_packet_hash", "run_manifest_hash", "capsule_hash",
        "equation_artifact_bundle_hash", "schedule_hash", "submission_hash",
        "prediction_commitment_hash", "scoring_release_hash", "call_ledger_hash",
        "prescore_audit_hash", "scoring_access_receipt_hash", "outcome_key_hash",
        "split_report_hash", "sample_count", "condition_count", "prediction_row_count",
        "condition_metrics", "primary_comparison", "evidence_audit", "resource_audit",
        "scorer_model_call_count", "formal_result_created", "decision", "claim_scope",
        "production_memory_write_authorized", "external_deployment_authorized",
        "broad_human_equation_claim_authorized", "claim_boundary", "score_report_hash",
    }
    if set(report) != expected_fields:
        errors.append("report.fields")
    unhashed = {key: value for key, value in report.items() if key != "score_report_hash"}
    if report.get("score_report_hash") != digest(unhashed):
        errors.append("report.hash")
    if report.get("schema") != SCORE_REPORT_SCHEMA or report.get("status") != "formal_m56_score_complete":
        errors.append("report.schema_or_status")
    if report.get("data_kind") != temporal_m55.REAL_KIND:
        errors.append("report.data_kind")
    if report.get("sample_count") != 30 or report.get("condition_count") != 7 or report.get("prediction_row_count") != 210:
        errors.append("report.counts")
    if set(report.get("condition_metrics") or {}) != set(CONDITION_IDS):
        errors.append("report.conditions")
    elif any((report["condition_metrics"][name] or {}).get("sample_count") != 30 for name in CONDITION_IDS):
        errors.append("report.condition_sample_counts")
    comparison = report.get("primary_comparison") or {}
    if comparison.get("control") != PRIMARY_CONTROL or comparison.get("system") != PRIMARY_SYSTEM:
        errors.append("report.primary")
    if comparison.get("sample_count") != 30:
        errors.append("report.primary_sample_count")
    expected_decision = "formal_gate_pass" if ((comparison.get("gates") or {}).get("formal_success") is True) else "formal_gate_fail_retained"
    if report.get("decision") != expected_decision:
        errors.append("report.decision")
    if report.get("scorer_model_call_count") != 0:
        errors.append("report.model_calls")
    if report.get("formal_result_created") is not True:
        errors.append("report.result")
    if any(report.get(name) is not False for name in (
        "production_memory_write_authorized", "external_deployment_authorized",
        "broad_human_equation_claim_authorized",
    )):
        errors.append("report.excess_authority")
    forbidden = _find_forbidden_keys(report)
    errors.extend(f"report.forbidden:{name}" for name in forbidden)
    return {"valid": not errors, "errors": errors, "score_report_hash": report.get("score_report_hash")}


def build_result_commitment(report: dict[str, Any]) -> dict[str, Any]:
    validation = validate_score_report(report)
    if not validation["valid"]:
        raise ValueError("invalid score report cannot be committed")
    value = {
        "schema": RESULT_COMMITMENT_SCHEMA,
        "version": "1.0.0",
        "status": "formal_m56_scoped_result_sha256_committed",
        "run_id": report["run_id"],
        "scorer_contract_hash": report["scorer_contract_hash"],
        "lease_hash": report["lease_hash"],
        "submission_hash": report["submission_hash"],
        "prediction_commitment_hash": report["prediction_commitment_hash"],
        "scoring_release_hash": report["scoring_release_hash"],
        "outcome_key_hash": report["outcome_key_hash"],
        "split_report_hash": report["split_report_hash"],
        "score_report_hash": report["score_report_hash"],
        "decision": report["decision"],
        "scorer_model_call_count": 0,
        "scorer_outcome_join_authorization_count": 1,
        "claim_scope": report["claim_scope"],
        "production_memory_write_authorized": False,
        "external_deployment_authorized": False,
        "broad_human_equation_claim_authorized": False,
    }
    value["result_commitment_hash"] = digest(value)
    return value


def validate_result_commitment(commitment: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    errors = list(validate_score_report(report)["errors"])
    expected = build_result_commitment(report) if not errors else None
    if expected is None or commitment != expected:
        errors.append("result_commitment.content_or_hash")
    return {
        "valid": not errors,
        "errors": errors,
        "result_commitment_hash": commitment.get("result_commitment_hash") if isinstance(commitment, dict) else None,
    }


def execute_formal_scoring(run_id: str) -> dict[str, Any]:
    """Score one already committed formal run; no caller-supplied data or rules."""

    paths = _paths(run_id)
    rows = load_prescore_inputs(run_id)
    prescore_report = validate_prescore_inputs(run_id, rows)
    if not prescore_report["valid"]:
        raise PermissionError("pre-score integrity gate failed: " + "; ".join(prescore_report["errors"]))
    prescore_audit = build_prescore_audit(run_id, rows, prescore_report)
    _write_or_validate_identical(paths["telemetry"] / PRESCORE_AUDIT_FILENAME, prescore_audit)
    if not prescore_report["scoring_ready"]:
        return {
            "status": "formal_scoring_blocked_before_outcome_access",
            "blockers": deepcopy(prescore_report["blockers"]),
            "prescore_audit_hash": prescore_audit["prescore_audit_hash"],
            "scorer_target_outcome_access_count": 0,
            "scorer_model_call_count": 0,
            "formal_result_created": False,
        }
    access_receipt = build_scoring_access_receipt(run_id, rows, prescore_audit)
    _write_or_validate_identical(paths["commitments"] / ACCESS_RECEIPT_FILENAME, access_receipt)
    outcome_rows = load_outcome_inputs(run_id)
    report = build_score_report(
        run_id, rows, prescore_report, access_receipt,
        outcome_rows["outcome_key"], outcome_rows["split_report"],
    )
    report_status = _write_or_validate_identical(paths["scoring"] / SCORE_REPORT_FILENAME, report)
    result_commitment = build_result_commitment(report)
    commitment_status = _write_or_validate_identical(
        paths["commitments"] / RESULT_COMMITMENT_FILENAME, result_commitment
    )
    return {
        "status": "formal_scoring_complete_result_committed",
        "decision": report["decision"],
        "score_report_hash": report["score_report_hash"],
        "result_commitment_hash": result_commitment["result_commitment_hash"],
        "score_report_write": report_status,
        "result_commitment_write": commitment_status,
        "scorer_outcome_join_authorization_count": 1,
        "scorer_model_call_count": 0,
        "formal_result_created": True,
        "claim_scope": report["claim_scope"],
    }


def build_synthetic_rehearsal() -> dict[str, Any]:
    value = {
        "schema": REHEARSAL_SCHEMA,
        "version": "1.0.0",
        "status": "no_call_no_outcome_state_machine_rehearsal_only",
        "stages": deepcopy(load_contract()["state_machine"]),
        "human_evidence_count": 0,
        "model_call_count": 0,
        "target_outcome_access_count": 0,
        "formal_scoring_authorized": False,
        "formal_result_created": False,
        "production_memory_write_authorized": False,
        "claim_boundary": "State-machine wiring only; no human labels, model predictions, outcome join, score or formal result.",
    }
    value["rehearsal_hash"] = digest(value)
    return value


def build_live_audit() -> dict[str, Any]:
    contract_report = validate_contract()
    generation = runner_m56.build_live_audit()
    counts = deepcopy(generation["counts"])
    value = {
        "schema": AUDIT_SCHEMA,
        "version": "1.0.0",
        "status": "formal_scoring_denied_waiting_for_human_chain",
        "contract_valid": contract_report["valid"],
        "contract_hash": contract_report["contract_hash"],
        "counts": counts,
        "formal_prediction_release_available": False,
        "formal_scoring_authorized": False,
        "scorer_target_outcome_access_count": 0,
        "scorer_model_call_count": 0,
        "formal_score_report_created": False,
        "formal_result_commitment_created": False,
        "blocking_gates": [name for name, passed in generation["gates"].items() if not passed],
        "claim_boundary": load_contract()["claim_boundary"],
    }
    value["audit_hash"] = digest(value)
    return value


def build_live_report() -> dict[str, Any]:
    return {
        "schema": "uruha_m56_separate_formal_scorer_live_report_v1",
        "status": "formal_scoring_denied_waiting_for_human_chain",
        "audit": build_live_audit(),
        "synthetic_rehearsal": build_synthetic_rehearsal(),
    }


def render_dashboard(report: dict[str, Any] | None = None) -> str:
    report = deepcopy(report or build_live_report())
    audit = report["audit"]
    counts = audit["counts"]
    stages = [
        ("1", "預測先封存", "210 列完整且不可改", True),
        ("2", "資源先比較", "B5 / Ours token 差 ≤ 5%", True),
        ("3", "才開答案艙", "generation 永遠看不到 outcome", False),
        ("4", "七組一起計分", "Brier、NLL、Top-1 等固定", False),
        ("5", "固定主對照", "B5 vs Ours，不能看完換組", False),
        ("6", "結果再封存", "負結果也必須保留", False),
    ]
    cards = "".join(
        f'<article class="stage {"pre" if before else "private"}"><span>{number}</span><b>{html.escape(title)}</b><small>{html.escape(detail)}</small></article>'
        for number, title, detail, before in stages
    )
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M56.4 獨立正式計分器</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#07101d;color:#eef5ff;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}main{{max-width:1320px;margin:auto;padding:30px}}.hero,.panel{{background:#101c2f;border:1px solid #314968;border-radius:22px;padding:24px;margin-bottom:18px}}.hero{{background:linear-gradient(135deg,#17364e,#29182f)}}h1{{font-size:clamp(31px,5vw,48px);margin:.25em 0}}p{{line-height:1.55}}.status{{display:inline-block;background:#581b2e;color:#ffc0cf;padding:7px 12px;border-radius:999px;font-weight:800}}.pink{{color:#ff9db4;font-weight:800;font-size:20px}}.flow{{display:grid;grid-template-columns:repeat(6,1fr);gap:10px}}.stage{{background:#091528;border:1px solid #38577b;border-radius:16px;padding:16px;min-height:142px}}.stage span,.stage b,.stage small{{display:block}}.stage span{{font-size:26px;color:#66dfc8;font-weight:900}}.stage b{{margin:10px 0}}.stage small{{color:#b9c9dc}}.stage.private{{border-color:#a9536b}}.wall{{display:grid;grid-template-columns:1fr auto 1fr;gap:18px;align-items:center}}.box{{border:1px solid #3b5b80;background:#081426;border-radius:18px;padding:20px;text-align:center;min-height:145px}}.divider{{font-size:45px;color:#ff87a2}}.metrics{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}}.metric{{background:#081426;border:1px solid #304d70;border-radius:15px;padding:17px;text-align:center}}.metric strong{{font-size:30px;display:block;color:#65dfc8}}.boundary{{border-left:5px solid #ff809b}}@media(max-width:900px){{.flow,.metrics,.wall{{grid-template-columns:1fr}}.divider{{transform:rotate(90deg);text-align:center}}}}</style></head><body><main>
<section class="hero"><span class="status">M56.4 FORMAL SCORING · DENIED NOW</span><h1>答案不是「跑完模型就打開」：先過資源公平門，才准計分</h1><p class="pink">V7 {counts['v7_slots_by_ledger'][0]}/18 + {counts['v7_slots_by_ledger'][1]}/18，所以現在 prediction release 0、答案讀取 0、正式結果 0。</p><p>這一層把生成與評分真的拆成兩個權限：先驗證所有預測與成本，才能讓獨立 scorer 讀封存答案。</p></section>
<section class="panel"><h2>不能跳過的六步</h2><div class="flow">{cards}</div></section>
<section class="panel"><h2>硬邊界：資源 gate 在答案之前</h2><div class="wall"><div class="box"><b>OUTCOME-BLIND</b><p>submission、SHA commitment、call ledger、B5/Ours token 差</p></div><div class="divider">║</div><div class="box"><b>SCORING · PRIVATE</b><p>outcome key、七組 metrics、B5 vs Ours、結果 commitment</p></div></div></section>
<section class="panel"><h2>目前 authoritative 數字</h2><div class="metrics"><div class="metric"><strong>{counts['v9_independently_reviewed_events']}/30</strong>V9 events</div><div class="metric"><strong>{counts['real_temporal_rows']}/30</strong>real rows</div><div class="metric"><strong>0</strong>score access</div><div class="metric"><strong>0</strong>scorer calls</div><div class="metric"><strong>0</strong>formal result</div></div></section>
<section class="panel boundary"><h2>證據邊界</h2><p>M56.4 只補齊未來正式計分與負結果保留機制。現在沒有真人 labels、沒有正式 predictions、沒有 performance score；它不能證明 Equation V1、Uruha 預測優勢或人類方程式。</p></section>
</main></body></html>"""


def serve_demo(port: int) -> None:
    page = render_dashboard().encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format: str, *_args: Any) -> None:
            return

        def do_GET(self) -> None:
            if self.path == "/health":
                body, content_type, status = b"ok", "text/plain; charset=utf-8", 200
            elif self.path in ("/", "/dashboard"):
                body, content_type, status = page, "text/html; charset=utf-8", 200
            else:
                body, content_type, status = b"not found", "text/plain; charset=utf-8", 404
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--port", type=int, default=7912)
    parser.add_argument("--format", choices=("report", "contract", "html"), default="report")
    args = parser.parse_args()
    if args.serve:
        serve_demo(args.port)
    elif args.format == "contract":
        print(json.dumps(validate_contract(), ensure_ascii=False, indent=2))
    elif args.format == "html":
        print(render_dashboard())
    else:
        print(json.dumps(build_live_report(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
