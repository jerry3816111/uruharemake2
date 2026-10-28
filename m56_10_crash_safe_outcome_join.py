#!/usr/bin/env python3
"""M56.10 crash-safe at-most-once private-outcome join.

The sanctioned entry preserves the frozen M56.8 authorization and M56.9
single-writer lock, then records a full-sync intent before the one permitted
private-outcome load.  A full-sync private score checkpoint lets a later
process finish the unchanged M56.4 result without loading the outcome again.
Intent without a valid checkpoint is deliberately terminal because a restart
cannot prove whether the outcome was opened before the process stopped.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import html
import inspect
import json
from pathlib import Path
from typing import Any

import m56_4_separate_formal_scorer as scorer_m56
import m56_7_mac_full_sync_generation as durable_m56
import m56_8_durable_release_gated_scoring as gated_m56
import m56_9_single_writer_formal_scoring as single_writer_m56


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/m56_10_crash_safe_outcome_join_v1.json"
MODE_FILENAME = "m56_10_outcome_join_mode.json"
INTENT_FILENAME = "m56_10_outcome_join_intent.json"
CHECKPOINT_FILENAME = "m56_10_score_checkpoint.json"
FAILURE_FILENAME = "m56_10_outcome_join_terminal_failure.json"
AUDIT_SCHEMA = "uruha_m56_crash_safe_outcome_join_audit_v1"
REHEARSAL_SCHEMA = "uruha_m56_crash_safe_outcome_join_rehearsal_v1"


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return sha256(canonical(value).encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    return sha256(Path(path).read_bytes()).hexdigest()


def load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def load_contract(path: str | Path = CONTRACT_PATH) -> dict[str, Any]:
    return load_json(path)


def validate_contract(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors: list[str] = []
    expected_fields = {
        "schema", "version", "status", "single_changed_variable", "public_api",
        "frozen_dependencies", "durable_state", "restart_policy", "guarantees",
        "unchanged_semantics", "authorization", "claim_boundary",
    }
    if set(contract) != expected_fields:
        errors.append("contract.fields")
    if contract.get("schema") != "uruha_m56_crash_safe_outcome_join_contract_v1":
        errors.append("contract.schema")
    if contract.get("version") != "1.0.0":
        errors.append("contract.version")
    if contract.get("status") != "prospective_frozen_before_implementation_and_any_real_m56_target_outcome_access":
        errors.append("contract.status")
    api = contract.get("public_api") or {}
    if api.get("function") != "execute_crash_safe_outcome_join_formal_scoring":
        errors.append("public_api.function")
    if api.get("parameters") != ["run_id"]:
        errors.append("public_api.parameters")
    if api.get("outcome_result_checkpoint_readiness_retry_wait_or_bypass_injection_allowed") is not False:
        errors.append("public_api.injection")
    dependencies = contract.get("frozen_dependencies") or {}
    if len(dependencies) != 3:
        errors.append("dependencies.count")
    for relative_path, expected_hash in dependencies.items():
        path = ROOT / relative_path
        if not path.is_file() or sha256_file(path) != expected_hash:
            errors.append(f"dependency:{relative_path}")
    durable = contract.get("durable_state") or {}
    if any(durable.get(name) is not True for name in (
        "mode_committed_before_m56_8_gate_and_m56_4_outcome_state",
        "join_intent_committed_before_private_outcome_load",
        "score_checkpoint_committed_after_one_load_before_canonical_result",
        "file_fsync_required", "file_f_fullfsync_required",
        "directory_fsync_required", "directory_f_fullfsync_required",
        "score_checkpoint_contains_exact_validated_m56_4_score_report",
    )):
        errors.append("durable_state.required")
    if durable.get("score_checkpoint_location") != "private_scoring_compartment":
        errors.append("durable_state.location")
    restart = contract.get("restart_policy") or {}
    expected_restart = {
        "no_intent_no_checkpoint": "perform_one_authorized_private_outcome_load",
        "valid_intent_and_valid_checkpoint": "reuse_checkpoint_without_private_outcome_load",
        "valid_intent_without_checkpoint": "terminal_fail_without_private_outcome_load",
        "checkpoint_without_valid_intent": "terminal_fail_without_private_outcome_load",
        "canonical_result_without_checkpoint": "terminal_fail_without_retroactive_certification",
        "retry_count": 0,
        "fallback_count": 0,
        "manual_result_injection_allowed": False,
    }
    if restart != expected_restart:
        errors.append("restart_policy")
    guarantees = contract.get("guarantees") or {}
    if guarantees.get("completed_run_private_outcome_load_count") != 1:
        errors.append("guarantees.completed_load_count")
    if any(guarantees.get(name) != 0 for name in (
        "checkpointed_restart_additional_private_outcome_load_count",
        "completed_sequential_replay_additional_private_outcome_load_count",
        "ambiguous_intent_only_restart_additional_private_outcome_load_count",
    )):
        errors.append("guarantees.restart_load_count")
    if guarantees.get("at_most_once_on_sanctioned_m56_10_path") is not True:
        errors.append("guarantees.at_most_once")
    if any(guarantees.get(name) is not False for name in (
        "unconditional_exactly_once_completion_across_all_crash_points",
        "availability_preserved_in_ambiguous_crash_window", "distributed_transaction_claimed",
        "same_host_malicious_access_cryptographically_prevented",
    )):
        errors.append("guarantees.overclaim")
    unchanged = contract.get("unchanged_semantics") or {}
    if not unchanged or any(value is not True for value in unchanged.values()):
        errors.append("unchanged_semantics")
    authorization = contract.get("authorization") or {}
    if not authorization or any(value is not False for value in authorization.values()):
        errors.append("authorization.current")
    if list(inspect.signature(execute_crash_safe_outcome_join_formal_scoring).parameters) != ["run_id"]:
        errors.append("implementation.public_signature")
    return {
        "valid": not errors,
        "errors": errors,
        "contract_hash": digest(contract),
        "binding_count": len(dependencies),
    }


def _paths(run_id: str) -> dict[str, Path]:
    paths = gated_m56._paths(run_id)
    return {
        **paths,
        "m56_10_mode": paths["telemetry"] / MODE_FILENAME,
        "m56_10_intent": paths["telemetry"] / INTENT_FILENAME,
        "m56_10_checkpoint": paths["scoring"] / CHECKPOINT_FILENAME,
        "m56_10_failure": paths["telemetry"] / FAILURE_FILENAME,
    }


def _durable_write_or_validate_identical(path: Path, value: dict[str, Any]) -> str:
    if path.exists():
        if load_json(path) != value:
            raise ValueError(f"existing immutable M56.10 artifact differs: {path.name}")
        return "validated_existing_identical"
    durable_m56._durable_atomic_write_json(path, value, exclusive=True)
    return "created_full_sync"


def _legacy_outcome_state(paths: dict[str, Path]) -> list[str]:
    candidates = (
        paths["m56_8_gate"],
        paths["commitments"] / scorer_m56.ACCESS_RECEIPT_FILENAME,
        paths["scoring"] / scorer_m56.SCORE_REPORT_FILENAME,
        paths["commitments"] / scorer_m56.RESULT_COMMITMENT_FILENAME,
    )
    return [path.name for path in candidates if path.exists()]


def build_mode_commitment(run_id: str, authorization: dict[str, Any]) -> dict[str, Any]:
    if not authorization.get("valid") or not authorization.get("scoring_ready"):
        raise PermissionError("M56.10 mode requires valid scoring-ready M56.8 authorization")
    rows = authorization["rows"]
    value = {
        "schema": "uruha_m56_crash_safe_outcome_join_mode_v1",
        "version": "1.0.0",
        "status": "m56_10_mode_committed_before_outcome_access_state",
        "run_id": run_id,
        "contract_hash": validate_contract()["contract_hash"],
        "m56_9_contract_hash": single_writer_m56.validate_contract()["contract_hash"],
        "m56_8_authorization_hash": authorization["authorization_hash"],
        "m56_7_durable_release_hash": authorization["m56_7_durable_release_hash"],
        "submission_hash": rows["submission"]["submission_hash"],
        "prediction_commitment_hash": rows["commitment"]["commitment_hash"],
        "scoring_release_hash": rows["release"]["release_hash"],
        "expected_outcome_key_hash": rows["request"]["outcome_key_hash"],
        "expected_split_report_hash": rows["request"]["split_report_hash"],
        "file_fsync_required": True,
        "file_f_fullfsync_required": True,
        "directory_fsync_required": True,
        "directory_f_fullfsync_required": True,
        "retry_count": 0,
        "fallback_count": 0,
        "formal_result_claim_authorized_before_checkpoint": False,
        "production_memory_write_authorized": False,
        "external_deployment_authorized": False,
    }
    value["mode_commitment_hash"] = digest(value)
    return value


def _commit_or_validate_mode(
    paths: dict[str, Path], run_id: str, authorization: dict[str, Any]
) -> tuple[dict[str, Any], str]:
    expected = build_mode_commitment(run_id, authorization)
    path = paths["m56_10_mode"]
    if path.exists():
        existing = load_json(path)
        if existing != expected:
            raise ValueError("existing immutable M56.10 mode differs")
        return existing, "validated_existing_identical"
    prior = _legacy_outcome_state(paths)
    if prior:
        raise PermissionError(
            "preexisting M56.8/M56.4 outcome state cannot be retroactively certified by M56.10: "
            + ", ".join(prior)
        )
    if any(paths[name].exists() for name in (
        "m56_10_intent", "m56_10_checkpoint", "m56_10_failure"
    )):
        raise PermissionError("M56.10 state exists without its required prior mode")
    durable_m56._durable_atomic_write_json(path, expected, exclusive=True)
    return expected, "created_before_m56_8_and_outcome_state"


def build_join_intent(
    run_id: str,
    mode: dict[str, Any],
    gate: dict[str, Any],
    rows: dict[str, dict[str, Any]],
    access_receipt: dict[str, Any],
) -> dict[str, Any]:
    value = {
        "schema": "uruha_m56_private_outcome_join_intent_v1",
        "version": "1.0.0",
        "status": "private_outcome_join_invocation_started_no_retry",
        "run_id": run_id,
        "contract_hash": validate_contract()["contract_hash"],
        "mode_commitment_hash": mode["mode_commitment_hash"],
        "m56_8_gate_hash": gate["gate_hash"],
        "prescore_audit_hash": access_receipt["prescore_audit_hash"],
        "scoring_access_receipt_hash": access_receipt["access_receipt_hash"],
        "prediction_commitment_hash": rows["commitment"]["commitment_hash"],
        "scoring_release_hash": rows["release"]["release_hash"],
        "expected_outcome_key_hash": rows["request"]["outcome_key_hash"],
        "expected_split_report_hash": rows["request"]["split_report_hash"],
        "private_outcome_load_authorization_count": 1,
        "retry_count": 0,
        "fallback_count": 0,
        "manual_result_injection_allowed": False,
        "production_memory_write_authorized": False,
        "external_deployment_authorized": False,
    }
    value["join_intent_hash"] = digest(value)
    return value


def build_score_checkpoint(
    run_id: str,
    mode: dict[str, Any],
    gate: dict[str, Any],
    intent: dict[str, Any],
    report: dict[str, Any],
) -> dict[str, Any]:
    report_validation = scorer_m56.validate_score_report(report)
    if not report_validation["valid"]:
        raise ValueError("M56.10 checkpoint requires an unchanged valid M56.4 score report")
    value = {
        "schema": "uruha_m56_private_score_checkpoint_v1",
        "version": "1.0.0",
        "status": "one_outcome_join_score_report_full_sync_committed",
        "run_id": run_id,
        "contract_hash": validate_contract()["contract_hash"],
        "mode_commitment_hash": mode["mode_commitment_hash"],
        "m56_8_gate_hash": gate["gate_hash"],
        "join_intent_hash": intent["join_intent_hash"],
        "scoring_access_receipt_hash": intent["scoring_access_receipt_hash"],
        "outcome_key_hash": report["outcome_key_hash"],
        "split_report_hash": report["split_report_hash"],
        "score_report_hash": report["score_report_hash"],
        "score_report": deepcopy(report),
        "private_outcome_loader_call_count": 1,
        "scorer_model_call_count": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "production_memory_write_authorized": False,
        "external_deployment_authorized": False,
    }
    value["score_checkpoint_hash"] = digest(value)
    return value


def validate_score_checkpoint(
    checkpoint: dict[str, Any],
    run_id: str,
    mode: dict[str, Any],
    gate: dict[str, Any],
    intent: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    expected_fields = {
        "schema", "version", "status", "run_id", "contract_hash",
        "mode_commitment_hash", "m56_8_gate_hash", "join_intent_hash",
        "scoring_access_receipt_hash", "outcome_key_hash", "split_report_hash",
        "score_report_hash", "score_report", "private_outcome_loader_call_count",
        "scorer_model_call_count", "retry_count", "fallback_count",
        "production_memory_write_authorized", "external_deployment_authorized",
        "score_checkpoint_hash",
    }
    if set(checkpoint) != expected_fields:
        errors.append("checkpoint.fields")
    if checkpoint.get("schema") != "uruha_m56_private_score_checkpoint_v1":
        errors.append("checkpoint.schema")
    if checkpoint.get("status") != "one_outcome_join_score_report_full_sync_committed":
        errors.append("checkpoint.status")
    unhashed = {key: value for key, value in checkpoint.items() if key != "score_checkpoint_hash"}
    if checkpoint.get("score_checkpoint_hash") != digest(unhashed):
        errors.append("checkpoint.hash")
    report = checkpoint.get("score_report")
    report_validation = scorer_m56.validate_score_report(report) if isinstance(report, dict) else {
        "valid": False, "errors": ["report.object"]
    }
    errors.extend(f"report:{name}" for name in report_validation["errors"])
    bindings = {
        "run_id": run_id,
        "contract_hash": validate_contract()["contract_hash"],
        "mode_commitment_hash": mode.get("mode_commitment_hash"),
        "m56_8_gate_hash": gate.get("gate_hash"),
        "join_intent_hash": intent.get("join_intent_hash"),
        "scoring_access_receipt_hash": intent.get("scoring_access_receipt_hash"),
    }
    for name, expected in bindings.items():
        if checkpoint.get(name) != expected:
            errors.append(f"checkpoint.binding:{name}")
    if isinstance(report, dict):
        for name in ("outcome_key_hash", "split_report_hash", "score_report_hash"):
            if checkpoint.get(name) != report.get(name):
                errors.append(f"checkpoint.report_binding:{name}")
        if report.get("run_id") != run_id:
            errors.append("checkpoint.report_binding:run_id")
    if checkpoint.get("private_outcome_loader_call_count") != 1:
        errors.append("checkpoint.outcome_load_count")
    if checkpoint.get("scorer_model_call_count") != 0:
        errors.append("checkpoint.model_call_count")
    if checkpoint.get("retry_count") != 0 or checkpoint.get("fallback_count") != 0:
        errors.append("checkpoint.retry_or_fallback")
    if checkpoint.get("production_memory_write_authorized") is not False:
        errors.append("checkpoint.production")
    if checkpoint.get("external_deployment_authorized") is not False:
        errors.append("checkpoint.deployment")
    return {
        "valid": not errors,
        "errors": errors,
        "score_checkpoint_hash": checkpoint.get("score_checkpoint_hash"),
    }


def build_terminal_failure(
    run_id: str, mode: dict[str, Any], intent: dict[str, Any]
) -> dict[str, Any]:
    value = {
        "schema": "uruha_m56_ambiguous_outcome_join_terminal_failure_v1",
        "version": "1.0.0",
        "status": "terminal_no_retry_outcome_join_state",
        "run_id": run_id,
        "contract_hash": validate_contract()["contract_hash"],
        "mode_commitment_hash": mode["mode_commitment_hash"],
        "join_intent_hash": intent["join_intent_hash"],
        "reason": "durable_intent_exists_without_valid_durable_score_checkpoint",
        "historical_private_outcome_load_count": "unknown_zero_or_one",
        "additional_private_outcome_load_authorized": False,
        "retry_count": 0,
        "fallback_count": 0,
        "formal_result_created": False,
        "production_memory_write_authorized": False,
        "external_deployment_authorized": False,
    }
    value["terminal_failure_hash"] = digest(value)
    return value


def _load_and_validate_intent(
    paths: dict[str, Path], run_id: str, mode: dict[str, Any], gate: dict[str, Any],
    rows: dict[str, dict[str, Any]], access_receipt: dict[str, Any],
) -> dict[str, Any]:
    intent = load_json(paths["m56_10_intent"])
    expected = build_join_intent(run_id, mode, gate, rows, access_receipt)
    if intent != expected:
        raise ValueError("existing immutable M56.10 outcome-join intent differs")
    return intent


def _commit_terminal_failure(
    paths: dict[str, Path], run_id: str, mode: dict[str, Any], intent: dict[str, Any]
) -> dict[str, Any]:
    failure = build_terminal_failure(run_id, mode, intent)
    _durable_write_or_validate_identical(paths["m56_10_failure"], failure)
    return failure


def _finalize_from_checkpoint(
    paths: dict[str, Path],
    run_id: str,
    authorization: dict[str, Any],
    gate: dict[str, Any],
    mode: dict[str, Any],
    intent: dict[str, Any],
    checkpoint: dict[str, Any],
    *,
    checkpoint_write: str,
    outcome_load_this_invocation: int,
) -> dict[str, Any]:
    validation = validate_score_checkpoint(checkpoint, run_id, mode, gate, intent)
    if not validation["valid"]:
        raise ValueError("M56.10 score checkpoint invalid: " + "; ".join(validation["errors"]))
    report = checkpoint["score_report"]
    report_status = _durable_write_or_validate_identical(
        paths["scoring"] / scorer_m56.SCORE_REPORT_FILENAME, report
    )
    result_commitment = scorer_m56.build_result_commitment(report)
    commitment_status = _durable_write_or_validate_identical(
        paths["commitments"] / scorer_m56.RESULT_COMMITMENT_FILENAME,
        result_commitment,
    )
    base_result = {
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
    gated_m56._validate_delegated_result(run_id, paths, gate, base_result)
    return {
        **base_result,
        "m56_8_gate_hash": gate["gate_hash"],
        "m56_8_gate_created": True,
        "m56_8_scoring_authorized": True,
        "m56_7_durable_release_hash": authorization["m56_7_durable_release_hash"],
        "m56_10_mode_commitment_hash": mode["mode_commitment_hash"],
        "m56_10_join_intent_hash": intent["join_intent_hash"],
        "m56_10_score_checkpoint_hash": checkpoint["score_checkpoint_hash"],
        "m56_10_checkpoint_write": checkpoint_write,
        "m56_10_private_outcome_load_this_invocation": outcome_load_this_invocation,
        "m56_10_completed_run_private_outcome_load_count": 1,
        "m56_10_at_most_once_sanctioned_path": True,
        "m56_10_terminal_failure_created": False,
    }


def _execute_under_lock(run_id: str) -> dict[str, Any]:
    paths = _paths(run_id)
    authorization = gated_m56.validate_durable_scoring_authorization(run_id)
    if not authorization["valid"]:
        raise PermissionError(
            "M56.10 durable-release authorization failed: " + "; ".join(authorization["errors"])
        )
    if not authorization["scoring_ready"]:
        result = gated_m56.execute_durable_release_gated_formal_scoring(run_id)
        return {
            **result,
            "m56_10_mode_created": False,
            "m56_10_private_outcome_load_this_invocation": 0,
            "m56_10_at_most_once_sanctioned_path": False,
        }
    rows = authorization["rows"]
    mode, mode_write = _commit_or_validate_mode(paths, run_id, authorization)
    gate, gate_write = gated_m56._commit_or_validate_gate(paths, run_id, authorization)
    prescore = authorization["prescore"]
    prescore_audit = scorer_m56.build_prescore_audit(run_id, rows, prescore)
    _durable_write_or_validate_identical(
        paths["telemetry"] / scorer_m56.PRESCORE_AUDIT_FILENAME, prescore_audit
    )
    access_receipt = scorer_m56.build_scoring_access_receipt(run_id, rows, prescore_audit)
    _durable_write_or_validate_identical(
        paths["commitments"] / scorer_m56.ACCESS_RECEIPT_FILENAME, access_receipt
    )

    checkpoint_exists = paths["m56_10_checkpoint"].exists()
    intent_exists = paths["m56_10_intent"].exists()
    canonical_exists = any(path.exists() for path in (
        paths["scoring"] / scorer_m56.SCORE_REPORT_FILENAME,
        paths["commitments"] / scorer_m56.RESULT_COMMITMENT_FILENAME,
    ))
    if canonical_exists and not checkpoint_exists:
        raise PermissionError("canonical M56.4 score/result exists without M56.10 checkpoint")
    if paths["m56_10_failure"].exists():
        raise PermissionError("M56.10 outcome-join state is terminal; retry is forbidden")
    if checkpoint_exists and not intent_exists:
        raise PermissionError("M56.10 checkpoint exists without its immutable join intent")
    if intent_exists:
        intent = _load_and_validate_intent(
            paths, run_id, mode, gate, rows, access_receipt
        )
        if not checkpoint_exists:
            _commit_terminal_failure(paths, run_id, mode, intent)
            raise PermissionError(
                "M56.10 intent exists without a valid durable score checkpoint; "
                "outcome reload is forbidden"
            )
        checkpoint = load_json(paths["m56_10_checkpoint"])
        return {
            **_finalize_from_checkpoint(
                paths, run_id, authorization, gate, mode, intent, checkpoint,
                checkpoint_write="validated_existing_restart_checkpoint",
                outcome_load_this_invocation=0,
            ),
            "m56_10_mode_write": mode_write,
            "m56_8_gate_write": gate_write,
        }

    intent = build_join_intent(run_id, mode, gate, rows, access_receipt)
    _durable_write_or_validate_identical(paths["m56_10_intent"], intent)
    try:
        outcome_rows = scorer_m56.load_outcome_inputs(run_id)
        report = scorer_m56.build_score_report(
            run_id, rows, prescore, access_receipt,
            outcome_rows["outcome_key"], outcome_rows["split_report"],
        )
        checkpoint = build_score_checkpoint(run_id, mode, gate, intent, report)
        checkpoint_write = _durable_write_or_validate_identical(
            paths["m56_10_checkpoint"], checkpoint
        )
    except BaseException:
        if not paths["m56_10_checkpoint"].exists():
            try:
                _commit_terminal_failure(paths, run_id, mode, intent)
            except BaseException:
                pass
        raise
    return {
        **_finalize_from_checkpoint(
            paths, run_id, authorization, gate, mode, intent, checkpoint,
            checkpoint_write=checkpoint_write,
            outcome_load_this_invocation=1,
        ),
        "m56_10_mode_write": mode_write,
        "m56_8_gate_write": gate_write,
    }


def execute_crash_safe_outcome_join_formal_scoring(run_id: str) -> dict[str, Any]:
    """Run the sanctioned at-most-once scorer for one standard private run id."""

    single_writer_m56._validate_permitted_run(run_id)
    with single_writer_m56._exclusive_scoring_lock(single_writer_m56._lock_path(run_id)):
        return _execute_under_lock(run_id)


def build_synthetic_rehearsal() -> dict[str, Any]:
    value = {
        "schema": REHEARSAL_SCHEMA,
        "version": "1.0.0",
        "status": "forged_engineering_state_machine_only",
        "pre_change": {
            "failed_then_restarted_invocations": 2,
            "private_outcome_loader_calls": 2,
        },
        "post_change": {
            "uninterrupted_completed_run_total_outcome_loads": 1,
            "checkpointed_restart_additional_outcome_loads": 0,
            "completed_sequential_replay_additional_outcome_loads": 0,
            "ambiguous_intent_only_restart_additional_outcome_loads": 0,
            "ambiguous_intent_only_state": "terminal_no_retry",
        },
        "guarantee": "at_most_once_on_cooperative_sanctioned_m56_10_path",
        "unconditional_exactly_once_completion": False,
        "availability_in_ambiguous_window": False,
        "human_evidence_count": 0,
        "formal_model_call_count": 0,
        "real_target_outcome_access_count": 0,
        "formal_result_created": False,
        "claim_boundary": load_contract()["claim_boundary"],
    }
    value["rehearsal_hash"] = digest(value)
    return value


def build_live_audit() -> dict[str, Any]:
    contract_report = validate_contract()
    upstream = single_writer_m56.build_live_audit()
    value = {
        "schema": AUDIT_SCHEMA,
        "version": "1.0.0",
        "status": "crash_safe_outcome_join_denied_waiting_for_human_chain",
        "contract_valid": contract_report["valid"],
        "contract_hash": contract_report["contract_hash"],
        "counts": deepcopy(upstream["counts"]),
        "formal_scoring_authorized": False,
        "formal_model_calls": 0,
        "target_outcome_access_count": 0,
        "formal_result_created": False,
        "blocking_gates": deepcopy(upstream["blocking_gates"]),
        "claim_boundary": load_contract()["claim_boundary"],
    }
    value["audit_hash"] = digest(value)
    return value


def build_live_report() -> dict[str, Any]:
    return {
        "schema": "uruha_m56_crash_safe_outcome_join_live_report_v1",
        "status": "crash_safe_outcome_join_denied_waiting_for_human_chain",
        "audit": build_live_audit(),
        "synthetic_rehearsal": build_synthetic_rehearsal(),
    }


def render_dashboard(report: dict[str, Any] | None = None) -> str:
    report = deepcopy(report or build_live_report())
    audit = report["audit"]
    counts = audit["counts"]
    rehearsal = report["synthetic_rehearsal"]
    before = rehearsal["pre_change"]
    after = rehearsal["post_change"]
    boundary = html.escape(audit["claim_boundary"])
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>M56.10 答案只讀一次狀態機</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#07131c;color:#eefaff;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}main{{max-width:1240px;margin:auto;padding:28px}}section{{border:1px solid #31586c;border-radius:20px;background:#0b202d;padding:24px;margin-bottom:18px}}.hero{{background:linear-gradient(135deg,#153c48,#3b243b)}}.deny{{display:inline-block;background:#672633;color:#ffdae0;border-radius:999px;padding:8px 12px;font-weight:850}}h1{{font-size:clamp(30px,5vw,45px);margin:14px 0 8px}}p{{color:#bfdbe4;line-height:1.62}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;border:0;background:none;padding:0}}.metric,.state,.compare{{border:1px solid #31586c;border-radius:16px;background:#0a1b27;padding:17px}}.metric strong{{display:block;color:#7ce2c4;font-size:28px}}.beforeafter{{display:grid;grid-template-columns:1fr auto 1fr;gap:16px;align-items:center}}.arrow{{font-size:38px;color:#70dbbc}}.bad{{border-color:#a84e60}}.good{{border-color:#2b806a}}.count{{font-size:42px;font-weight:900}}.bad .count{{color:#ff8193}}.good .count{{color:#70e0bd}}.states{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}.state b{{display:grid;place-items:center;width:42px;height:42px;border-radius:50%;background:#245e6b;color:#8af0d3}}.state.ok{{border-color:#2b806a}}.state.stop{{border-color:#b76f3c;background:#281b13}}.equation{{font-size:clamp(17px,2.2vw,24px);font-weight:800;color:#8be8ce;text-align:center;padding:14px}}.boundary{{border-left:6px solid #e1a452;background:#272014}}code{{color:#88e8ce}}@media(max-width:850px){{.metrics,.beforeafter,.states{{grid-template-columns:1fr}}.arrow{{transform:rotate(90deg);text-align:center}}}}
</style></head><body><main>
<section class="hero"><span class="deny">DENIED NOW · 0 REAL OUTCOME READS</span><h1>M56.10 · 正式答案只讀一次，重啟不能偷偷再開</h1><p>M56.9 已阻止兩個程式同時讀答案；M56.10 再把「準備讀取」和「已算完分數」耐久記錄下來，讓下一次啟動知道該安全續作，還是必須停止。</p></section>
<section class="metrics"><div class="metric"><strong>{counts['v7_slots_by_ledger'][0]}/18</strong><small>真人 A</small></div><div class="metric"><strong>{counts['v7_slots_by_ledger'][1]}/18</strong><small>真人 B</small></div><div class="metric"><strong>{counts['real_temporal_rows']}/30</strong><small>正式時間列</small></div><div class="metric"><strong>0</strong><small>正式答案／結果</small></div></section>
<section><h2>真正重現到的跨重啟錯誤</h2><div class="beforeafter"><div class="compare bad"><h3>修改前 · M56.9</h3><div class="count">{before['private_outcome_loader_calls']} 次</div><p>第一次讀完答案後中斷；第二次不知道已讀過，又重新打開一次。</p></div><div class="arrow">→</div><div class="compare good"><h3>修改後 · M56.10</h3><div class="count">{after['uninterrupted_completed_run_total_outcome_loads']} 次</div><p>完整成功只讀一次；完成後再啟動也只驗證 checkpoint，額外讀取為 {after['completed_sequential_replay_additional_outcome_loads']}。</p></div></div></section>
<section><h2>三種重啟狀態</h2><div class="states"><div class="state ok"><b>A</b><h3>還沒開始讀</h3><p>先耐久寫入 intent，再授權唯一一次答案讀取。</p></div><div class="state ok"><b>B</b><h3>已有完整 checkpoint</h3><p>直接用已驗證的 M56.4 score report 完成結果；額外答案讀取 <strong>0</strong>。</p></div><div class="state stop"><b>!</b><h3>只有 intent</h3><p>不知道中斷前到底讀了沒有，所以永久停止、不重試、不補造結果。</p></div></div><div class="equation">completed = 1 total load · checkpoint restart = +0 · ambiguous restart = +0 and terminal</div></section>
<section class="boundary"><h2>為什麼模糊狀態不能硬續跑？</h2><p>「打開舊答案檔」和「寫出新 checkpoint」不是同一個原子交易。只有 intent 時若再讀，可能變成第二次；若假裝已有結果，又會捏造證據。M56.10 選擇保住可證明的 at-most-once 邊界，代價是這個狹窄 crash window 不保證可用性。</p></section>
<section class="bad"><h2>證據邊界</h2><p>{boundary}</p></section>
</main></body></html>"""


def serve_demo(port: int) -> None:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    page = render_dashboard().encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path not in ("/", "/dashboard"):
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)

        def log_message(self, format: str, *args: Any) -> None:
            del format, args

    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="M56.10 crash-safe at-most-once formal scorer")
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--rehearsal", action="store_true")
    parser.add_argument("--serve", type=int)
    parser.add_argument("--run-id")
    args = parser.parse_args()
    if args.serve is not None:
        serve_demo(args.serve)
    elif args.run_id:
        print(json.dumps(
            execute_crash_safe_outcome_join_formal_scoring(args.run_id),
            ensure_ascii=False,
            indent=2,
        ))
    elif args.rehearsal:
        print(json.dumps(build_synthetic_rehearsal(), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(build_live_audit(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
