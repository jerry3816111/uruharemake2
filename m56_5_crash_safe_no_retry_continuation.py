from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import argparse
import html
import json
import math
import os
from pathlib import Path
import time
from typing import Any

import m56_2_real_data_activation_envelope as activation_m56
import m56_3_lease_gated_generation_runner as runner_m56
import m56_4_separate_formal_scorer as scorer_m56


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/m56_5_crash_safe_no_retry_continuation_v1.json"
PRIVATE_ROOT = runner_m56.PRIVATE_ROOT

MODE_SCHEMA = "uruha_m56_crash_safe_execution_mode_commitment_v1"
EQUATION_CHECKPOINT_SCHEMA = "uruha_m56_equation_rematerialization_checkpoint_v1"
INTENT_SCHEMA = "uruha_m56_single_transport_invocation_intent_v1"
STEP_CHECKPOINT_SCHEMA = "uruha_m56_immutable_completed_step_checkpoint_v1"
AUDIT_SCHEMA = "uruha_m56_crash_safe_no_retry_continuation_audit_v1"
REHEARSAL_SCHEMA = "uruha_m56_crash_safe_no_retry_continuation_rehearsal_v1"

MODE_FILENAME = "m56_5_execution_mode_commitment.json"
EQUATION_CHECKPOINT_FILENAME = "m56_5_equation_rematerialization_checkpoint.json"
CHECKPOINT_DIRECTORY = "m56_5_step_checkpoints"

FORBIDDEN_CHECKPOINT_KEYS = {
    "actual_observed_behavior",
    "acceptable_behavior_labels",
    "outcome_key",
    "private_outcome_key",
    "target_outcome",
    "gold_answer",
    "raw_prompt",
    "raw_prompt_text",
    "raw_source",
    "raw_source_text",
    "raw_response",
    "raw_response_text",
    "reasoning",
    "reasoning_trace",
    "chain_of_thought",
    "private_mental_state",
}


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


def _find_forbidden_keys(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            location = f"{prefix}.{key}" if prefix else str(key)
            if key in FORBIDDEN_CHECKPOINT_KEYS:
                found.append(location)
            found.extend(_find_forbidden_keys(child, location))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_find_forbidden_keys(child, f"{prefix}[{index}]"))
    return found


def validate_contract(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors: list[str] = []
    expected_fields = {
        "schema", "version", "status", "single_changed_variable", "public_api",
        "frozen_dependencies", "state_machine", "recovery_policy", "checkpoint_boundary",
        "final_artifacts", "authorization", "claim_boundary",
    }
    if set(contract) != expected_fields:
        errors.append("contract.fields")
    if contract.get("schema") != "uruha_m56_crash_safe_no_retry_continuation_contract_v1":
        errors.append("contract.schema")
    if contract.get("version") != "1.0.0" or contract.get("status") != "prospective_frozen_before_any_real_m56_generation_call":
        errors.append("contract.version_or_status")
    api = contract.get("public_api") or {}
    if api.get("function") != "execute_resumable_formal_generation" or api.get("parameters") != ["run_id"]:
        errors.append("public_api.signature")
    if any(api.get(name) is not False for name in (
        "provider_injection_allowed", "prediction_injection_allowed", "outcome_injection_allowed",
        "resume_override_allowed", "retry_or_fallback_override_allowed",
    )):
        errors.append("public_api.injection")
    dependencies = contract.get("frozen_dependencies") or {}
    if len(dependencies) != 6:
        errors.append("dependencies.count")
    for relative_path, expected_hash in dependencies.items():
        path = ROOT / relative_path
        if not path.is_file() or sha256_file(path) != expected_hash:
            errors.append(f"dependency:{relative_path}")
    recovery = contract.get("recovery_policy") or {}
    expected_recovery = {
        "completed_checkpoint_reuse_allowed": True,
        "completed_step_model_recall_allowed": False,
        "intent_plus_valid_checkpoint_is_completed": True,
        "intent_without_checkpoint_is_terminal": True,
        "failure_record_is_terminal": True,
        "checkpoint_mutation_is_terminal": True,
        "out_of_order_execution_allowed": False,
        "retry_count": 0,
        "fallback_count": 0,
    }
    if recovery != expected_recovery:
        errors.append("recovery_policy")
    boundary = contract.get("checkpoint_boundary") or {}
    if boundary.get("combined_result_and_call_telemetry") is not True:
        errors.append("checkpoint_boundary.combined")
    if any(boundary.get(name) is not False for name in (
        "additional_raw_prompt_copy_persisted", "additional_raw_source_copy_persisted", "raw_model_response_persisted",
        "reasoning_trace_persisted", "private_outcome_access", "private_mental_state_assertion_persisted",
    )):
        errors.append("checkpoint_boundary.private_or_raw")
    final_artifacts = contract.get("final_artifacts") or {}
    if any(value is not True for value in final_artifacts.values()):
        errors.append("final_artifacts")
    authorization = contract.get("authorization") or {}
    if any(value is not False for value in authorization.values()):
        errors.append("authorization.current")
    return {
        "valid": not errors,
        "errors": errors,
        "contract_hash": digest(contract),
        "binding_count": len(dependencies),
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
    telemetry = root / "telemetry"
    return {
        "root": root,
        "generation": root / "generation",
        "commitments": root / "commitments",
        "telemetry": telemetry,
        "checkpoints": telemetry / CHECKPOINT_DIRECTORY,
        "mode": telemetry / MODE_FILENAME,
        "equation": telemetry / EQUATION_CHECKPOINT_FILENAME,
        "schedule": root / "generation" / runner_m56.SCHEDULE_FILENAME,
        "submission": root / "generation" / runner_m56.SUBMISSION_FILENAME,
        "ledger": telemetry / runner_m56.CALL_LEDGER_FILENAME,
        "commitment": root / "commitments" / runner_m56.COMMITMENT_FILENAME,
        "release": root / "commitments" / runner_m56.SCORING_RELEASE_FILENAME,
        "failure": telemetry / runner_m56.FAILURE_FILENAME,
    }


def _write_or_validate_identical(path: Path, value: dict[str, Any]) -> str:
    if path.exists():
        existing = load_json(path)
        if existing != value:
            raise FileExistsError(f"immutable artifact differs: {path.name}")
        return "validated_existing_identical"
    runner_m56._atomic_write_json(path, value, exclusive=True)
    return "created"


def build_mode_commitment(run_id: str, lease_hash: str) -> dict[str, Any]:
    value = {
        "schema": MODE_SCHEMA,
        "version": "1.0.0",
        "status": "m56_5_checkpointing_committed_before_any_transport",
        "run_id": run_id,
        "contract_hash": validate_contract()["contract_hash"],
        "runner_contract_hash": runner_m56.validate_contract()["contract_hash"],
        "lease_hash": lease_hash,
        "completed_step_reuse_allowed": True,
        "model_recall_for_completed_step_allowed": False,
        "ambiguous_inflight_recall_allowed": False,
        "retry_count": 0,
        "fallback_count": 0,
        "generation_target_outcome_access_count": 0,
        "formal_scoring_authorized": False,
        "formal_result_claim_authorized": False,
        "production_memory_write_authorized": False,
        "external_deployment_authorized": False,
    }
    value["mode_commitment_hash"] = digest(value)
    return value


def validate_mode_commitment(value: dict[str, Any], run_id: str, lease_hash: str) -> list[str]:
    errors: list[str] = []
    expected = build_mode_commitment(run_id, lease_hash)
    if value != expected:
        errors.append("mode.content_or_hash")
    errors.extend(f"mode.forbidden:{name}" for name in _find_forbidden_keys(value))
    return errors


def _ensure_mode_before_schedule(paths: dict[str, Path], run_id: str, lease_hash: str) -> dict[str, Any]:
    if not paths["mode"].exists() and paths["schedule"].exists():
        raise PermissionError("existing schedule without M56.5 pre-transport mode commitment is ambiguous")
    value = build_mode_commitment(run_id, lease_hash)
    _write_or_validate_identical(paths["mode"], value)
    errors = validate_mode_commitment(load_json(paths["mode"]), run_id, lease_hash)
    if errors:
        raise ValueError("invalid M56.5 mode commitment: " + "; ".join(errors))
    return value


def _ensure_schedule(paths: dict[str, Path], rows: dict[str, dict[str, Any]]) -> dict[str, Any]:
    expected = runner_m56.build_generation_schedule(
        rows["packet"], rows["manifest"], rows["capsule"], rows["bundle"], rows["lease"]["lease_hash"]
    )
    _write_or_validate_identical(paths["schedule"], expected)
    report = runner_m56.validate_generation_schedule(
        expected, rows["packet"], rows["manifest"], rows["capsule"], rows["bundle"], rows["lease"]["lease_hash"]
    )
    if not report["valid"]:
        raise ValueError("schedule invalid: " + "; ".join(report["errors"]))
    return expected


def build_equation_checkpoint(
    run_id: str, rows: dict[str, dict[str, Any]], schedule: dict[str, Any], cpu_seconds: float
) -> dict[str, Any]:
    if not isinstance(cpu_seconds, (int, float)) or not math.isfinite(float(cpu_seconds)) or cpu_seconds < 0:
        raise ValueError("invalid Equation rematerialization CPU")
    value = {
        "schema": EQUATION_CHECKPOINT_SCHEMA,
        "version": "1.0.0",
        "status": "equation_bundle_rematerialized_identically_before_step_execution",
        "run_id": run_id,
        "contract_hash": validate_contract()["contract_hash"],
        "lease_hash": rows["lease"]["lease_hash"],
        "schedule_hash": schedule["schedule_hash"],
        "equation_artifact_bundle_hash": rows["bundle"]["artifact_bundle_hash"],
        "equation_artifact_rematerialization_cpu_seconds": float(cpu_seconds),
        "bundle_drift_count": 0,
        "model_call_count": 0,
        "generation_target_outcome_access_count": 0,
        "retry_count": 0,
        "fallback_count": 0,
    }
    value["equation_checkpoint_hash"] = digest(value)
    return value


def _ensure_equation_checkpoint(
    paths: dict[str, Path], run_id: str, rows: dict[str, dict[str, Any]], schedule: dict[str, Any]
) -> dict[str, Any]:
    started = time.process_time()
    rebuilt = activation_m56.build_formal_artifact_bundle(rows["packet"], rows["capsule"], rows["manifest"])
    elapsed = time.process_time() - started
    if rebuilt != rows["bundle"]:
        raise ValueError("Equation artifact rematerialization drift")
    if paths["equation"].exists():
        value = load_json(paths["equation"])
        expected = build_equation_checkpoint(
            run_id, rows, schedule, value.get("equation_artifact_rematerialization_cpu_seconds")
        )
        if value != expected:
            raise ValueError("Equation checkpoint drift")
        return value
    value = build_equation_checkpoint(run_id, rows, schedule, elapsed)
    runner_m56._atomic_write_json(paths["equation"], value, exclusive=True)
    return value


def _all_steps(schedule: dict[str, Any]) -> list[dict[str, Any]]:
    return deepcopy(schedule["summary_steps"] + schedule["prediction_steps"])


def _step_paths(paths: dict[str, Path], step: dict[str, Any]) -> tuple[Path, Path]:
    stem = f"{int(step['step_index']):04d}"
    return paths["checkpoints"] / f"{stem}.json", paths["checkpoints"] / f"{stem}.intent.json"


def _task_maps(rows: dict[str, dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    summaries = {row["summary_task_id"]: row for row in rows["capsule"]["summary_tasks"]}
    predictions = {row["task_id"]: row for row in rows["capsule"]["prediction_tasks"]}
    return summaries, predictions


def _prompt_for_step(
    step: dict[str, Any], rows: dict[str, dict[str, Any]], summary_by_id: dict[str, dict[str, Any]]
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any]]:
    summary_tasks, prediction_tasks = _task_maps(rows)
    run_map = {row["condition_id"]: row for row in rows["manifest"]["condition_runs"]}
    if step["phase"] == "b4_summary":
        task = summary_tasks[step["step_id"]]
        run = run_map["B4_FULL_HISTORY_SUMMARY"]
        if not step["model_call_required"]:
            return None, None, run
        return runner_m56.build_summary_prompt(task), runner_m56._summary_json_schema(), run
    task = prediction_tasks[step["step_id"]]
    run = run_map[task["condition_id"]]
    if not step["model_call_required"]:
        return None, None, run
    return (
        runner_m56.build_prediction_prompt(task, summary_by_id, rows["bundle"]),
        runner_m56._prediction_json_schema(task["view"]["candidate_behavior_labels"]),
        run,
    )


def build_intent(
    run_id: str, rows: dict[str, dict[str, Any]], schedule: dict[str, Any], step: dict[str, Any],
    prompt: dict[str, Any], run: dict[str, Any],
) -> dict[str, Any]:
    value = {
        "schema": INTENT_SCHEMA,
        "version": "1.0.0",
        "status": "single_transport_intent_committed_before_call",
        "run_id": run_id,
        "contract_hash": validate_contract()["contract_hash"],
        "runner_contract_hash": runner_m56.validate_contract()["contract_hash"],
        "lease_hash": rows["lease"]["lease_hash"],
        "schedule_hash": schedule["schedule_hash"],
        "step_index": step["step_index"],
        "phase": step["phase"],
        "step_id": step["step_id"],
        "source_hash": step["source_hash"],
        "prompt_hash": prompt["prompt_hash"],
        "model_name": run["model_name"],
        "model_artifact_digest": run["model_artifact_digest"],
        "hardware_fingerprint": run["hardware_fingerprint"],
        "provider_options_hash": digest(run["provider_options"]),
        "transport_attempt_authorized": 1,
        "retry_count": 0,
        "fallback_count": 0,
        "generation_target_outcome_access_count": 0,
    }
    value["intent_hash"] = digest(value)
    return value


def _validate_intent(
    value: dict[str, Any], run_id: str, rows: dict[str, dict[str, Any]], schedule: dict[str, Any],
    step: dict[str, Any], prompt: dict[str, Any], run: dict[str, Any],
) -> list[str]:
    expected = build_intent(run_id, rows, schedule, step, prompt, run)
    errors = [] if value == expected else ["intent.content_or_hash"]
    errors.extend(f"intent.forbidden:{name}" for name in _find_forbidden_keys(value))
    return errors


def _call_telemetry(step: dict[str, Any], call: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": runner_m56.CALL_SCHEMA,
        "phase": step["phase"],
        "step_id": step["step_id"],
        **{key: value for key, value in call.items() if key != "parsed"},
    }


def _result_for_step(
    step: dict[str, Any], rows: dict[str, dict[str, Any]], summary_by_id: dict[str, dict[str, Any]],
    call: dict[str, Any] | None, run: dict[str, Any],
) -> tuple[str, dict[str, Any], dict[str, Any] | None]:
    summary_tasks, prediction_tasks = _task_maps(rows)
    if step["phase"] == "b4_summary":
        task = summary_tasks[step["step_id"]]
        if call is None:
            result = runner_m56._empty_summary_artifact(task, rows["snapshot"])
            return "summary_artifact", result, None
        result = runner_m56._summary_artifact(task, call, run)
        return "summary_artifact", result, _call_telemetry(step, call)
    task = prediction_tasks[step["step_id"]]
    if call is None:
        result = runner_m56._deterministic_b0(task, run)
        return "prediction_row", result, None
    result = runner_m56._prediction_row(task, call, run, summary_by_id, rows["bundle"])
    return "prediction_row", result, _call_telemetry(step, call)


def build_step_checkpoint(
    run_id: str, rows: dict[str, dict[str, Any]], schedule: dict[str, Any], step: dict[str, Any],
    result_kind: str, result: dict[str, Any], call_telemetry: dict[str, Any] | None,
) -> dict[str, Any]:
    model_calls = 1 if step["model_call_required"] else 0
    if (call_telemetry is not None) != bool(model_calls):
        raise ValueError("checkpoint call telemetry does not match scheduled call role")
    value = {
        "schema": STEP_CHECKPOINT_SCHEMA,
        "version": "1.0.0",
        "status": "immutable_step_complete_no_retry",
        "run_id": run_id,
        "contract_hash": validate_contract()["contract_hash"],
        "runner_contract_hash": runner_m56.validate_contract()["contract_hash"],
        "lease_hash": rows["lease"]["lease_hash"],
        "schedule_hash": schedule["schedule_hash"],
        "step_index": step["step_index"],
        "phase": step["phase"],
        "step_id": step["step_id"],
        "source_hash": step["source_hash"],
        "model_call_required": step["model_call_required"],
        "result_kind": result_kind,
        "result": deepcopy(result),
        "call_telemetry": deepcopy(call_telemetry),
        "model_call_count": model_calls,
        "transport_attempt_count": model_calls,
        "retry_count": 0,
        "fallback_count": 0,
        "generation_target_outcome_access_count": 0,
        "formal_scoring_authorized": False,
        "formal_result_claim_authorized": False,
        "production_memory_write_authorized": False,
        "external_deployment_authorized": False,
    }
    forbidden = _find_forbidden_keys(value)
    if forbidden:
        raise ValueError("checkpoint contains forbidden content: " + "; ".join(forbidden))
    value["checkpoint_hash"] = digest(value)
    return value


def _call_from_checkpoint(checkpoint: dict[str, Any]) -> dict[str, Any] | None:
    telemetry = checkpoint["call_telemetry"]
    if telemetry is None:
        return None
    return {
        **{key: value for key, value in telemetry.items() if key not in {"schema", "phase", "step_id"}},
        "parsed": (
            {"summary_text": checkpoint["result"]["summary_text"]}
            if checkpoint["result_kind"] == "summary_artifact"
            else {
                "probabilities": deepcopy(checkpoint["result"]["probabilities"]),
                "authorized_evidence_ids": deepcopy(checkpoint["result"]["authorized_evidence_ids"]),
                "brief_evidence": checkpoint["result"]["brief_evidence"],
            }
        ),
    }


def validate_step_checkpoint(
    checkpoint: dict[str, Any], run_id: str, rows: dict[str, dict[str, Any]], schedule: dict[str, Any],
    step: dict[str, Any], summary_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    errors: list[str] = []
    expected_fields = {
        "schema", "version", "status", "run_id", "contract_hash", "runner_contract_hash",
        "lease_hash", "schedule_hash", "step_index", "phase", "step_id", "source_hash",
        "model_call_required", "result_kind", "result", "call_telemetry", "model_call_count",
        "transport_attempt_count", "retry_count", "fallback_count",
        "generation_target_outcome_access_count", "formal_scoring_authorized",
        "formal_result_claim_authorized", "production_memory_write_authorized",
        "external_deployment_authorized", "checkpoint_hash",
    }
    if set(checkpoint) != expected_fields:
        errors.append("checkpoint.fields")
    unhashed = {key: value for key, value in checkpoint.items() if key != "checkpoint_hash"}
    if checkpoint.get("checkpoint_hash") != digest(unhashed):
        errors.append("checkpoint.hash")
    for name, expected in (
        ("schema", STEP_CHECKPOINT_SCHEMA),
        ("version", "1.0.0"),
        ("status", "immutable_step_complete_no_retry"),
        ("run_id", run_id),
        ("contract_hash", validate_contract()["contract_hash"]),
        ("runner_contract_hash", runner_m56.validate_contract()["contract_hash"]),
        ("lease_hash", rows["lease"]["lease_hash"]),
        ("schedule_hash", schedule["schedule_hash"]),
        ("step_index", step["step_index"]),
        ("phase", step["phase"]),
        ("step_id", step["step_id"]),
        ("source_hash", step["source_hash"]),
        ("model_call_required", step["model_call_required"]),
    ):
        if checkpoint.get(name) != expected:
            errors.append(f"checkpoint.{name}")
    expected_calls = int(step["model_call_required"])
    if checkpoint.get("model_call_count") != expected_calls or checkpoint.get("transport_attempt_count") != expected_calls:
        errors.append("checkpoint.call_count")
    if checkpoint.get("retry_count") != 0 or checkpoint.get("fallback_count") != 0:
        errors.append("checkpoint.retry_or_fallback")
    if checkpoint.get("generation_target_outcome_access_count") != 0:
        errors.append("checkpoint.outcome_access")
    if any(checkpoint.get(name) is not False for name in (
        "formal_scoring_authorized", "formal_result_claim_authorized",
        "production_memory_write_authorized", "external_deployment_authorized",
    )):
        errors.append("checkpoint.excess_authority")
    errors.extend(f"checkpoint.forbidden:{name}" for name in _find_forbidden_keys(checkpoint))
    run_map = {row["condition_id"]: row for row in rows["manifest"]["condition_runs"]}
    _, prediction_tasks = _task_maps(rows)
    run = run_map["B4_FULL_HISTORY_SUMMARY"] if step["phase"] == "b4_summary" else run_map[prediction_tasks[step["step_id"]]["condition_id"]]
    call = _call_from_checkpoint(checkpoint)
    if step["model_call_required"]:
        if call is None:
            errors.append("checkpoint.call_telemetry_missing")
        else:
            expected_prompt, _, _ = _prompt_for_step(step, rows, summary_by_id)
            if expected_prompt is None or call.get("prompt_hash") != expected_prompt.get("prompt_hash"):
                errors.append("checkpoint.prompt_hash")
            if (checkpoint.get("result") or {}).get("prompt_hash") != call.get("prompt_hash"):
                errors.append("checkpoint.result_prompt_hash")
            resource_errors = runner_m56._validate_call_resources(
                call, input_budget=int(run["input_token_budget"]), output_budget=int(run["output_token_budget"])
            )
            errors.extend(f"checkpoint.resource:{name}" for name in resource_errors)
            try:
                runner_m56._validate_model_identity(call, run["model_name"])
            except ValueError as exc:
                errors.append(f"checkpoint.model:{exc}")
    elif call is not None:
        errors.append("checkpoint.unexpected_call_telemetry")
    if not errors:
        try:
            result_kind, result, telemetry = _result_for_step(step, rows, summary_by_id, call, run)
            expected = build_step_checkpoint(run_id, rows, schedule, step, result_kind, result, telemetry)
            if checkpoint != expected:
                errors.append("checkpoint.reconstruction")
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"checkpoint.reconstruction:{exc}")
    return {
        "valid": not errors,
        "errors": errors,
        "checkpoint_hash": checkpoint.get("checkpoint_hash"),
        "model_call_count": checkpoint.get("model_call_count", 0),
    }


def _later_step_artifact_exists(paths: dict[str, Path], steps: list[dict[str, Any]], index: int) -> bool:
    for later in steps[index + 1:]:
        checkpoint_path, intent_path = _step_paths(paths, later)
        if checkpoint_path.exists() or intent_path.exists():
            return True
    return False


def _validate_checkpoint_inventory(paths: dict[str, Path], steps: list[dict[str, Any]]) -> None:
    directory = paths["checkpoints"]
    if not directory.exists():
        return
    allowed: set[str] = set()
    for step in steps:
        checkpoint_path, intent_path = _step_paths(paths, step)
        allowed.add(checkpoint_path.name)
        allowed.add(intent_path.name)
    actual = {path.name for path in directory.iterdir()}
    unexpected = sorted(actual - allowed)
    if unexpected:
        raise PermissionError("unexpected checkpoint artifact: " + ", ".join(unexpected))


def _after_intent_hook(step_index: int) -> None:
    del step_index


def _after_checkpoint_hook(step_index: int) -> None:
    del step_index


def _after_checkpoint_write_before_intent_clear_hook(step_index: int) -> None:
    del step_index


def _collect_or_execute_steps(
    paths: dict[str, Path], run_id: str, rows: dict[str, dict[str, Any]], schedule: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], int]:
    steps = _all_steps(schedule)
    summaries: list[dict[str, Any]] = []
    predictions: list[dict[str, Any]] = []
    calls: list[dict[str, Any]] = []
    summary_by_id: dict[str, dict[str, Any]] = {}
    reused = 0
    _validate_checkpoint_inventory(paths, steps)
    for index, step in enumerate(steps):
        checkpoint_path, intent_path = _step_paths(paths, step)
        if checkpoint_path.exists():
            checkpoint = load_json(checkpoint_path)
            report = validate_step_checkpoint(checkpoint, run_id, rows, schedule, step, summary_by_id)
            if not report["valid"]:
                raise ValueError("checkpoint validation failed: " + "; ".join(report["errors"]))
            if intent_path.exists():
                prompt, _, run = _prompt_for_step(step, rows, summary_by_id)
                if prompt is None:
                    raise ValueError("deterministic completed step cannot have an invocation intent")
                intent_errors = _validate_intent(load_json(intent_path), run_id, rows, schedule, step, prompt, run)
                if intent_errors:
                    raise ValueError("intent validation failed: " + "; ".join(intent_errors))
                intent_path.unlink()
            reused += 1
        else:
            if _later_step_artifact_exists(paths, steps, index):
                raise PermissionError("out-of-order checkpoint or intent detected")
            prompt, output_schema, run = _prompt_for_step(step, rows, summary_by_id)
            if intent_path.exists():
                if prompt is None:
                    raise PermissionError("unexpected deterministic-step intent marker")
                intent_errors = _validate_intent(load_json(intent_path), run_id, rows, schedule, step, prompt, run)
                if intent_errors:
                    raise ValueError("intent validation failed: " + "; ".join(intent_errors))
                raise PermissionError("ambiguous in-flight transport has no completed checkpoint; recall forbidden")
            if prompt is None:
                call = None
            else:
                intent = build_intent(run_id, rows, schedule, step, prompt, run)
                runner_m56._atomic_write_json(intent_path, intent, exclusive=True)
                _after_intent_hook(int(step["step_index"]))
                call = runner_m56._ollama_generate(prompt["prompt"], output_schema or {}, run["provider_options"])
                call["prompt_hash"] = prompt["prompt_hash"]
                resource_errors = runner_m56._validate_call_resources(
                    call, input_budget=int(run["input_token_budget"]), output_budget=int(run["output_token_budget"])
                )
                if resource_errors:
                    raise ValueError("step resource gate failed: " + "; ".join(resource_errors))
                runner_m56._validate_model_identity(call, run["model_name"])
            result_kind, result, telemetry = _result_for_step(step, rows, summary_by_id, call, run)
            checkpoint = build_step_checkpoint(
                run_id, rows, schedule, step, result_kind, result, telemetry
            )
            runner_m56._atomic_write_json(checkpoint_path, checkpoint, exclusive=True)
            if intent_path.exists():
                _after_checkpoint_write_before_intent_clear_hook(int(step["step_index"]))
                intent_path.unlink()
            _after_checkpoint_hook(int(step["step_index"]))
        result = checkpoint["result"]
        if checkpoint["result_kind"] == "summary_artifact":
            summaries.append(deepcopy(result))
            summary_by_id[result["summary_task_id"]] = deepcopy(result)
        else:
            predictions.append(deepcopy(result))
        if checkpoint["call_telemetry"] is not None:
            calls.append(deepcopy(checkpoint["call_telemetry"]))
    return summaries, predictions, calls, reused


def _finalize(
    paths: dict[str, Path], rows: dict[str, dict[str, Any]], schedule: dict[str, Any],
    equation_checkpoint: dict[str, Any], summaries: list[dict[str, Any]],
    predictions: list[dict[str, Any]], calls: list[dict[str, Any]],
) -> dict[str, Any]:
    lease = rows["lease"]
    submission = runner_m56.build_formal_submission(
        schedule, rows["packet"], rows["manifest"], rows["capsule"], rows["bundle"], lease,
        summaries, predictions, equation_checkpoint["equation_artifact_rematerialization_cpu_seconds"],
    )
    submission_report = runner_m56.validate_formal_submission(
        submission, schedule, rows["packet"], rows["manifest"], rows["capsule"], rows["bundle"], lease
    )
    if not submission_report["valid"]:
        raise ValueError("formal submission invalid: " + "; ".join(submission_report["errors"]))
    ledger = {
        "schema": "uruha_m56_formal_call_ledger_v1",
        "version": "1.0.0",
        "status": "complete_before_prediction_commitment",
        "lease_hash": lease["lease_hash"],
        "schedule_hash": schedule["schedule_hash"],
        "call_count": len(calls),
        "required_call_count": schedule["required_model_call_count"],
        "calls": deepcopy(calls),
        "equation_artifact_rematerialization_cpu_seconds": equation_checkpoint["equation_artifact_rematerialization_cpu_seconds"],
        "retry_count": 0,
        "fallback_count": 0,
        "generation_target_outcome_access_count": 0,
    }
    ledger["ledger_hash"] = digest(ledger)
    _write_or_validate_identical(paths["submission"], submission)
    _write_or_validate_identical(paths["ledger"], ledger)
    commitment = runner_m56.build_prediction_commitment(submission, schedule, lease, submission_report)
    _write_or_validate_identical(paths["commitment"], commitment)
    release = runner_m56.build_scoring_release(commitment, submission, schedule, lease, submission_report)
    _write_or_validate_identical(paths["release"], release)
    scorer_rows = {
        **rows,
        "schedule": schedule,
        "submission": submission,
        "commitment": commitment,
        "release": release,
        "call_ledger": ledger,
    }
    prescore = scorer_m56.validate_prescore_inputs(lease["run_id"], scorer_rows)
    if not prescore["valid"]:
        raise ValueError("M56.4 pre-score compatibility failed: " + "; ".join(prescore["errors"]))
    return {
        "submission": submission,
        "ledger": ledger,
        "commitment": commitment,
        "release": release,
        "prescore": prescore,
    }


def _validate_existing_complete(
    paths: dict[str, Path], run_id: str, rows: dict[str, dict[str, Any]], schedule: dict[str, Any]
) -> dict[str, Any] | None:
    final_paths = [paths["submission"], paths["ledger"], paths["commitment"], paths["release"]]
    if not any(path.exists() for path in final_paths):
        return None
    if not all(path.exists() for path in final_paths):
        return None
    submission = load_json(paths["submission"])
    ledger = load_json(paths["ledger"])
    commitment = load_json(paths["commitment"])
    release = load_json(paths["release"])
    submission_report = runner_m56.validate_formal_submission(
        submission, schedule, rows["packet"], rows["manifest"], rows["capsule"], rows["bundle"], rows["lease"]
    )
    errors = list(submission_report["errors"])
    errors.extend(scorer_m56.validate_call_ledger(
        ledger, schedule, submission, commitment, rows["lease"]
    )["errors"])
    errors.extend(runner_m56.validate_prediction_commitment(
        commitment, submission, schedule, rows["lease"], submission_report
    )["errors"])
    errors.extend(runner_m56.validate_scoring_release(
        release, commitment, submission, schedule, rows["lease"], submission_report
    )["errors"])
    if errors:
        raise ValueError("existing complete run invalid: " + "; ".join(errors))
    return {
        "status": "formal_generation_already_complete_scoring_released",
        "submission_hash": submission["submission_hash"],
        "commitment_hash": commitment["commitment_hash"],
        "scoring_release_hash": release["release_hash"],
        "model_call_count": ledger["call_count"],
        "reused_completed_step_count": len(_all_steps(schedule)),
        "generation_target_outcome_access_count": 0,
        "formal_result_claim_authorized": False,
    }


def execute_resumable_formal_generation(run_id: str) -> dict[str, Any]:
    """Execute or continue one M56.5 run; the only caller input is its already-authorized run id."""

    paths = _paths(run_id)
    phase = "input_validation"
    lease_hash: str | None = None
    try:
        rows = runner_m56.load_permitted_runner_inputs(run_id)
        validation = runner_m56.validate_runner_inputs(run_id, rows)
        if not validation["valid"]:
            raise PermissionError("runner inputs invalid: " + "; ".join(validation["errors"]))
        lease_hash = rows["lease"]["lease_hash"]
        if paths["failure"].exists():
            raise PermissionError("terminal generation failure already exists; continuation forbidden")
        phase = "pre_transport_mode_commitment"
        _ensure_mode_before_schedule(paths, run_id, lease_hash)
        phase = "schedule_commitment"
        schedule = _ensure_schedule(paths, rows)
        complete = _validate_existing_complete(paths, run_id, rows, schedule)
        if complete is not None:
            return complete
        phase = "equation_artifact_rematerialization"
        equation_checkpoint = _ensure_equation_checkpoint(paths, run_id, rows, schedule)
        phase = "checkpointed_generation"
        summaries, predictions, calls, reused = _collect_or_execute_steps(paths, run_id, rows, schedule)
        phase = "finalization"
        final = _finalize(paths, rows, schedule, equation_checkpoint, summaries, predictions, calls)
        return {
            "status": "formal_generation_complete_scoring_released",
            "submission_hash": final["submission"]["submission_hash"],
            "commitment_hash": final["commitment"]["commitment_hash"],
            "scoring_release_hash": final["release"]["release_hash"],
            "model_call_count": len(calls),
            "reused_completed_step_count": reused,
            "generation_target_outcome_access_count": 0,
            "formal_result_claim_authorized": False,
        }
    except Exception as exc:
        if paths["telemetry"].is_dir():
            runner_m56._terminal_failure(paths, lease_hash, phase, exc)
        raise


def build_synthetic_rehearsal() -> dict[str, Any]:
    value = {
        "schema": REHEARSAL_SCHEMA,
        "version": "1.0.0",
        "status": "no_call_no_outcome_state_machine_rehearsal_only",
        "fixture_step_count": 211,
        "fixture_completed_checkpoints": 12,
        "fixture_reused_without_model_recall": 12,
        "fixture_ambiguous_intent_without_checkpoint": 1,
        "fixture_ambiguous_state_decision": "terminal_no_recall",
        "human_evidence_count": 0,
        "model_call_count": 0,
        "target_outcome_access_count": 0,
        "formal_generation_authorized": False,
        "formal_scoring_authorized": False,
        "formal_result_created": False,
        "production_memory_write_authorized": False,
        "claim_boundary": "Graph and state-machine fixture only; no human labels, formal model calls, outcome access, score, or result.",
    }
    value["rehearsal_hash"] = digest(value)
    return value


def build_live_audit() -> dict[str, Any]:
    contract_report = validate_contract()
    generation = runner_m56.build_live_audit()
    value = {
        "schema": AUDIT_SCHEMA,
        "version": "1.0.0",
        "status": (
            "formal_generation_continuation_ready"
            if generation["formal_generation_authorized"]
            else "formal_generation_continuation_denied_waiting_for_human_chain"
        ),
        "contract_valid": contract_report["valid"],
        "contract_hash": contract_report["contract_hash"],
        "counts": deepcopy(generation["counts"]),
        "formal_generation_authorized": generation["formal_generation_authorized"],
        "formal_model_calls": 0,
        "completed_checkpoint_count": 0,
        "ambiguous_inflight_count": 0,
        "generation_target_outcome_access_count": 0,
        "formal_commitment_created": False,
        "formal_scoring_release_created": False,
        "formal_result_created": False,
        "blocking_gates": [name for name, passed in generation["gates"].items() if passed is False],
        "claim_boundary": load_contract()["claim_boundary"],
    }
    value["audit_hash"] = digest(value)
    return value


def build_live_report() -> dict[str, Any]:
    return {
        "schema": "uruha_m56_crash_safe_no_retry_continuation_live_report_v1",
        "status": "formal_generation_continuation_denied_waiting_for_human_chain",
        "audit": build_live_audit(),
        "synthetic_rehearsal": build_synthetic_rehearsal(),
    }


def render_dashboard(report: dict[str, Any] | None = None) -> str:
    report = deepcopy(report or build_live_report())
    audit = report["audit"]
    counts = audit["counts"]
    rehearsal = report["synthetic_rehearsal"]
    stages = [
        ("01", "授權與固定順序", "先驗證真人鏈、lease、固定 summary 順序與 210 個預測。"),
        ("02", "每步先寫呼叫意圖", "模型呼叫前先留下不可變標記；沒有暗中重試。"),
        ("03", "結果與成本一起封存", "機率／summary 與 token、時間、記憶資源原子落盤。"),
        ("04", "重新啟動只讀已完成步驟", "完整 checkpoint 可沿用，該 task 不再呼叫模型。"),
        ("05", "不確定是否完成就終止", "只有 intent 沒有結果時，禁止猜測與再次呼叫。"),
        ("06", "全部完成才承諾與放行計分", "仍用原 M56.3 submission、SHA commitment 與 M56.4 scorer。"),
    ]
    stage_html = "".join(
        f'<div class="node"><span>{number}</span><h3>{html.escape(title)}</h3><p>{html.escape(body)}</p></div>'
        for number, title, body in stages
    )
    return f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>M56.5 Crash-safe No-retry Continuation</title>
<style>
*{{box-sizing:border-box}} body{{margin:0;background:#071019;color:#eef7ff;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
main{{max-width:1180px;margin:auto;padding:28px}} .hero{{padding:26px;border:1px solid #31516a;border-radius:20px;background:linear-gradient(135deg,#10283a,#111929)}}
.deny{{display:inline-block;padding:8px 12px;border-radius:999px;background:#61242a;color:#ffdadd;font-weight:800}} h1{{font-size:34px;margin:14px 0 8px}} .sub{{color:#acd1e7;line-height:1.6}}
.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0}} .metric,.card{{border:1px solid #29475c;border-radius:16px;background:#0c1c28;padding:16px}}
.metric strong{{display:block;font-size:28px;color:#7bd5ff}} .metric small{{color:#97b9cc}} .flow{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:22px 0}}
.node{{position:relative;border:1px solid #2c617b;border-radius:18px;background:#0b2231;padding:18px;min-height:154px}} .node span{{font:700 13px ui-monospace;color:#6fe1c1}} .node h3{{margin:10px 0 7px}} .node p,.card p{{color:#a9c7d9;line-height:1.55;margin:0}}
.states{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}} .good{{border-color:#247b68}} .stop{{border-color:#9d4a53}} .final{{border-color:#7e66b5}}
.bar{{height:12px;background:#182d3b;border-radius:9px;overflow:hidden;margin-top:12px}} .bar i{{display:block;width:0%;height:100%;background:#54d4a6}}
.boundary{{margin-top:22px;border:1px solid #77444d;background:#24151b;border-radius:16px;padding:18px;color:#ffd8dc;line-height:1.6}}
@media(max-width:820px){{.metrics,.flow,.states{{grid-template-columns:1fr}} h1{{font-size:28px}}}}
</style></head><body><main>
<section class="hero"><span class="deny">DENIED NOW · 0 FORMAL CALLS</span><h1>M56.5 · 中斷後可以安全續跑，但不能重試</h1>
<p class="sub">把長時間正式實驗拆成固定的 B4 summary 步驟與 210 個預測步驟；summary 數由預先封存的 distinct history 決定。完整封存的步驟可以在重新啟動後沿用；只留下呼叫意圖、卻沒有完整結果的步驟必須終止，避免偷偷再抽一次答案。</p></section>
<section class="metrics"><div class="metric"><strong>{counts['v7_slots_by_ledger'][0]}/18</strong><small>真人 A</small></div><div class="metric"><strong>{counts['v7_slots_by_ledger'][1]}/18</strong><small>真人 B</small></div><div class="metric"><strong>{counts['real_temporal_rows']}/30</strong><small>正式時間列</small></div><div class="metric"><strong>0</strong><small>正式呼叫／答案讀取／結果</small></div></section>
<section class="flow">{stage_html}</section>
<section class="states"><div class="card good"><h3>完整 checkpoint</h3><p>結果、資源、task 與來源雜湊完整一致：重新啟動後直接沿用，模型呼叫數不增加。</p><div class="bar"><i style="width:100%"></i></div></div>
<div class="card stop"><h3>只有 intent</h3><p>無法證明模型是否已回覆：正式 run 終止，禁止重呼、fallback 或人工補值。</p><div class="bar"><i style="width:48%;background:#e16e79"></i></div></div>
<div class="card final"><h3>全部完成</h3><p>才建立原 M56.3 submission／call ledger／SHA commitment，再交給 M56.4 獨立 scorer。</p><div class="bar"><i style="width:100%;background:#9e8ae6"></i></div></div></section>
<section class="card" style="margin-top:22px"><h3>圖示用故障演練，不是正式結果</h3><p>{rehearsal['fixture_completed_checkpoints']} 個假 checkpoint 可被沿用；1 個只有 intent 的假狀態會 terminal。此圖的真人、模型呼叫與答案存取皆為 0。</p></section>
<section class="boundary"><strong>證據邊界：</strong>這只證明中斷恢復機制不會重呼已完成或不確定的 task。它不證明 Uruha 預測、Equation V1、模型優勢、人類方程式、完整產品或正式部署。</section>
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
    parser = argparse.ArgumentParser(description="M56.5 crash-safe no-retry formal generation continuation")
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--rehearsal", action="store_true")
    parser.add_argument("--serve", type=int)
    parser.add_argument("--run-id")
    args = parser.parse_args()
    if args.serve is not None:
        serve_demo(args.serve)
    elif args.run_id:
        print(json.dumps(execute_resumable_formal_generation(args.run_id), ensure_ascii=False, indent=2))
    elif args.rehearsal:
        print(json.dumps(build_synthetic_rehearsal(), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(build_live_audit(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
