#!/usr/bin/env python3
"""M57.1 durable pre-outcome commitment for the frozen M57 diagnostic plan."""

from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import html
import inspect
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from typing import Any
from unittest import mock

import m56_4_separate_formal_scorer as scorer_m56
import m56_7_mac_full_sync_generation as durable_m56
import m56_8_durable_release_gated_scoring as gated_m56
import m56_9_single_writer_formal_scoring as single_writer_m56
import m56_10_crash_safe_outcome_join as crash_safe_m56
import m57_component_error_localization as localization_m57


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/m57_1_preoutcome_diagnostic_commitment_v1.json"
RESULT_PATH = ROOT / "analysis/m57_1_preoutcome_diagnostic_commitment_rehearsal_2026-09-04.json"
MODE_FILENAME = "m57_1_preoutcome_diagnostic_mode.json"
MODE_SCHEMA = "uruha_m57_preoutcome_diagnostic_mode_commitment_v1"
REHEARSAL_SCHEMA = "uruha_m57_preoutcome_diagnostic_commitment_rehearsal_v1"
AUDIT_SCHEMA = "uruha_m57_preoutcome_diagnostic_commitment_live_audit_v1"


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
    expected = {
        "schema", "version", "status", "single_changed_variable", "public_api",
        "frozen_dependencies", "preoutcome_order", "commitment_bindings", "durability",
        "formal_effect", "current_authorization", "claim_boundary",
    }
    if set(contract) != expected:
        errors.append("contract.fields")
    if contract.get("schema") != "uruha_m57_preoutcome_diagnostic_commitment_contract_v1":
        errors.append("contract.schema")
    if contract.get("version") != "1.0.0":
        errors.append("contract.version")
    if contract.get("status") != "prospective_frozen_before_implementation_and_any_real_m56_target_outcome_access":
        errors.append("contract.status")
    api = contract.get("public_api") or {}
    if api.get("commit_function") != "commit_m57_preoutcome_diagnostic_mode":
        errors.append("api.commit")
    if api.get("validate_function") != "validate_m57_preoutcome_diagnostic_mode":
        errors.append("api.validate")
    if api.get("parameters") != ["run_id"]:
        errors.append("api.parameters")
    if api.get("plan_resource_outcome_readiness_authorization_or_retry_injection_allowed") is not False:
        errors.append("api.injection")
    if list(inspect.signature(commit_m57_preoutcome_diagnostic_mode).parameters) != ["run_id"]:
        errors.append("api.commit_signature")
    if list(inspect.signature(validate_m57_preoutcome_diagnostic_mode).parameters) != ["run_id"]:
        errors.append("api.validate_signature")
    dependencies = contract.get("frozen_dependencies") or {}
    if len(dependencies) != 6:
        errors.append("dependencies.count")
    for relative, expected_hash in dependencies.items():
        path = ROOT / relative
        if not path.is_file() or sha256_file(path) != expected_hash:
            errors.append(f"dependency:{relative}")
    order = contract.get("preoutcome_order") or {}
    required_order_true = (
        "same_per_run_scoring_lock_required", "m56_8_gate_absent_at_first_commit",
        "m56_10_mode_intent_checkpoint_failure_absent_at_first_commit",
        "m56_4_access_report_result_absent_at_first_commit",
        "identical_existing_commitment_revalidation_after_scoring_allowed",
    )
    if any(order.get(name) is not True for name in required_order_true):
        errors.append("preoutcome_order.required")
    if order.get("retroactive_first_commit_after_any_outcome_state_allowed") is not False:
        errors.append("preoutcome_order.retroactive")
    bindings = contract.get("commitment_bindings") or {}
    if any(bindings.get(name) is not True for name in (
        "m57_stage_plan_hash", "m57_analyzer_contract_hash",
        "m56_dataset_packet_and_runtime_hashes", "m56_hardware_model_and_equation_artifact_hashes",
        "m56_schedule_submission_prediction_and_call_ledger_hashes", "m56_7_durable_release_hash",
        "expected_withheld_outcome_hashes_without_reading_outcome",
    )):
        errors.append("commitment_bindings.required")
    if bindings.get("retry_count") != 0 or bindings.get("fallback_count") != 0:
        errors.append("commitment_bindings.retry")
    durability = contract.get("durability") or {}
    if not durability or any(value is not True for value in durability.values()):
        errors.append("durability")
    formal = contract.get("formal_effect") or {}
    current = contract.get("current_authorization") or {}
    if not formal or any(value is not False for value in formal.values()):
        errors.append("formal_effect")
    if not current or any(value is not False for value in current.values()):
        errors.append("current_authorization")
    return {
        "valid": not errors,
        "errors": errors,
        "contract_hash": digest(contract),
        "binding_count": len(dependencies),
    }


def _paths(run_id: str) -> dict[str, Path]:
    paths = crash_safe_m56._paths(run_id)
    return {**paths, "m57_1_mode": paths["commitments"] / MODE_FILENAME}


def _outcome_state_paths(paths: dict[str, Path]) -> tuple[Path, ...]:
    return (
        paths["m56_8_gate"],
        paths["m56_10_mode"],
        paths["m56_10_intent"],
        paths["m56_10_checkpoint"],
        paths["m56_10_failure"],
        paths["commitments"] / scorer_m56.ACCESS_RECEIPT_FILENAME,
        paths["scoring"] / scorer_m56.SCORE_REPORT_FILENAME,
        paths["commitments"] / scorer_m56.RESULT_COMMITMENT_FILENAME,
    )


def _present_outcome_state(paths: dict[str, Path]) -> list[str]:
    return [path.name for path in _outcome_state_paths(paths) if path.exists()]


def _load_authorization(run_id: str) -> dict[str, Any]:
    authorization = gated_m56.validate_durable_scoring_authorization(run_id)
    if not authorization.get("valid"):
        raise PermissionError(
            "M57.1 requires a valid durable M56 generation run: "
            + "; ".join(authorization.get("errors") or [])
        )
    if not authorization.get("scoring_ready"):
        raise PermissionError(
            "M57.1 requires an M56 run that is ready before private outcome scoring: "
            + "; ".join(authorization.get("blockers") or [])
        )
    return authorization


def build_preoutcome_diagnostic_mode(run_id: str, authorization: dict[str, Any]) -> dict[str, Any]:
    if not authorization.get("valid") or not authorization.get("scoring_ready"):
        raise PermissionError("M57.1 mode requires valid scoring-ready M56 authorization")
    rows = authorization["rows"]
    snapshot = rows["snapshot"]
    plans = localization_m57._stage_plans()
    value = {
        "schema": MODE_SCHEMA,
        "version": "1.0.0",
        "status": "m57_stage_plans_and_m56_resources_committed_before_outcome_state",
        "run_id": run_id,
        "contract_hash": validate_contract()["contract_hash"],
        "m57_analyzer_contract_hash": localization_m57.validate_contract()["contract_hash"],
        "stage_plans": plans,
        "substitution_plan_commitment_hash": localization_m57.digest(plans),
        "m56_8_preoutcome_authorization_hash": authorization["authorization_hash"],
        "m56_7_mode_commitment_hash": authorization["m56_7_mode_commitment_hash"],
        "m56_7_durable_release_hash": authorization["m56_7_durable_release_hash"],
        "dataset_hash": rows["packet"]["dataset_hash"],
        "prediction_packet_hash": digest(rows["packet"]),
        "run_manifest_hash": digest(rows["manifest"]),
        "runtime_snapshot_hash": snapshot["runtime_snapshot_hash"],
        "hardware_fingerprint": snapshot["hardware_fingerprint"],
        "model_manifest_sha256": snapshot["model_manifest_sha256"],
        "model_name": snapshot["model_name"],
        "provider": snapshot["provider"],
        "ollama_version": snapshot["ollama_version"],
        "equation_artifact_bundle_hash": rows["bundle"]["artifact_bundle_hash"],
        "schedule_hash": rows["schedule"]["schedule_hash"],
        "submission_hash": rows["submission"]["submission_hash"],
        "prediction_commitment_hash": rows["commitment"]["commitment_hash"],
        "scoring_release_hash": rows["release"]["release_hash"],
        "call_ledger_hash": rows["call_ledger"]["ledger_hash"],
        "expected_outcome_key_hash": rows["request"]["outcome_key_hash"],
        "expected_split_report_hash": rows["request"]["split_report_hash"],
        "sample_count": rows["packet"]["sample_count"],
        "condition_count": rows["request"]["condition_count"],
        "generation_model_call_count": rows["commitment"]["model_call_count"],
        "outcome_state_absent_at_first_commit": True,
        "target_outcome_access_count_at_commitment": 0,
        "same_run_scoring_lock_held_at_commitment": True,
        "file_fsync_required": True,
        "file_f_fullfsync_required": True,
        "directory_fsync_required": True,
        "directory_f_fullfsync_required": True,
        "retry_count": 0,
        "fallback_count": 0,
        "component_substitution_predictions_created": False,
        "formal_m57_execution_authorized": False,
        "formal_m57_result_created": False,
        "m58_authorized": False,
        "production_memory_write_authorized": False,
        "external_deployment_authorized": False,
        "claim_boundary": load_contract()["claim_boundary"],
    }
    value["mode_commitment_hash"] = digest(value)
    return value


def validate_mode_value(
    value: dict[str, Any], run_id: str, authorization: dict[str, Any]
) -> dict[str, Any]:
    errors: list[str] = []
    expected = build_preoutcome_diagnostic_mode(run_id, authorization)
    if not isinstance(value, dict) or value != expected:
        errors.append("mode.content_or_hash")
    return {
        "valid": not errors,
        "errors": errors,
        "mode_commitment_hash": value.get("mode_commitment_hash") if isinstance(value, dict) else None,
    }


def _completed_m56_result_link(
    paths: dict[str, Path], mode: dict[str, Any], authorization: dict[str, Any]
) -> dict[str, Any]:
    report_path = paths["scoring"] / scorer_m56.SCORE_REPORT_FILENAME
    result_path = paths["commitments"] / scorer_m56.RESULT_COMMITMENT_FILENAME
    if not report_path.exists() and not result_path.exists():
        return {"present": False, "valid": False, "errors": []}
    if not report_path.exists() or not result_path.exists():
        return {"present": True, "valid": False, "errors": ["m56_result.partial"]}
    report = load_json(report_path)
    result = load_json(result_path)
    errors = list(scorer_m56.validate_score_report(report)["errors"])
    errors.extend(scorer_m56.validate_result_commitment(result, report)["errors"])
    chain_paths = {
        "m56_8_gate": paths["m56_8_gate"],
        "m56_10_mode": paths["m56_10_mode"],
        "m56_10_intent": paths["m56_10_intent"],
        "m56_10_checkpoint": paths["m56_10_checkpoint"],
        "m56_4_access_receipt": paths["commitments"] / scorer_m56.ACCESS_RECEIPT_FILENAME,
    }
    missing = [name for name, path in chain_paths.items() if not path.exists()]
    errors.extend(f"m56_10_chain.missing:{name}" for name in missing)
    if not missing:
        gate = load_json(chain_paths["m56_8_gate"])
        scoring_mode = load_json(chain_paths["m56_10_mode"])
        intent = load_json(chain_paths["m56_10_intent"])
        checkpoint = load_json(chain_paths["m56_10_checkpoint"])
        access_receipt = load_json(chain_paths["m56_4_access_receipt"])
        expected_scoring_mode = crash_safe_m56.build_mode_commitment(
            mode["run_id"], authorization
        )
        if scoring_mode != expected_scoring_mode:
            errors.append("m56_10_chain.mode")
        gate_validation = gated_m56.validate_durable_scoring_gate(
            gate, mode["run_id"], authorization
        )
        errors.extend(f"m56_10_chain.gate:{name}" for name in gate_validation["errors"])
        prescore_audit = scorer_m56.build_prescore_audit(
            mode["run_id"], authorization["rows"], authorization["prescore"]
        )
        expected_access_receipt = scorer_m56.build_scoring_access_receipt(
            mode["run_id"], authorization["rows"], prescore_audit
        )
        if access_receipt != expected_access_receipt:
            errors.append("m56_10_chain.access_receipt")
        expected_intent = crash_safe_m56.build_join_intent(
            mode["run_id"], scoring_mode, gate, authorization["rows"], access_receipt
        )
        if intent != expected_intent:
            errors.append("m56_10_chain.intent")
        checkpoint_validation = crash_safe_m56.validate_score_checkpoint(
            checkpoint, mode["run_id"], scoring_mode, gate, intent
        )
        errors.extend(
            f"m56_10_chain.checkpoint:{name}"
            for name in checkpoint_validation["errors"]
        )
        if checkpoint.get("score_report") != report:
            errors.append("m56_10_chain.checkpoint_report")
    expected = {
        "run_id": mode["run_id"],
        "dataset_hash": mode["dataset_hash"],
        "prediction_packet_hash": mode["prediction_packet_hash"],
        "run_manifest_hash": mode["run_manifest_hash"],
        "equation_artifact_bundle_hash": mode["equation_artifact_bundle_hash"],
        "schedule_hash": mode["schedule_hash"],
        "submission_hash": mode["submission_hash"],
        "prediction_commitment_hash": mode["prediction_commitment_hash"],
        "scoring_release_hash": mode["scoring_release_hash"],
        "call_ledger_hash": mode["call_ledger_hash"],
        "outcome_key_hash": mode["expected_outcome_key_hash"],
        "split_report_hash": mode["expected_split_report_hash"],
    }
    for name, expected_value in expected.items():
        if report.get(name) != expected_value:
            errors.append(f"m56_result.binding:{name}")
    return {
        "present": True,
        "valid": not errors,
        "errors": errors,
        "score_report_hash": report.get("score_report_hash"),
        "result_commitment_hash": result.get("result_commitment_hash"),
    }


def commit_m57_preoutcome_diagnostic_mode(run_id: str) -> dict[str, Any]:
    """Commit the frozen M57 plan before the sanctioned M56 outcome path starts."""

    contract = validate_contract()
    if not contract["valid"]:
        raise PermissionError("M57.1 contract invalid: " + "; ".join(contract["errors"]))
    single_writer_m56._validate_permitted_run(run_id)
    paths = _paths(run_id)
    with single_writer_m56._exclusive_scoring_lock(single_writer_m56._lock_path(run_id)):
        authorization = _load_authorization(run_id)
        expected = build_preoutcome_diagnostic_mode(run_id, authorization)
        path = paths["m57_1_mode"]
        if path.exists():
            existing = load_json(path)
            validation = validate_mode_value(existing, run_id, authorization)
            if not validation["valid"]:
                raise ValueError("existing immutable M57.1 mode differs")
            return {
                "status": "existing_identical_preoutcome_diagnostic_mode_validated",
                "mode_write": "validated_existing_identical",
                "mode_commitment_hash": existing["mode_commitment_hash"],
                "outcome_state_artifacts_now": _present_outcome_state(paths),
                "target_outcome_access_count": 0,
                "formal_m57_result_created": False,
            }
        prior = _present_outcome_state(paths)
        if prior:
            raise PermissionError(
                "M57.1 cannot retroactively certify a diagnostic plan after M56 outcome state: "
                + ", ".join(prior)
            )
        durable_m56._durable_atomic_write_json(path, expected, exclusive=True)
        return {
            "status": "preoutcome_diagnostic_mode_committed_full_sync",
            "mode_write": "created_before_m56_outcome_state",
            "mode_commitment_hash": expected["mode_commitment_hash"],
            "outcome_state_artifacts_now": [],
            "target_outcome_access_count": 0,
            "formal_m57_result_created": False,
        }


def validate_m57_preoutcome_diagnostic_mode(run_id: str) -> dict[str, Any]:
    """Validate one existing M57.1 commitment without authorizing formal M57."""

    contract = validate_contract()
    if not contract["valid"]:
        raise PermissionError("M57.1 contract invalid: " + "; ".join(contract["errors"]))
    authorization = _load_authorization(run_id)
    paths = _paths(run_id)
    if not paths["m57_1_mode"].exists():
        raise PermissionError("M57.1 pre-outcome diagnostic commitment is absent")
    mode = load_json(paths["m57_1_mode"])
    validation = validate_mode_value(mode, run_id, authorization)
    if not validation["valid"]:
        raise ValueError("M57.1 pre-outcome diagnostic commitment invalid")
    result_link = _completed_m56_result_link(paths, mode, authorization)
    return {
        "status": "preoutcome_diagnostic_mode_validated",
        "mode_commitment_hash": mode["mode_commitment_hash"],
        "substitution_plan_commitment_hash": mode["substitution_plan_commitment_hash"],
        "outcome_state_artifacts_now": _present_outcome_state(paths),
        "m56_result_present": result_link["present"],
        "m56_result_link_valid": result_link["valid"],
        "m56_result_link_errors": result_link["errors"],
        "component_substitution_predictions_created": False,
        "target_outcome_access_count": 0,
        "formal_m57_execution_authorized": False,
        "formal_m57_result_created": False,
        "m58_authorized": False,
        "claim_boundary": load_contract()["claim_boundary"],
    }


def build_engineering_rehearsal() -> dict[str, Any]:
    """Exercise the order boundary on a temporary forged M56 run only."""

    from test_m56_9_single_writer_formal_scoring import materialize_scoring_run
    from test_m56_10_crash_safe_outcome_join import m5610_private_roots

    with TemporaryDirectory(prefix="uruha-m57-1-preoutcome-") as temp:
        root = Path(temp)
        run_id = "m57-1-forged-preoutcome-order-rehearsal"
        with m5610_private_roots(root):
            run_root = materialize_scoring_run(root, run_id)
            started = perf_counter()
            first = commit_m57_preoutcome_diagnostic_mode(run_id)
            commit_seconds = perf_counter() - started
            mode_path = run_root / "commitments" / MODE_FILENAME
            mode_bytes = mode_path.stat().st_size
            mode = load_json(mode_path)
            original_loader = scorer_m56.load_outcome_inputs
            loads = {"count": 0}

            def counted_loader(value: str) -> dict[str, Any]:
                loads["count"] += 1
                return original_loader(value)

            with mock.patch.object(scorer_m56, "load_outcome_inputs", side_effect=counted_loader):
                m56_result = crash_safe_m56.execute_crash_safe_outcome_join_formal_scoring(run_id)
            validation_started = perf_counter()
            validation = validate_m57_preoutcome_diagnostic_mode(run_id)
            validation_seconds = perf_counter() - validation_started
            replay = commit_m57_preoutcome_diagnostic_mode(run_id)
    value = {
        "schema": REHEARSAL_SCHEMA,
        "version": "1.0.0",
        "status": "forged_preoutcome_commit_then_m56_result_link_validated",
        "contract_hash": validate_contract()["contract_hash"],
        "fixture_kind": "temporary_forged_30_row_m56_run_engineering_only",
        "first_commit_status": first["status"],
        "first_commit_outcome_state_count": len(first["outcome_state_artifacts_now"]),
        "mode_commitment_hash": mode["mode_commitment_hash"],
        "substitution_plan_commitment_hash": mode["substitution_plan_commitment_hash"],
        "bound_stage_count": len(mode["stage_plans"]),
        "bound_m56_artifact_hash_count": 17,
        "commitment_utf8_bytes": mode_bytes,
        "commit_seconds": commit_seconds,
        "forged_m56_outcome_loader_calls": loads["count"],
        "m56_result_created_in_forged_fixture": m56_result["formal_result_created"],
        "post_result_link_valid": validation["m56_result_link_valid"],
        "post_result_validation_seconds": validation_seconds,
        "post_result_replay_status": replay["status"],
        "post_result_mode_hash_unchanged": replay["mode_commitment_hash"] == mode["mode_commitment_hash"],
        "retroactive_first_commit_allowed": False,
        "m57_1_model_call_count": 0,
        "real_target_outcome_access_count": 0,
        "formal_m57_result_created": False,
        "m58_authorized": False,
        "claim_boundary": load_contract()["claim_boundary"],
    }
    value["rehearsal_hash"] = digest(value)
    report = validate_rehearsal(value)
    if not report["valid"]:
        raise AssertionError("M57.1 rehearsal invalid: " + "; ".join(report["errors"]))
    return value


def validate_rehearsal(value: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    expected = {
        "schema", "version", "status", "contract_hash", "fixture_kind",
        "first_commit_status", "first_commit_outcome_state_count", "mode_commitment_hash",
        "substitution_plan_commitment_hash", "bound_stage_count", "bound_m56_artifact_hash_count",
        "commitment_utf8_bytes", "commit_seconds", "forged_m56_outcome_loader_calls",
        "m56_result_created_in_forged_fixture", "post_result_link_valid",
        "post_result_validation_seconds", "post_result_replay_status",
        "post_result_mode_hash_unchanged", "retroactive_first_commit_allowed",
        "m57_1_model_call_count", "real_target_outcome_access_count",
        "formal_m57_result_created", "m58_authorized", "claim_boundary", "rehearsal_hash",
    }
    if not isinstance(value, dict) or set(value) != expected:
        return {"valid": False, "errors": ["rehearsal.fields"]}
    unhashed = {key: child for key, child in value.items() if key != "rehearsal_hash"}
    if value.get("rehearsal_hash") != digest(unhashed):
        errors.append("rehearsal.hash")
    if value.get("schema") != REHEARSAL_SCHEMA or value.get("status") != "forged_preoutcome_commit_then_m56_result_link_validated":
        errors.append("rehearsal.schema_or_status")
    if value.get("contract_hash") != validate_contract()["contract_hash"]:
        errors.append("rehearsal.contract")
    if value.get("first_commit_outcome_state_count") != 0:
        errors.append("rehearsal.preoutcome_order")
    if value.get("bound_stage_count") != 5 or value.get("bound_m56_artifact_hash_count") != 17:
        errors.append("rehearsal.bindings")
    if value.get("forged_m56_outcome_loader_calls") != 1:
        errors.append("rehearsal.forged_outcome_load")
    if value.get("m56_result_created_in_forged_fixture") is not True or value.get("post_result_link_valid") is not True:
        errors.append("rehearsal.result_link")
    if value.get("post_result_replay_status") != "existing_identical_preoutcome_diagnostic_mode_validated":
        errors.append("rehearsal.replay")
    if value.get("post_result_mode_hash_unchanged") is not True:
        errors.append("rehearsal.mode_drift")
    if value.get("retroactive_first_commit_allowed") is not False:
        errors.append("rehearsal.retroactive")
    if value.get("m57_1_model_call_count") != 0 or value.get("real_target_outcome_access_count") != 0:
        errors.append("rehearsal.real_or_model")
    if value.get("formal_m57_result_created") is not False or value.get("m58_authorized") is not False:
        errors.append("rehearsal.authority")
    return {"valid": not errors, "errors": errors, "rehearsal_hash": value.get("rehearsal_hash")}


def build_live_audit() -> dict[str, Any]:
    upstream = localization_m57.build_live_audit()
    value = {
        "schema": AUDIT_SCHEMA,
        "version": "1.0.0",
        "status": "m57_1_mechanism_ready_but_no_live_preoutcome_run_or_formal_result",
        "contract_valid": validate_contract()["valid"],
        "contract_hash": validate_contract()["contract_hash"],
        "counts": deepcopy(upstream["counts"]),
        "live_m57_1_commitment_created": False,
        "live_m56_result_created": upstream["m56_formal_result_created"],
        "formal_m57_execution_authorized": False,
        "formal_m57_result_created": False,
        "target_outcome_access_count": 0,
        "formal_model_call_count": 0,
        "blocking_gates": deepcopy(upstream["blocking_gates"]),
        "claim_boundary": load_contract()["claim_boundary"],
    }
    value["audit_hash"] = digest(value)
    return value


def load_saved_rehearsal(path: str | Path = RESULT_PATH) -> dict[str, Any]:
    value = load_json(path)
    report = validate_rehearsal(value)
    if not report["valid"]:
        raise PermissionError("invalid saved M57.1 rehearsal: " + "; ".join(report["errors"]))
    return value


def render_dashboard(
    rehearsal: dict[str, Any] | None = None, audit: dict[str, Any] | None = None
) -> str:
    rehearsal = deepcopy(rehearsal or load_saved_rehearsal())
    audit = deepcopy(audit or build_live_audit())
    if not validate_rehearsal(rehearsal)["valid"]:
        raise PermissionError("invalid M57.1 rehearsal cannot be rendered")
    counts = audit["counts"]
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>M57.1 答案前診斷封存</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#08131c;color:#effaff;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}main{{max-width:1160px;margin:auto;padding:28px}}section{{border:1px solid #34576a;border-radius:20px;background:#0e202b;padding:24px;margin-bottom:18px}}.hero{{background:linear-gradient(135deg,#173744,#34263e)}}h1{{font-size:clamp(30px,5vw,46px);margin:13px 0}}p{{color:#c6dce5;line-height:1.65}}.deny{{display:inline-block;background:#6a2734;color:#ffe1e6;padding:8px 12px;border-radius:999px;font-weight:850}}.flow{{display:grid;grid-template-columns:1fr auto 1fr auto 1fr;gap:12px;align-items:stretch}}.card{{min-width:0;border:1px solid #446779;border-radius:16px;background:#091922;padding:18px}}.card b,.card span{{display:block;overflow-wrap:anywhere}}.card b{{color:#8ce7c9;font-size:18px}}.card span{{margin-top:8px;color:#bfd5de;line-height:1.5}}.arrow{{align-self:center;color:#ffd47e;font-size:31px;font-weight:900}}.compare{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}.before{{border-color:#bf6a73}}.after{{border-color:#54b995}}.metric{{font-size:32px;font-weight:900;color:#7fe9c5}}.chips{{display:flex;gap:8px;flex-wrap:wrap}}.chips i{{font-style:normal;background:#183240;border-radius:999px;padding:7px 10px;color:#cae4ed}}.boundary{{border-left:6px solid #e1a552;background:#282014}}@media(max-width:850px){{.flow,.compare{{grid-template-columns:1fr}}.arrow{{text-align:center;transform:rotate(90deg)}}}}
</style></head><body><main><section class="hero"><span class="deny">FORMAL M57 DENIED · V7 {counts['v7_slots_by_ledger'][0]}/18 + {counts['v7_slots_by_ledger'][1]}/18</span><h1>M57.1 · 先封存怎麼查錯，再開答案</h1><p>如果看完結果才決定要替換哪一層，就不能證明診斷沒有迎合答案。這一層把五個診斷計畫與同一份資料、模型、硬體及資源 hash 先耐久封存。</p></section>
<section><h2>可驗證的時間順序</h2><div class="flow"><div class="card"><b>① M56 預測已封存</b><span>30 samples · 210 predictions · durable release</span></div><div class="arrow">→</div><div class="card"><b>② M57 診斷計畫封存</b><span>5 stages · {rehearsal['bound_m56_artifact_hash_count']} exact artifact bindings · 0 outcome read</span></div><div class="arrow">→</div><div class="card"><b>③ 之後才可開答案</b><span>forged rehearsal 1 load；真實資料仍是 0</span></div></div></section>
<section><h2>修改前後</h2><div class="compare"><div class="card before"><b>修改前</b><div class="metric">0 個 M57 commitment</div><p>未來即使有 M56 結果，也無法證明 stage plan 不是事後補做。</p></div><div class="card after"><b>修改後（工程 fixture）</b><div class="metric">5 stages · hash 不變</div><p>先 commit、再跑 forged M56、最後重驗仍完全一致；事後第一次補做會拒絕。</p></div></div></section>
<section><h2>到底綁住了什麼</h2><div class="chips"><i>dataset / packet</i><i>runtime / hardware</i><i>model manifest</i><i>Equation artifacts</i><i>schedule / submission</i><i>prediction commitment</i><i>call ledger</i><i>durable release</i><i>expected outcome hashes</i></div><p>封存檔 {rehearsal['commitment_utf8_bytes']} bytes；M57.1 自己新增模型呼叫 = 0，真實 target outcome access = 0。</p></section>
<section class="boundary"><h2>這不是正式診斷結果</h2><p>這次只證明「診斷計畫先於答案」的機制在暫存 forged run 中可運作，沒有產生任何 component prediction，也沒有定位 Uruha 的錯誤層。真人時間資料仍是 {counts['real_temporal_rows']}/30，formal M56 result = 0，M58 仍禁止開始。</p></section></main></body></html>"""


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
    parser = argparse.ArgumentParser(description="M57.1 pre-outcome diagnostic commitment")
    parser.add_argument("--rehearsal", action="store_true")
    parser.add_argument("--serve", type=int)
    args = parser.parse_args()
    if args.serve is not None:
        serve_demo(args.serve)
    elif args.rehearsal:
        print(json.dumps(build_engineering_rehearsal(), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(build_live_audit(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
