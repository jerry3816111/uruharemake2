#!/usr/bin/env python3
"""M57.3 crash-safe sanctioned outcome-to-analyzer bridge.

The public surface accepts only a run id.  It revalidates the complete M57.2
pre-outcome capsule and M56.10 result chain, commits a no-retry diagnostic
intent, then performs one separately authorized private-outcome load.  The
joined checkpoint is private; only aggregate localization is committed.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import inspect
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from typing import Any
from unittest import mock

import m55_temporal_row_contract as temporal_m55
import m56_4_separate_formal_scorer as scorer_m56
import m56_7_mac_full_sync_generation as durable_m56
import m56_9_single_writer_formal_scoring as single_writer_m56
import m56_10_crash_safe_outcome_join as crash_safe_m56
import m57_component_error_localization as localization_m57
import m57_1_preoutcome_diagnostic_commitment as commitment_m57
import m57_2_component_prediction_capsule as component_m57


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/m57_3_sanctioned_outcome_analyzer_bridge_v1.json"
RESULT_PATH = ROOT / "analysis/m57_3_sanctioned_outcome_analyzer_bridge_rehearsal_2026-09-04.json"
MODE_FILENAME = "m57_3_outcome_analyzer_bridge_mode.json"
INTENT_FILENAME = "m57_3_outcome_analyzer_bridge_intent.json"
CHECKPOINT_FILENAME = "m57_3_private_joined_analyzer_checkpoint.json"
FAILURE_FILENAME = "m57_3_outcome_analyzer_bridge_terminal_failure.json"
RESULT_FILENAME = "m57_3_component_localization_result.json"
COMMITMENT_FILENAME = "m57_3_component_localization_result_commitment.json"

MODE_SCHEMA = "uruha_m57_sanctioned_outcome_analyzer_bridge_mode_v1"
INTENT_SCHEMA = "uruha_m57_sanctioned_outcome_analyzer_bridge_intent_v1"
CHECKPOINT_SCHEMA = "uruha_m57_private_joined_analyzer_checkpoint_v1"
FAILURE_SCHEMA = "uruha_m57_ambiguous_outcome_analyzer_bridge_failure_v1"
RESULT_SCHEMA = "uruha_m57_sanctioned_component_localization_result_v1"
COMMITMENT_SCHEMA = "uruha_m57_sanctioned_component_localization_commitment_v1"
REHEARSAL_SCHEMA = "uruha_m57_sanctioned_outcome_analyzer_bridge_rehearsal_v1"
AUDIT_SCHEMA = "uruha_m57_sanctioned_outcome_analyzer_bridge_live_audit_v1"

FORMAL_EVIDENCE_KIND = "real_independent_preoutcome_component_evidence"
ENGINEERING_EVIDENCE_KIND = "author_constructed_engineering_only"


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
        "frozen_dependencies", "required_upstream_chain", "outcome_access",
        "transformation", "state_machine", "durability", "current_authorization",
        "claim_boundary",
    }
    if set(contract) != expected:
        errors.append("contract.fields")
    if contract.get("schema") != "uruha_m57_sanctioned_outcome_analyzer_bridge_contract_v1":
        errors.append("contract.schema")
    if contract.get("version") != "1.0.0":
        errors.append("contract.version")
    if contract.get("status") != "prospective_frozen_before_implementation_and_any_real_m57_diagnostic_target_outcome_access":
        errors.append("contract.status")
    api = contract.get("public_api") or {}
    if api.get("execute_function") != "execute_m57_sanctioned_outcome_analyzer_bridge":
        errors.append("api.execute")
    if api.get("validate_function") != "validate_m57_sanctioned_outcome_analyzer_bridge":
        errors.append("api.validate")
    if api.get("parameters") != ["run_id"]:
        errors.append("api.parameters")
    if api.get("labels_bundle_provider_readiness_authorization_retry_or_resource_injection_allowed") is not False:
        errors.append("api.injection")
    if list(inspect.signature(execute_m57_sanctioned_outcome_analyzer_bridge).parameters) != ["run_id"]:
        errors.append("api.execute_signature")
    if list(inspect.signature(validate_m57_sanctioned_outcome_analyzer_bridge).parameters) != ["run_id"]:
        errors.append("api.validate_signature")
    dependencies = contract.get("frozen_dependencies") or {}
    if len(dependencies) != 9:
        errors.append("dependencies.count")
    for relative, expected_hash in dependencies.items():
        path = ROOT / relative
        if not path.is_file() or sha256_file(path) != expected_hash:
            errors.append(f"dependency:{relative}")
    if contract.get("required_upstream_chain") != [
        "valid_m57_1_preoutcome_mode",
        "complete_valid_m57_2_component_prediction_capsule",
        "complete_valid_m56_8_and_m56_10_result_chain",
    ]:
        errors.append("upstream_chain")
    access = contract.get("outcome_access") or {}
    expected_counts = {
        "m56_scoring_sanctioned_load_count": 1,
        "m57_diagnostic_sanctioned_load_count": 1,
        "complete_run_total_named_sanctioned_load_count": 2,
        "m57_successful_replay_additional_load_count": 0,
        "m57_checkpoint_restart_additional_load_count": 0,
        "m57_intent_without_checkpoint_additional_load_count": 0,
    }
    for name, expected_value in expected_counts.items():
        if access.get(name) != expected_value:
            errors.append(f"outcome_access.{name}")
    for name in (
        "same_per_run_scoring_lock_required",
        "mode_and_intent_committed_before_m57_diagnostic_load",
    ):
        if access.get(name) is not True:
            errors.append(f"outcome_access.{name}")
    if access.get("labels_from_caller_allowed") is not False or access.get("labels_inferred_from_aggregate_score_allowed") is not False:
        errors.append("outcome_access.labels")
    transform = contract.get("transformation") or {}
    if transform.get("sample_count") != 30 or transform.get("label_count") != 13:
        errors.append("transformation.counts")
    if transform.get("preoutcome_available_stage_ids") != ["perception", "retrieval", "state"]:
        errors.append("transformation.stages")
    for name in ("decision_postoutcome_one_hot_ceiling", "unchanged_m57_analyzer_required"):
        if transform.get(name) is not True:
            errors.append(f"transformation.{name}")
    for name in (
        "decision_eligible_for_causal_ranking",
        "realization_without_independent_blind_human_ratings_available",
        "preoutcome_probabilities_may_change",
        "mechanics_projection_may_create_formal_authority",
    ):
        if transform.get(name) is not False:
            errors.append(f"transformation.{name}")
    if contract.get("state_machine") != [
        "upstream_chain_revalidated", "bridge_mode_committed",
        "outcome_join_intent_committed", "single_m57_diagnostic_outcome_load",
        "private_joined_checkpoint_committed", "unchanged_m57_analyzer_projection_validated",
        "aggregate_result_committed", "result_hash_commitment_committed",
    ]:
        errors.append("state_machine")
    durability = contract.get("durability") or {}
    for name in (
        "atomic_exclusive_writes_required", "file_fsync_required",
        "file_full_sync_required_when_supported", "directory_fsync_required",
        "directory_full_sync_required_when_supported",
    ):
        if durability.get(name) is not True:
            errors.append(f"durability.{name}")
    if durability.get("same_run_retry_after_intent_allowed") is not False:
        errors.append("durability.retry")
    current = contract.get("current_authorization") or {}
    if not current or any(value is not False for value in current.values()):
        errors.append("authorization")
    return {
        "valid": not errors,
        "errors": errors,
        "contract_hash": digest(contract),
        "binding_count": len(dependencies),
    }


def _paths(run_id: str) -> dict[str, Path]:
    paths = component_m57._paths(run_id)
    return {
        **paths,
        "m57_3_mode": paths["telemetry"] / MODE_FILENAME,
        "m57_3_intent": paths["telemetry"] / INTENT_FILENAME,
        "m57_3_checkpoint": paths["scoring"] / CHECKPOINT_FILENAME,
        "m57_3_failure": paths["telemetry"] / FAILURE_FILENAME,
        "m57_3_result": paths["scoring"] / RESULT_FILENAME,
        "m57_3_commitment": paths["commitments"] / COMMITMENT_FILENAME,
    }


def _write_or_validate_identical(path: Path, value: dict[str, Any]) -> str:
    if path.exists():
        if load_json(path) != value:
            raise ValueError(f"existing immutable M57.3 artifact differs: {path.name}")
        return "validated_existing_identical"
    durable_m56._durable_atomic_write_json(path, value, exclusive=True)
    return "created_full_sync"


def _load_upstream(run_id: str, *, allow_forged: bool) -> dict[str, Any]:
    context = component_m57._load_preoutcome_context(run_id)
    paths = _paths(run_id)
    component_validation = component_m57._validate_m57_preoutcome_component_predictions(
        run_id, allow_forged=allow_forged
    )
    if not component_validation["valid"]:
        raise PermissionError(
            "M57.3 requires a valid M57.2 capsule: "
            + "; ".join(component_validation["errors"])
        )
    evidence = load_json(paths["evidence"])
    evidence_kind = evidence.get("data_kind")
    if allow_forged:
        if evidence_kind != ENGINEERING_EVIDENCE_KIND:
            raise PermissionError("internal M57.3 rehearsal accepts only the named engineering evidence kind")
    elif evidence_kind != FORMAL_EVIDENCE_KIND:
        raise PermissionError("M57.3 formal bridge requires real independent pre-outcome evidence")
    link = commitment_m57._completed_m56_result_link(
        paths, context["mode"], context["authorization"]
    )
    if not link["present"] or not link["valid"]:
        raise PermissionError(
            "M57.3 requires a complete valid M56.10 result chain: "
            + "; ".join(link.get("errors") or ["missing_result"])
        )
    report = load_json(paths["scoring"] / scorer_m56.SCORE_REPORT_FILENAME)
    result_commitment = load_json(paths["commitments"] / scorer_m56.RESULT_COMMITMENT_FILENAME)
    checkpoint_m56 = load_json(paths["m56_10_checkpoint"])
    capsule = load_json(paths["m57_2_capsule"])
    capsule_commitment = load_json(paths["m57_2_commitment"])
    if scorer_m56.validate_score_report(report)["valid"] is not True:
        raise ValueError("M56 score report invalid")
    if scorer_m56.validate_result_commitment(result_commitment, report)["valid"] is not True:
        raise ValueError("M56 result commitment invalid")
    return {
        "context": context,
        "paths": paths,
        "evidence": evidence,
        "component_validation": component_validation,
        "capsule": capsule,
        "capsule_commitment": capsule_commitment,
        "m56_report": report,
        "m56_result_commitment": result_commitment,
        "m56_checkpoint": checkpoint_m56,
        "formal": not allow_forged,
        "m56_result_link": link,
    }


def build_bridge_mode(run_id: str, upstream: dict[str, Any]) -> dict[str, Any]:
    context = upstream["context"]
    capsule = upstream["capsule"]
    report = upstream["m56_report"]
    value = {
        "schema": MODE_SCHEMA,
        "version": "1.0.0",
        "status": "upstream_result_and_preoutcome_predictions_bound_before_m57_diagnostic_access",
        "run_id": run_id,
        "contract_hash": validate_contract()["contract_hash"],
        "formal_authorization": upstream["formal"],
        "evidence_kind": upstream["evidence"]["data_kind"],
        "m57_analyzer_contract_hash": context["mode"]["m57_analyzer_contract_hash"],
        "m57_analyzer_implementation_sha256": sha256_file(ROOT / "m57_component_error_localization.py"),
        "m57_1_mode_commitment_hash": context["mode"]["mode_commitment_hash"],
        "m57_2_evidence_manifest_hash": capsule["evidence_manifest_hash"],
        "m57_2_schedule_hash": capsule["schedule_hash"],
        "m57_2_capsule_hash": capsule["capsule_hash"],
        "m57_2_call_ledger_hash": load_json(upstream["paths"]["m57_2_ledger"])["ledger_hash"],
        "m57_2_prediction_commitment_hash": upstream["capsule_commitment"]["commitment_hash"],
        "m56_score_checkpoint_hash": upstream["m56_checkpoint"]["score_checkpoint_hash"],
        "m56_score_report_hash": report["score_report_hash"],
        "m56_result_commitment_hash": upstream["m56_result_commitment"]["result_commitment_hash"],
        "dataset_hash": report["dataset_hash"],
        "prediction_packet_hash": report["prediction_packet_hash"],
        "expected_outcome_key_hash": report["outcome_key_hash"],
        "expected_split_report_hash": report["split_report_hash"],
        "sample_count": 30,
        "preoutcome_prediction_count": capsule["available_prediction_count"],
        "m56_scoring_outcome_load_count": 1,
        "m57_diagnostic_outcome_load_authorization_count": 1,
        "retry_count": 0,
        "fallback_count": 0,
        "production_memory_write_authorized": False,
        "external_deployment_authorized": False,
    }
    value["mode_hash"] = digest(value)
    return value


def validate_bridge_mode(value: dict[str, Any], run_id: str, upstream: dict[str, Any]) -> dict[str, Any]:
    expected = build_bridge_mode(run_id, upstream)
    errors = [] if value == expected else ["mode.content_or_hash"]
    return {"valid": not errors, "errors": errors, "mode_hash": value.get("mode_hash")}


def build_join_intent(run_id: str, mode: dict[str, Any]) -> dict[str, Any]:
    value = {
        "schema": INTENT_SCHEMA,
        "version": "1.0.0",
        "status": "m57_diagnostic_outcome_join_started_no_retry",
        "run_id": run_id,
        "contract_hash": validate_contract()["contract_hash"],
        "mode_hash": mode["mode_hash"],
        "formal_authorization": mode["formal_authorization"],
        "expected_outcome_key_hash": mode["expected_outcome_key_hash"],
        "expected_split_report_hash": mode["expected_split_report_hash"],
        "m57_2_capsule_hash": mode["m57_2_capsule_hash"],
        "m56_score_report_hash": mode["m56_score_report_hash"],
        "private_outcome_load_authorization_count": 1,
        "caller_label_injection_allowed": False,
        "retry_count": 0,
        "fallback_count": 0,
        "production_memory_write_authorized": False,
        "external_deployment_authorized": False,
    }
    value["intent_hash"] = digest(value)
    return value


def validate_join_intent(value: dict[str, Any], run_id: str, mode: dict[str, Any]) -> dict[str, Any]:
    expected = build_join_intent(run_id, mode)
    errors = [] if value == expected else ["intent.content_or_hash"]
    return {"valid": not errors, "errors": errors, "intent_hash": value.get("intent_hash")}


def _projection(bundle: dict[str, Any]) -> dict[str, Any]:
    value = deepcopy(bundle)
    value["data_kind"] = "synthetic_engineering_only"
    value["fixture_kind"] = "mechanics_projection_of_authenticated_m57_3_join"
    value["formal_authorization"] = False
    value["claim_boundary"] = localization_m57.load_contract()["claim_boundary"]
    value.pop("bundle_hash", None)
    value["bundle_hash"] = localization_m57.digest(value)
    return value


def _standard_substitution(stage_id: str, source: dict[str, Any]) -> dict[str, Any]:
    return {
        "stage_id": stage_id,
        "availability": source["availability"],
        "changed_component": source["changed_component"],
        "plan_hash": source["plan_hash"],
        "downstream_recomputed": source["downstream_recomputed"],
        "probabilities": deepcopy(source["probabilities"]),
        "downstream_output_hash": source["downstream_output_hash"],
        "evidence_available_before_outcome": source["evidence_available_before_outcome"],
        "future_outcome_used": source["future_outcome_used"],
    }


def build_joined_bundle(
    upstream: dict[str, Any], outcome_key: dict[str, Any], outcome_validation: dict[str, Any]
) -> dict[str, Any]:
    if not outcome_validation["valid"]:
        raise ValueError("joined bundle requires validated outcome input")
    labels = tuple(outcome_validation["label_order"])
    if labels != localization_m57.LABELS:
        raise ValueError("outcome label order differs from frozen M57 taxonomy")
    outcomes = {row["sample_id"]: row for row in outcome_key["outcomes"]}
    capsule = upstream["capsule"]
    rows = []
    for source_row in capsule["rows"]:
        sample_id = source_row["sample_id"]
        if sample_id not in outcomes:
            raise ValueError(f"missing outcome for {sample_id}")
        observed = outcomes[sample_id]["actual_observed_behavior"]
        substitutions = {
            stage_id: _standard_substitution(stage_id, source_row["substitutions"][stage_id])
            for stage_id in ("perception", "retrieval", "state")
        }
        decision_probabilities = {
            label: 1.0 if label == observed else 0.0 for label in labels
        }
        substitutions["decision"] = {
            "stage_id": "decision",
            "availability": "available",
            "changed_component": "decision",
            "plan_hash": upstream["context"]["mode"]["stage_plans"]["decision"]["plan_hash"],
            "downstream_recomputed": True,
            "probabilities": decision_probabilities,
            "downstream_output_hash": digest(decision_probabilities),
            "evidence_available_before_outcome": False,
            "future_outcome_used": True,
        }
        substitutions["realization"] = _standard_substitution(
            "realization", source_row["substitutions"]["realization"]
        )
        rows.append({
            "sample_id": sample_id,
            "observed_label": observed,
            "original_probabilities": deepcopy(source_row["original_probabilities"]),
            "original_output_hash": source_row["original_output_hash"],
            "substitutions": substitutions,
        })
    formal = upstream["formal"]
    plans = deepcopy(upstream["context"]["mode"]["stage_plans"])
    value = {
        "schema": localization_m57.BUNDLE_SCHEMA,
        "version": "1.0.0",
        "status": "all_predictions_and_stage_plans_committed_before_outcome_scoring",
        "data_kind": "real_formal_m56_diagnostic" if formal else "synthetic_engineering_only",
        "fixture_kind": (
            "authorized_real_30_row_postresult_component_diagnostic"
            if formal else "author_constructed_full_chain_bridge_mechanics"
        ),
        "label_order": list(labels),
        "sample_count": 30,
        "prediction_commitment_hash": upstream["capsule_commitment"]["commitment_hash"],
        "stage_plans": plans,
        "substitution_plan_commitment_hash": localization_m57.digest(plans),
        "outcome_access_after_all_predictions_committed": True,
        "same_resource_contract": True,
        "single_stage_change_verified": True,
        "retry_count": 0,
        "fallback_count": 0,
        "formal_authorization": formal,
        "rows": rows,
        "claim_boundary": localization_m57.load_contract()["claim_boundary"],
    }
    value["bundle_hash"] = localization_m57.digest(value)
    return value


def validate_joined_bundle(bundle: dict[str, Any], upstream: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    formal = upstream["formal"]
    if bundle.get("data_kind") != ("real_formal_m56_diagnostic" if formal else "synthetic_engineering_only"):
        errors.append("bundle.data_kind")
    if bundle.get("formal_authorization") is not formal:
        errors.append("bundle.formal_authorization")
    if bundle.get("prediction_commitment_hash") != upstream["capsule_commitment"]["commitment_hash"]:
        errors.append("bundle.prediction_commitment")
    if bundle.get("substitution_plan_commitment_hash") != upstream["context"]["mode"]["substitution_plan_commitment_hash"]:
        errors.append("bundle.plan_commitment")
    if bundle.get("bundle_hash") != localization_m57.digest({key: value for key, value in bundle.items() if key != "bundle_hash"}):
        errors.append("bundle.hash")
    source_rows = {row["sample_id"]: row for row in upstream["capsule"]["rows"]}
    rows = bundle.get("rows") or []
    if not isinstance(rows, list) or len(rows) != 30 or [row.get("sample_id") for row in rows] != list(source_rows):
        errors.append("bundle.rows")
    else:
        for index, row in enumerate(rows):
            source = source_rows[row["sample_id"]]
            if row.get("original_probabilities") != source["original_probabilities"] or row.get("original_output_hash") != source["original_output_hash"]:
                errors.append(f"row[{index}].original")
            observed = row.get("observed_label")
            if observed not in localization_m57.LABELS:
                errors.append(f"row[{index}].observed")
            substitutions = row.get("substitutions") or {}
            if tuple(substitutions) != localization_m57.STAGE_IDS:
                errors.append(f"row[{index}].stages")
                continue
            for stage_id in ("perception", "retrieval", "state", "realization"):
                expected = _standard_substitution(stage_id, source["substitutions"][stage_id])
                if substitutions[stage_id] != expected:
                    errors.append(f"row[{index}].{stage_id}.mutation")
            decision = substitutions["decision"]
            one_hot = {label: 1.0 if label == observed else 0.0 for label in localization_m57.LABELS}
            expected_decision = {
                "stage_id": "decision", "availability": "available",
                "changed_component": "decision",
                "plan_hash": upstream["context"]["mode"]["stage_plans"]["decision"]["plan_hash"],
                "downstream_recomputed": True, "probabilities": one_hot,
                "downstream_output_hash": digest(one_hot),
                "evidence_available_before_outcome": False, "future_outcome_used": True,
            }
            if decision != expected_decision:
                errors.append(f"row[{index}].decision")
    projected = _projection(bundle)
    projection_validation = localization_m57.validate_bundle(projected)
    errors.extend(f"projection:{name}" for name in projection_validation["errors"])
    core = None
    if not errors:
        core = localization_m57.analyze_component_substitution_bundle(projected)
    return {
        "valid": not errors,
        "errors": errors,
        "bundle_hash": bundle.get("bundle_hash"),
        "projection_hash": projected.get("bundle_hash"),
        "core_analysis": core,
    }


def build_private_checkpoint(
    run_id: str, mode: dict[str, Any], intent: dict[str, Any], upstream: dict[str, Any],
    bundle: dict[str, Any], joined_validation: dict[str, Any], outcome_validation: dict[str, Any],
) -> dict[str, Any]:
    if not joined_validation["valid"]:
        raise ValueError("checkpoint requires valid joined bundle")
    value = {
        "schema": CHECKPOINT_SCHEMA,
        "version": "1.0.0",
        "status": "one_m57_diagnostic_outcome_join_and_analysis_full_sync_committed",
        "run_id": run_id,
        "contract_hash": validate_contract()["contract_hash"],
        "mode_hash": mode["mode_hash"],
        "intent_hash": intent["intent_hash"],
        "formal_authorization": upstream["formal"],
        "m57_2_capsule_hash": upstream["capsule"]["capsule_hash"],
        "m56_score_report_hash": upstream["m56_report"]["score_report_hash"],
        "outcome_key_hash": outcome_validation["outcome_key_hash"],
        "split_report_hash": outcome_validation["split_report_hash"],
        "joined_bundle_hash": bundle["bundle_hash"],
        "analysis_projection_hash": joined_validation["projection_hash"],
        "core_analysis_hash": joined_validation["core_analysis"]["analysis_hash"],
        "joined_bundle": deepcopy(bundle),
        "core_analysis": deepcopy(joined_validation["core_analysis"]),
        "observed_label_count": 30,
        "decision_ceiling_count": 30,
        "preoutcome_prediction_count": upstream["capsule"]["available_prediction_count"],
        "m57_diagnostic_private_outcome_load_count": 1,
        "m57_model_call_count": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "production_memory_write_authorized": False,
        "external_deployment_authorized": False,
    }
    value["checkpoint_hash"] = digest(value)
    return value


def validate_private_checkpoint(
    checkpoint: dict[str, Any], run_id: str, mode: dict[str, Any],
    intent: dict[str, Any], upstream: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    expected_fields = {
        "schema", "version", "status", "run_id", "contract_hash", "mode_hash",
        "intent_hash", "formal_authorization", "m57_2_capsule_hash",
        "m56_score_report_hash", "outcome_key_hash", "split_report_hash",
        "joined_bundle_hash", "analysis_projection_hash", "core_analysis_hash",
        "joined_bundle", "core_analysis", "observed_label_count",
        "decision_ceiling_count", "preoutcome_prediction_count",
        "m57_diagnostic_private_outcome_load_count", "m57_model_call_count",
        "retry_count", "fallback_count", "production_memory_write_authorized",
        "external_deployment_authorized", "checkpoint_hash",
    }
    if not isinstance(checkpoint, dict) or set(checkpoint) != expected_fields:
        return {"valid": False, "errors": ["checkpoint.fields"]}
    if checkpoint.get("checkpoint_hash") != digest({key: value for key, value in checkpoint.items() if key != "checkpoint_hash"}):
        errors.append("checkpoint.hash")
    bindings = {
        "schema": CHECKPOINT_SCHEMA,
        "version": "1.0.0",
        "status": "one_m57_diagnostic_outcome_join_and_analysis_full_sync_committed",
        "run_id": run_id,
        "contract_hash": validate_contract()["contract_hash"],
        "mode_hash": mode["mode_hash"],
        "intent_hash": intent["intent_hash"],
        "formal_authorization": upstream["formal"],
        "m57_2_capsule_hash": upstream["capsule"]["capsule_hash"],
        "m56_score_report_hash": upstream["m56_report"]["score_report_hash"],
        "outcome_key_hash": mode["expected_outcome_key_hash"],
        "split_report_hash": mode["expected_split_report_hash"],
        "observed_label_count": 30,
        "decision_ceiling_count": 30,
        "preoutcome_prediction_count": upstream["capsule"]["available_prediction_count"],
        "m57_diagnostic_private_outcome_load_count": 1,
        "m57_model_call_count": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "production_memory_write_authorized": False,
        "external_deployment_authorized": False,
    }
    for name, expected in bindings.items():
        if checkpoint.get(name) != expected:
            errors.append(f"checkpoint.binding:{name}")
    bundle = checkpoint.get("joined_bundle") or {}
    joined = validate_joined_bundle(bundle, upstream)
    errors.extend(f"joined:{name}" for name in joined["errors"])
    if checkpoint.get("joined_bundle_hash") != bundle.get("bundle_hash"):
        errors.append("checkpoint.bundle_hash")
    if checkpoint.get("analysis_projection_hash") != joined.get("projection_hash"):
        errors.append("checkpoint.projection_hash")
    expected_core = joined.get("core_analysis")
    if expected_core is None or checkpoint.get("core_analysis") != expected_core:
        errors.append("checkpoint.core_analysis")
    if expected_core is not None and checkpoint.get("core_analysis_hash") != expected_core.get("analysis_hash"):
        errors.append("checkpoint.core_hash")
    return {
        "valid": not errors,
        "errors": errors,
        "checkpoint_hash": checkpoint.get("checkpoint_hash"),
    }


def build_terminal_failure(run_id: str, mode: dict[str, Any], intent: dict[str, Any]) -> dict[str, Any]:
    value = {
        "schema": FAILURE_SCHEMA,
        "version": "1.0.0",
        "status": "terminal_no_retry_ambiguous_m57_diagnostic_outcome_state",
        "run_id": run_id,
        "contract_hash": validate_contract()["contract_hash"],
        "mode_hash": mode["mode_hash"],
        "intent_hash": intent["intent_hash"],
        "reason": "durable_intent_exists_without_valid_durable_joined_checkpoint",
        "historical_m57_diagnostic_outcome_load_count": "unknown_zero_or_one",
        "additional_outcome_load_authorized": False,
        "retry_count": 0,
        "fallback_count": 0,
        "formal_result_created": False,
        "m58_authorized": False,
        "production_memory_write_authorized": False,
        "external_deployment_authorized": False,
    }
    value["failure_hash"] = digest(value)
    return value


def build_result(run_id: str, checkpoint: dict[str, Any], upstream: dict[str, Any]) -> dict[str, Any]:
    core = checkpoint["core_analysis"]
    formal = upstream["formal"]
    value = {
        "schema": RESULT_SCHEMA,
        "version": "1.0.0",
        "status": "formal_component_localization_complete" if formal else "engineering_full_chain_bridge_complete",
        "run_id": run_id,
        "contract_hash": validate_contract()["contract_hash"],
        "data_kind": "real_formal_m57_diagnostic" if formal else "author_constructed_engineering_only",
        "formal_authorization": formal,
        "formal_result_created": formal,
        "m57_1_mode_commitment_hash": upstream["context"]["mode"]["mode_commitment_hash"],
        "m57_2_prediction_commitment_hash": upstream["capsule_commitment"]["commitment_hash"],
        "m56_score_report_hash": upstream["m56_report"]["score_report_hash"],
        "m56_result_commitment_hash": upstream["m56_result_commitment"]["result_commitment_hash"],
        "checkpoint_hash": checkpoint["checkpoint_hash"],
        "joined_bundle_hash": checkpoint["joined_bundle_hash"],
        "analysis_projection_hash": checkpoint["analysis_projection_hash"],
        "core_analysis_hash": core["analysis_hash"],
        "sample_count": 30,
        "observed_label_count": 30,
        "preoutcome_component_prediction_count": checkpoint["preoutcome_prediction_count"],
        "decision_ceiling_count": 30,
        "available_stage_substitution_count": checkpoint["preoutcome_prediction_count"] + 30,
        "realization_stage_available": False,
        "stage_results": deepcopy(core["stage_results"]),
        "leading_recoverable_stage": core["leading_recoverable_stage"],
        "attribution_status": core["attribution_status"],
        "unique_biological_or_psychological_cause_claim_authorized": False,
        "m56_scoring_private_outcome_load_count": 1,
        "m57_diagnostic_private_outcome_load_count": 1,
        "complete_run_total_named_sanctioned_outcome_load_count": 2,
        "m57_model_call_count": 0,
        "retry_count": 0,
        "fallback_count": 0,
        # A real bridge result is necessary but not sufficient for M58.  The
        # frozen M57 rule must also identify one unambiguous eligible leader.
        "m58_planning_authorized": formal and core["leading_recoverable_stage"] is not None,
        "production_memory_write_authorized": False,
        "external_deployment_authorized": False,
        "claim_boundary": load_contract()["claim_boundary"],
    }
    value["result_hash"] = digest(value)
    return value


def validate_result(value: dict[str, Any], run_id: str, checkpoint: dict[str, Any], upstream: dict[str, Any]) -> dict[str, Any]:
    expected = build_result(run_id, checkpoint, upstream)
    errors = [] if value == expected else ["result.content_or_hash"]
    return {"valid": not errors, "errors": errors, "result_hash": value.get("result_hash")}


def build_result_commitment(result: dict[str, Any]) -> dict[str, Any]:
    value = {
        "schema": COMMITMENT_SCHEMA,
        "version": "1.0.0",
        "status": "m57_scoped_result_sha256_committed",
        "run_id": result["run_id"],
        "contract_hash": result["contract_hash"],
        "data_kind": result["data_kind"],
        "formal_result_created": result["formal_result_created"],
        "checkpoint_hash": result["checkpoint_hash"],
        "result_hash": result["result_hash"],
        "m57_diagnostic_private_outcome_load_count": 1,
        "m58_planning_authorized": result["m58_planning_authorized"],
        "production_memory_write_authorized": False,
        "external_deployment_authorized": False,
    }
    value["commitment_hash"] = digest(value)
    return value


def validate_result_commitment(value: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    expected = build_result_commitment(result)
    errors = [] if value == expected else ["commitment.content_or_hash"]
    return {"valid": not errors, "errors": errors, "commitment_hash": value.get("commitment_hash")}


def _finalize(
    run_id: str, mode: dict[str, Any], intent: dict[str, Any], checkpoint: dict[str, Any],
    upstream: dict[str, Any], *, outcome_load_this_invocation: int,
) -> dict[str, Any]:
    validation = validate_private_checkpoint(checkpoint, run_id, mode, intent, upstream)
    if not validation["valid"]:
        raise ValueError("invalid M57.3 checkpoint: " + "; ".join(validation["errors"]))
    result = build_result(run_id, checkpoint, upstream)
    result_write = _write_or_validate_identical(upstream["paths"]["m57_3_result"], result)
    commitment = build_result_commitment(result)
    commitment_write = _write_or_validate_identical(
        upstream["paths"]["m57_3_commitment"], commitment
    )
    return {
        "status": result["status"],
        "formal_result_created": result["formal_result_created"],
        "result_hash": result["result_hash"],
        "commitment_hash": commitment["commitment_hash"],
        "leading_recoverable_stage": result["leading_recoverable_stage"],
        "attribution_status": result["attribution_status"],
        "observed_label_count": result["observed_label_count"],
        "preoutcome_component_prediction_count": result["preoutcome_component_prediction_count"],
        "decision_ceiling_count": result["decision_ceiling_count"],
        "available_stage_substitution_count": result["available_stage_substitution_count"],
        "realization_stage_available": False,
        "m57_diagnostic_outcome_load_this_invocation": outcome_load_this_invocation,
        "m57_diagnostic_completed_run_outcome_load_count": 1,
        "complete_run_total_named_sanctioned_outcome_load_count": 2,
        "m57_model_call_count": 0,
        "m58_planning_authorized": result["m58_planning_authorized"],
        "result_write": result_write,
        "commitment_write": commitment_write,
    }


def _execute(run_id: str, *, allow_forged: bool) -> dict[str, Any]:
    contract = validate_contract()
    if not contract["valid"]:
        raise PermissionError("M57.3 contract invalid: " + "; ".join(contract["errors"]))
    single_writer_m56._validate_permitted_run(run_id)
    with single_writer_m56._exclusive_scoring_lock(single_writer_m56._lock_path(run_id)):
        upstream = _load_upstream(run_id, allow_forged=allow_forged)
        paths = upstream["paths"]
        mode = build_bridge_mode(run_id, upstream)
        if paths["m57_3_mode"].exists():
            existing_mode = load_json(paths["m57_3_mode"])
            if not validate_bridge_mode(existing_mode, run_id, upstream)["valid"]:
                raise ValueError("existing M57.3 mode differs")
            mode = existing_mode
        else:
            _write_or_validate_identical(paths["m57_3_mode"], mode)
        checkpoint_exists = paths["m57_3_checkpoint"].exists()
        intent_exists = paths["m57_3_intent"].exists()
        result_exists = paths["m57_3_result"].exists() or paths["m57_3_commitment"].exists()
        if result_exists and not checkpoint_exists:
            raise PermissionError("M57.3 result exists without a valid joined checkpoint")
        if checkpoint_exists and not intent_exists:
            raise PermissionError("M57.3 checkpoint exists without immutable intent")
        if paths["m57_3_failure"].exists():
            raise PermissionError("M57.3 outcome-join state is terminal; retry is forbidden")
        if intent_exists:
            intent = load_json(paths["m57_3_intent"])
            if not validate_join_intent(intent, run_id, mode)["valid"]:
                raise ValueError("existing M57.3 intent differs")
            if not checkpoint_exists:
                failure = build_terminal_failure(run_id, mode, intent)
                _write_or_validate_identical(paths["m57_3_failure"], failure)
                raise PermissionError(
                    "M57.3 intent exists without a valid durable checkpoint; outcome reload is forbidden"
                )
            checkpoint = load_json(paths["m57_3_checkpoint"])
            return _finalize(
                run_id, mode, intent, checkpoint, upstream,
                outcome_load_this_invocation=0,
            )
        intent = build_join_intent(run_id, mode)
        _write_or_validate_identical(paths["m57_3_intent"], intent)
        try:
            outcome_inputs = scorer_m56.load_outcome_inputs(run_id)
            rows = upstream["context"]["authorization"]["rows"]
            outcome_validation = scorer_m56.validate_outcome_inputs(
                outcome_inputs["outcome_key"], outcome_inputs["split_report"],
                rows["packet"], rows["request"],
            )
            if not outcome_validation["valid"]:
                raise ValueError(
                    "M57.3 private outcome invalid: "
                    + "; ".join(outcome_validation["errors"])
                )
            bundle = build_joined_bundle(
                upstream, outcome_inputs["outcome_key"], outcome_validation
            )
            joined = validate_joined_bundle(bundle, upstream)
            if not joined["valid"]:
                raise ValueError("M57.3 joined bundle invalid: " + "; ".join(joined["errors"]))
            checkpoint = build_private_checkpoint(
                run_id, mode, intent, upstream, bundle, joined, outcome_validation
            )
            _write_or_validate_identical(paths["m57_3_checkpoint"], checkpoint)
        except BaseException:
            if not paths["m57_3_checkpoint"].exists():
                try:
                    _write_or_validate_identical(
                        paths["m57_3_failure"], build_terminal_failure(run_id, mode, intent)
                    )
                except BaseException:
                    pass
            raise
        return _finalize(
            run_id, mode, intent, checkpoint, upstream,
            outcome_load_this_invocation=1,
        )


def execute_m57_sanctioned_outcome_analyzer_bridge(run_id: str) -> dict[str, Any]:
    """Execute the formal bridge; all labels and authority come from run artifacts."""
    return _execute(run_id, allow_forged=False)


def _validate_existing(run_id: str, *, allow_forged: bool) -> dict[str, Any]:
    upstream = _load_upstream(run_id, allow_forged=allow_forged)
    paths = upstream["paths"]
    required = (
        "m57_3_mode", "m57_3_intent", "m57_3_checkpoint",
        "m57_3_result", "m57_3_commitment",
    )
    missing = [name for name in required if not paths[name].exists()]
    if missing:
        return {"valid": False, "errors": [f"missing:{name}" for name in missing]}
    mode = load_json(paths["m57_3_mode"])
    intent = load_json(paths["m57_3_intent"])
    checkpoint = load_json(paths["m57_3_checkpoint"])
    result = load_json(paths["m57_3_result"])
    commitment = load_json(paths["m57_3_commitment"])
    errors = []
    errors.extend(f"mode:{name}" for name in validate_bridge_mode(mode, run_id, upstream)["errors"])
    errors.extend(f"intent:{name}" for name in validate_join_intent(intent, run_id, mode)["errors"])
    errors.extend(
        f"checkpoint:{name}"
        for name in validate_private_checkpoint(checkpoint, run_id, mode, intent, upstream)["errors"]
    )
    errors.extend(f"result:{name}" for name in validate_result(result, run_id, checkpoint, upstream)["errors"])
    errors.extend(f"commitment:{name}" for name in validate_result_commitment(commitment, result)["errors"])
    return {
        "status": "m57_3_sanctioned_bridge_validated" if not errors else "m57_3_sanctioned_bridge_invalid",
        "valid": not errors,
        "errors": errors,
        "data_kind": result.get("data_kind"),
        "formal_result_created": result.get("formal_result_created"),
        "result_hash": result.get("result_hash"),
        "commitment_hash": commitment.get("commitment_hash"),
        "observed_label_count": result.get("observed_label_count"),
        "decision_ceiling_count": result.get("decision_ceiling_count"),
        "m57_diagnostic_completed_run_outcome_load_count": 1,
        "additional_outcome_load_count": 0,
        "m58_planning_authorized": result.get("m58_planning_authorized"),
    }


def validate_m57_sanctioned_outcome_analyzer_bridge(run_id: str) -> dict[str, Any]:
    """Validate only a real formal bridge; engineering fixtures remain invalid."""
    try:
        return _validate_existing(run_id, allow_forged=False)
    except (FileNotFoundError, PermissionError, ValueError, json.JSONDecodeError) as exc:
        return {
            "status": "m57_3_sanctioned_bridge_invalid",
            "valid": False,
            "errors": [f"formal_validation:{type(exc).__name__}:{exc}"],
            "formal_result_created": False,
            "m58_planning_authorized": False,
        }


def build_engineering_rehearsal() -> dict[str, Any]:
    from test_m56_10_crash_safe_outcome_join import m5610_private_roots
    from test_m56_9_single_writer_formal_scoring import materialize_scoring_run

    with TemporaryDirectory(prefix="uruha-m57-3-bridge-") as temp:
        private_root = Path(temp)
        run_id = "m57-3-author-constructed-full-chain"
        loads = {"count": 0}
        with m5610_private_roots(private_root):
            run_root = materialize_scoring_run(private_root, run_id)
            commitment_m57.commit_m57_preoutcome_diagnostic_mode(run_id)
            context = component_m57._load_preoutcome_context(run_id)
            evidence = component_m57.build_forged_engineering_evidence_manifest(run_id, context)
            durable_m56._durable_atomic_write_json(
                run_root / "generation" / component_m57.EVIDENCE_FILENAME,
                evidence, exclusive=True,
            )
            with mock.patch.object(
                component_m57.runner_m56, "_ollama_generate",
                side_effect=component_m57._mock_ollama_call,
            ):
                component_m57._execute(run_id, allow_forged=True)
            original_loader = scorer_m56.load_outcome_inputs

            def counted_loader(value: str) -> dict[str, dict[str, Any]]:
                loads["count"] += 1
                return original_loader(value)

            with mock.patch.object(scorer_m56, "load_outcome_inputs", side_effect=counted_loader):
                m56 = crash_safe_m56.execute_crash_safe_outcome_join_formal_scoring(run_id)
                start = perf_counter()
                first = _execute(run_id, allow_forged=True)
                first_seconds = perf_counter() - start
                replay = _execute(run_id, allow_forged=True)
            validation = _validate_existing(run_id, allow_forged=True)
            result = load_json(_paths(run_id)["m57_3_result"])
            checkpoint = load_json(_paths(run_id)["m57_3_checkpoint"])
            artifact_bytes = {
                name: _paths(run_id)[name].stat().st_size
                for name in (
                    "m57_3_mode", "m57_3_intent", "m57_3_checkpoint",
                    "m57_3_result", "m57_3_commitment",
                )
            }
        value = {
            "schema": REHEARSAL_SCHEMA,
            "version": "1.0.0",
            "status": "author_constructed_full_chain_joined_and_analyzed_without_formal_authority",
            "run_id": run_id,
            "contract_hash": validate_contract()["contract_hash"],
            "fixture_kind": ENGINEERING_EVIDENCE_KIND,
            "m56_result_status": m56["status"],
            "m57_3_first_status": first["status"],
            "m57_3_replay_status": replay["status"],
            "m56_scoring_outcome_loader_calls": 1,
            "m57_diagnostic_outcome_loader_calls": loads["count"] - 1,
            "complete_run_total_named_sanctioned_outcome_loads": loads["count"],
            "replay_additional_outcome_loads": replay["m57_diagnostic_outcome_load_this_invocation"],
            "observed_label_count": result["observed_label_count"],
            "preoutcome_component_prediction_count": result["preoutcome_component_prediction_count"],
            "decision_ceiling_count": result["decision_ceiling_count"],
            "available_stage_substitution_count": result["available_stage_substitution_count"],
            "realization_stage_available": result["realization_stage_available"],
            "unchanged_analyzer_core_analysis_hash": checkpoint["core_analysis_hash"],
            "leading_recoverable_stage": result["leading_recoverable_stage"],
            "attribution_status": result["attribution_status"],
            "formal_result_created": result["formal_result_created"],
            "m58_planning_authorized": result["m58_planning_authorized"],
            "public_formal_validator_accepts_fixture": False,
            "internal_validation_valid": validation["valid"],
            "real_model_call_count": 0,
            "real_target_outcome_access_count": 0,
            "mocked_component_model_call_count": 90,
            "elapsed_seconds": first_seconds,
            "artifact_utf8_bytes": artifact_bytes,
            "claim_boundary": load_contract()["claim_boundary"],
        }
        value["rehearsal_hash"] = digest(value)
        return value


def validate_rehearsal(value: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if value.get("schema") != REHEARSAL_SCHEMA or value.get("status") != "author_constructed_full_chain_joined_and_analyzed_without_formal_authority":
        errors.append("rehearsal.schema_or_status")
    if value.get("rehearsal_hash") != digest({key: child for key, child in value.items() if key != "rehearsal_hash"}):
        errors.append("rehearsal.hash")
    if value.get("contract_hash") != validate_contract()["contract_hash"]:
        errors.append("rehearsal.contract")
    expected_counts = {
        "m56_scoring_outcome_loader_calls": 1,
        "m57_diagnostic_outcome_loader_calls": 1,
        "complete_run_total_named_sanctioned_outcome_loads": 2,
        "replay_additional_outcome_loads": 0,
        "observed_label_count": 30,
        "preoutcome_component_prediction_count": 90,
        "decision_ceiling_count": 30,
        "available_stage_substitution_count": 120,
        "mocked_component_model_call_count": 90,
        "real_model_call_count": 0,
        "real_target_outcome_access_count": 0,
    }
    for name, expected in expected_counts.items():
        if value.get(name) != expected:
            errors.append(f"rehearsal.{name}")
    if value.get("realization_stage_available") is not False:
        errors.append("rehearsal.realization")
    if value.get("formal_result_created") is not False or value.get("m58_planning_authorized") is not False:
        errors.append("rehearsal.authority")
    if value.get("public_formal_validator_accepts_fixture") is not False or value.get("internal_validation_valid") is not True:
        errors.append("rehearsal.validation_boundary")
    return {"valid": not errors, "errors": errors, "rehearsal_hash": value.get("rehearsal_hash")}


def build_live_audit() -> dict[str, Any]:
    upstream = component_m57.build_live_audit()
    value = {
        "schema": AUDIT_SCHEMA,
        "version": "1.0.0",
        "status": "m57_3_bridge_ready_but_live_human_chain_and_formal_result_absent",
        "contract_valid": validate_contract()["valid"],
        "contract_hash": validate_contract()["contract_hash"],
        "counts": deepcopy(upstream["counts"]),
        "live_m57_3_modes": 0,
        "live_m57_3_joined_checkpoints": 0,
        "formal_m57_outcome_access_authorized": False,
        "formal_m57_result_created": False,
        "target_outcome_access_count": 0,
        "formal_model_call_count": 0,
        "m58_authorized": False,
        "blocking_gates": deepcopy(upstream["blocking_gates"]),
        "claim_boundary": load_contract()["claim_boundary"],
    }
    value["audit_hash"] = digest(value)
    return value


def load_saved_rehearsal(path: str | Path = RESULT_PATH) -> dict[str, Any]:
    value = load_json(path)
    validation = validate_rehearsal(value)
    if not validation["valid"]:
        raise PermissionError("invalid saved M57.3 rehearsal: " + "; ".join(validation["errors"]))
    return value


def render_dashboard(
    rehearsal: dict[str, Any] | None = None, audit: dict[str, Any] | None = None,
) -> str:
    rehearsal = deepcopy(rehearsal or load_saved_rehearsal())
    audit = deepcopy(audit or build_live_audit())
    if not validate_rehearsal(rehearsal)["valid"]:
        raise PermissionError("invalid M57.3 rehearsal cannot be rendered")
    counts = audit["counts"]
    total_bytes = sum(rehearsal["artifact_utf8_bytes"].values())
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>M57.3 受控答案連接器</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#07131a;color:#f4fbff;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}main{{max-width:1180px;margin:auto;padding:28px}}section{{border:1px solid #335d70;border-radius:20px;background:#0d202a;padding:24px;margin-bottom:18px;overflow:hidden}}.hero{{background:linear-gradient(135deg,#123c48,#3d294b)}}h1{{font-size:clamp(30px,5vw,48px);margin:12px 0}}p{{color:#c9dce5;line-height:1.65}}.deny{{display:inline-block;background:#742b3a;color:#ffe4e9;padding:8px 12px;border-radius:999px;font-weight:850}}.flow{{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:9px;align-items:stretch}}.card{{min-width:0;border:1px solid #466b7e;border-radius:15px;background:#081922;padding:15px}}.card b,.card span{{display:block;overflow-wrap:anywhere}}.card b{{color:#83e6c7}}.card span{{color:#bdd4de;margin-top:7px;line-height:1.45}}.load{{border-color:#d09a52}}.private{{border-color:#ad6875}}.good{{border-color:#4cb68d}}.compare{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}.metric{{font-size:34px;font-weight:900;color:#7be3c1}}.boundary{{border-left:6px solid #dfaa55;background:#282115}}.bars{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}}.bar{{text-align:center}}.bar strong{{font-size:27px;color:#8be7c9}}@media(max-width:950px){{.flow,.bars{{grid-template-columns:repeat(2,1fr)}}}}@media(max-width:650px){{.flow,.bars,.compare{{grid-template-columns:1fr}}}}
</style></head><body><main><section class="hero"><span class="deny">FORMAL M57 DENIED · V7 {counts['v7_slots_by_ledger'][0]}/18 + {counts['v7_slots_by_ledger'][1]}/18</span><h1>M57.3 · 預測不能自己填答案</h1><p>答案前的 90 個元件預測，必須經過具名、可追蹤、不可重試的答案連接器，才可以進入既有診斷器。</p></section>
<section><h2>完整受控資料流</h2><div class="flow"><div class="card"><b>① M57.2</b><span>30 題 × 3 層預測先封存</span></div><div class="card good"><b>② M56 結果鏈</b><span>score report + commitment 完整驗證</span></div><div class="card load"><b>③ M57 診斷讀取</b><span>另一次明名授權；最多 1 次</span></div><div class="card private"><b>④ 私有 checkpoint</b><span>30 labels + 30 decision ceilings</span></div><div class="card"><b>⑤ 原 M57 analyzer</b><span>同一統計規則；不改 predictions</span></div><div class="card"><b>⑥ Aggregate</b><span>只輸出元件統計與證據邊界</span></div></div></section>
<section><h2>不是偷偷重開答案</h2><div class="compare"><div class="card"><b>M56 正式評分</b><div class="metric">1 次</div><p>原本就需要的一次 private outcome load，用來產生 B5 vs Ours 正式分數。</p></div><div class="card load"><b>M57 元件診斷</b><div class="metric">1 次</div><p>新的、獨立命名授權；intent 先落盤，成功 replay 額外讀取 = {rehearsal['replay_additional_outcome_loads']}。</p></div></div></section>
<section><h2>工程 rehearsal 實際形成的內容</h2><div class="bars"><div class="card bar"><strong>{rehearsal['observed_label_count']}</strong><span>observed labels</span></div><div class="card bar"><strong>{rehearsal['preoutcome_component_prediction_count']}</strong><span>答案前 predictions</span></div><div class="card bar"><strong>{rehearsal['decision_ceiling_count']}</strong><span>decision ceilings</span></div><div class="card bar"><strong>{rehearsal['available_stage_substitution_count']}</strong><span>可評分 stage rows</span></div><div class="card bar"><strong>0</strong><span>realization ratings</span></div></div><p>五個 durable artifacts 共 {total_bytes:,} bytes；join + analyzer {rehearsal['elapsed_seconds']:.3f}s。這是 author-constructed fixture，不是模型或真人資料表現。</p></section>
<section class="boundary"><h2>現在能證明與不能證明</h2><p>能證明：完整 result chain、答案來源、decision upper bound 與 unchanged analyzer 可以 fail-closed 串起來；forged fixture 仍不能通過 public formal validator。不能證明：哪個真實 Uruha 元件出錯、私人心理、Equation V1、全面勝 LLM。real temporal rows {counts['real_temporal_rows']}/30，formal result 0，M58 denied。</p></section></main></body></html>"""


def serve_demo(port: int) -> None:
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
    parser = argparse.ArgumentParser(description="M57.3 sanctioned outcome-to-analyzer bridge")
    parser.add_argument("--run-id")
    parser.add_argument("--validate-run")
    parser.add_argument("--rehearsal", action="store_true")
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--serve", type=int)
    args = parser.parse_args()
    if args.run_id:
        print(json.dumps(execute_m57_sanctioned_outcome_analyzer_bridge(args.run_id), ensure_ascii=False, indent=2))
    elif args.validate_run:
        print(json.dumps(validate_m57_sanctioned_outcome_analyzer_bridge(args.validate_run), ensure_ascii=False, indent=2))
    elif args.rehearsal:
        value = build_engineering_rehearsal()
        print(json.dumps(value, ensure_ascii=False, indent=2))
    elif args.audit:
        print(json.dumps(build_live_audit(), ensure_ascii=False, indent=2))
    elif args.serve:
        serve_demo(args.serve)
    else:
        parser.error("choose --run-id, --validate-run, --rehearsal, --audit, or --serve")


if __name__ == "__main__":
    main()
