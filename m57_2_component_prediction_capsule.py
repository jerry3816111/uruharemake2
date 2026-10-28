#!/usr/bin/env python3
"""M57.2 source-bound pre-outcome component prediction capsule.

The public execution path accepts only a run ID. It requires an already durable
M57.1 mode plus a separately prepared 30-row evidence manifest, commits the
schedule before model calls, never opens the scoring compartment, and never
accepts caller-supplied providers, outcomes, readiness or retry controls.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import inspect
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from typing import Any
from unittest import mock

import m56_3_lease_gated_generation_runner as runner_m56
import m56_7_mac_full_sync_generation as durable_m56
import m56_9_single_writer_formal_scoring as single_writer_m56
import m56_10_crash_safe_outcome_join as crash_safe_m56
import m56_blinded_execution_capsule as capsule_m56
import m57_1_preoutcome_diagnostic_commitment as commitment_m57
import m57_component_error_localization as localization_m57


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/m57_2_component_prediction_capsule_v1.json"
RESULT_PATH = ROOT / "analysis/m57_2_component_prediction_capsule_rehearsal_2026-09-04.json"

EVIDENCE_FILENAME = "m57_2_component_evidence_manifest.json"
SCHEDULE_FILENAME = "m57_2_component_prediction_schedule.json"
CAPSULE_FILENAME = "m57_2_component_prediction_capsule.json"
COMMITMENT_FILENAME = "m57_2_component_prediction_commitment.json"
CALL_LEDGER_FILENAME = "m57_2_component_call_ledger.json"
FAILURE_FILENAME = "m57_2_terminal_component_generation_failure.json"

EVIDENCE_SCHEMA = "uruha_m57_component_evidence_manifest_v1"
SCHEDULE_SCHEMA = "uruha_m57_preoutcome_component_schedule_v1"
CAPSULE_SCHEMA = "uruha_m57_preoutcome_component_prediction_capsule_v1"
COMMITMENT_SCHEMA = "uruha_m57_preoutcome_component_prediction_commitment_v1"
CALL_LEDGER_SCHEMA = "uruha_m57_component_call_ledger_v1"
FAILURE_SCHEMA = "uruha_m57_terminal_component_generation_failure_v1"
REHEARSAL_SCHEMA = "uruha_m57_2_component_prediction_capsule_rehearsal_v1"
AUDIT_SCHEMA = "uruha_m57_2_component_prediction_capsule_live_audit_v1"

PREOUTCOME_STAGES = ("perception", "retrieval", "state")
POST_OR_SURFACE_STAGES = ("decision", "realization")
STAGE_IDS = localization_m57.STAGE_IDS
PRIVATE_STATE_IDS = {"transient_state", "relationship_state", "goal_need_state"}
OBSERVABLE_STATE_IDS = {
    "current_observable_input", "observable_history", "structured_memory",
    "observable_context", "person_parameter", "uncertainty_calibration",
}
FORBIDDEN_KEYS = set(capsule_m56.OUTCOME_KEYS) | {
    "target_outcome", "target_behavior", "private_outcome_key",
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


def _find_keys(value: Any, forbidden: set[str] = FORBIDDEN_KEYS, prefix: str = "") -> list[str]:
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
    expected_fields = {
        "schema", "version", "status", "single_changed_variable", "public_api",
        "frozen_dependencies", "evidence", "generation", "state_machine",
        "durability", "current_authorization", "claim_boundary",
    }
    if set(contract) != expected_fields:
        errors.append("contract.fields")
    if contract.get("schema") != "uruha_m57_preoutcome_component_prediction_capsule_contract_v1":
        errors.append("contract.schema")
    if contract.get("version") != "1.0.0":
        errors.append("contract.version")
    if contract.get("status") != "prospective_frozen_before_implementation_and_any_real_m56_target_outcome_access":
        errors.append("contract.status")
    api = contract.get("public_api") or {}
    if api.get("execute_function") != "execute_m57_preoutcome_component_predictions":
        errors.append("api.execute")
    if api.get("validate_function") != "validate_m57_preoutcome_component_predictions":
        errors.append("api.validate")
    if api.get("parameters") != ["run_id"]:
        errors.append("api.parameters")
    if api.get("evidence_provider_outcome_readiness_authorization_retry_or_resource_injection_allowed") is not False:
        errors.append("api.injection")
    if list(inspect.signature(execute_m57_preoutcome_component_predictions).parameters) != ["run_id"]:
        errors.append("api.execute_signature")
    if list(inspect.signature(validate_m57_preoutcome_component_predictions).parameters) != ["run_id"]:
        errors.append("api.validate_signature")
    dependencies = contract.get("frozen_dependencies") or {}
    if len(dependencies) != 6:
        errors.append("dependencies.count")
    for relative, expected_hash in dependencies.items():
        path = ROOT / relative
        if not path.is_file() or sha256_file(path) != expected_hash:
            errors.append(f"dependency:{relative}")
    evidence = contract.get("evidence") or {}
    if evidence.get("sample_count") != 30:
        errors.append("evidence.sample_count")
    if tuple(evidence.get("stage_order") or ()) != STAGE_IDS:
        errors.append("evidence.stage_order")
    if tuple(evidence.get("preoutcome_prediction_stages") or ()) != PREOUTCOME_STAGES:
        errors.append("evidence.preoutcome_stages")
    required_evidence_true = (
        "state_stage_requires_source_bound_observable_proxy",
        "outcome_named_keys_forbidden",
    )
    if any(evidence.get(name) is not True for name in required_evidence_true):
        errors.append("evidence.required")
    required_evidence_false = (
        "private_state_annotation_allowed", "post_cutoff_history_id_allowed",
        "decision_preoutcome_availability_allowed",
        "realization_without_independent_blind_human_ratings_available",
        "author_constructed_evidence_formal_authority",
    )
    if any(evidence.get(name) is not False for name in required_evidence_false):
        errors.append("evidence.boundary")
    generation = contract.get("generation") or {}
    if generation.get("provider") != "local_ollama" or generation.get("model") != "qwen3.5:9b":
        errors.append("generation.identity")
    if generation.get("maximum_model_call_count") != 90:
        errors.append("generation.call_count")
    if generation.get("transport_attempts_per_call") != 1:
        errors.append("generation.transport")
    if generation.get("retry_count") != 0 or generation.get("fallback_count") != 0:
        errors.append("generation.retry")
    if generation.get("target_outcome_access_before_commitment") != 0:
        errors.append("generation.outcome")
    for name in (
        "same_ours_manifest_provider_options_required", "same_ours_input_token_budget_required",
        "same_ours_output_token_budget_required", "strict_json_distribution_only",
    ):
        if generation.get(name) is not True:
            errors.append(f"generation.{name}")
    if generation.get("raw_model_response_persisted") is not False or generation.get("hidden_reasoning_requested_or_persisted") is not False:
        errors.append("generation.output_boundary")
    expected_states = [
        "m57_1_mode_validated", "evidence_manifest_validated",
        "component_schedule_committed", "all_available_component_predictions_complete",
        "resource_ledger_complete", "prediction_capsule_committed",
        "prediction_hash_commitment_committed",
    ]
    if contract.get("state_machine") != expected_states:
        errors.append("state_machine")
    durability = contract.get("durability") or {}
    if not durability or any(value is not True for name, value in durability.items() if name != "same_run_retry_after_attempt_allowed"):
        errors.append("durability.required")
    if durability.get("same_run_retry_after_attempt_allowed") is not False:
        errors.append("durability.retry")
    authorization = contract.get("current_authorization") or {}
    if not authorization or any(value is not False for value in authorization.values()):
        errors.append("authorization")
    return {
        "valid": not errors,
        "errors": errors,
        "contract_hash": digest(contract),
        "binding_count": len(dependencies),
    }


def _paths(run_id: str) -> dict[str, Path]:
    paths = commitment_m57._paths(run_id)
    return {
        **paths,
        "evidence": paths["generation"] / EVIDENCE_FILENAME,
        "m57_2_schedule": paths["generation"] / SCHEDULE_FILENAME,
        "m57_2_capsule": paths["generation"] / CAPSULE_FILENAME,
        "m57_2_commitment": paths["commitments"] / COMMITMENT_FILENAME,
        "m57_2_ledger": paths["telemetry"] / CALL_LEDGER_FILENAME,
        "m57_2_failure": paths["telemetry"] / FAILURE_FILENAME,
    }


def _load_preoutcome_context(run_id: str) -> dict[str, Any]:
    authorization = commitment_m57._load_authorization(run_id)
    paths = _paths(run_id)
    if not paths["m57_1_mode"].exists():
        raise PermissionError("M57.2 requires an existing M57.1 pre-outcome mode")
    mode = load_json(paths["m57_1_mode"])
    mode_validation = commitment_m57.validate_mode_value(mode, run_id, authorization)
    if not mode_validation["valid"]:
        raise ValueError("M57.1 mode is invalid")
    return {
        "authorization": authorization,
        "rows": authorization["rows"],
        "mode": mode,
        "paths": paths,
    }


def _ours_task_map(rows: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        task["sample_id"]: task
        for task in rows["capsule"]["prediction_tasks"]
        if task["condition_id"] == capsule_m56.PRIMARY_SYSTEM
    }


def _ours_prediction_map(rows: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        row["sample_id"]: row
        for row in rows["submission"]["prediction_rows"]
        if row["condition_id"] == capsule_m56.PRIMARY_SYSTEM
    }


def _artifact_map(rows: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["sample_id"]: row for row in rows["bundle"]["sample_artifacts"]}


def _sample_order(rows: dict[str, Any]) -> list[str]:
    return [row["sample_id"] for row in rows["packet"]["model_inputs"]]


def _validate_contribution(
    value: Any, *, source_hash: str, scope: str,
) -> list[str]:
    errors: list[str] = []
    fields = {
        "contributor_id", "contributor_role", "contribution_id",
        "source_information_hash", "payload", "created_before_outcome",
        "contribution_hash",
    }
    if not isinstance(value, dict) or set(value) != fields:
        return [f"{scope}.fields"]
    unhashed = {key: child for key, child in value.items() if key != "contribution_hash"}
    if value.get("contribution_hash") != digest(unhashed):
        errors.append(f"{scope}.hash")
    for name in ("contributor_id", "contributor_role", "contribution_id"):
        if not isinstance(value.get(name), str) or not value[name]:
            errors.append(f"{scope}.{name}")
    if value.get("source_information_hash") != source_hash:
        errors.append(f"{scope}.source")
    if not isinstance(value.get("payload"), dict):
        errors.append(f"{scope}.payload")
    if value.get("created_before_outcome") is not True:
        errors.append(f"{scope}.timing")
    return errors


def _validate_resolved_payload(
    stage_id: str, payload: Any, source: dict[str, Any], scope: str,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return [f"{scope}.object"]
    if stage_id == "perception":
        if set(payload) != {"observable_features", "representation_note"}:
            errors.append(f"{scope}.fields")
        features = payload.get("observable_features")
        if not isinstance(features, list) or not features or any(not isinstance(item, str) or not item for item in features):
            errors.append(f"{scope}.features")
        if not isinstance(payload.get("representation_note"), str) or not payload.get("representation_note"):
            errors.append(f"{scope}.note")
    elif stage_id == "retrieval":
        if set(payload) != {"selected_history_ids", "selection_rule"}:
            errors.append(f"{scope}.fields")
        selected = payload.get("selected_history_ids")
        allowed = [row["history_id"] for row in source["all_pre_cutoff_history"]]
        if not isinstance(selected, list) or len(selected) != len(set(selected or [])):
            errors.append(f"{scope}.ids")
        elif set(selected) - set(allowed):
            errors.append(f"{scope}.post_cutoff_or_unknown_id")
        if not isinstance(payload.get("selection_rule"), str) or not payload.get("selection_rule"):
            errors.append(f"{scope}.rule")
    elif stage_id == "state":
        if set(payload) != {"observable_proxy_variables", "source_refs"}:
            errors.append(f"{scope}.fields")
        variables = payload.get("observable_proxy_variables")
        if not isinstance(variables, dict) or not variables:
            errors.append(f"{scope}.variables")
        elif set(variables) - OBSERVABLE_STATE_IDS or set(variables) & PRIVATE_STATE_IDS:
            errors.append(f"{scope}.private_or_unknown_variable")
        refs = payload.get("source_refs")
        allowed_refs = {
            "source_information.current_pre_cutoff_event",
            "source_information.prediction_time",
            "source_information.participants",
            *{f"history:{row['history_id']}" for row in source["all_pre_cutoff_history"]},
        }
        if not isinstance(refs, list) or not refs or len(refs) != len(set(refs or [])):
            errors.append(f"{scope}.source_refs")
        elif set(refs) - allowed_refs:
            errors.append(f"{scope}.unknown_source_ref")
    else:
        errors.append(f"{scope}.stage")
    forbidden = _find_keys(payload)
    errors.extend(f"{scope}.forbidden:{name}" for name in forbidden)
    return errors


def _validate_stage_evidence(
    value: Any, *, stage_id: str, source_hash: str,
    source: dict[str, Any], scope: str,
) -> list[str]:
    fields = {
        "stage_id", "availability", "oracle_kind", "source_information_hash",
        "evidence_timing", "contributions", "adjudication", "resolved_payload",
        "unavailable_reason", "private_mental_truth_claimed", "evidence_hash",
    }
    if not isinstance(value, dict) or set(value) != fields:
        return [f"{scope}.fields"]
    errors: list[str] = []
    unhashed = {key: child for key, child in value.items() if key != "evidence_hash"}
    if value.get("evidence_hash") != digest(unhashed):
        errors.append(f"{scope}.hash")
    frozen = next(stage for stage in localization_m57.load_contract()["stages"] if stage["id"] == stage_id)
    if value.get("stage_id") != stage_id or value.get("oracle_kind") != frozen["oracle_kind"]:
        errors.append(f"{scope}.identity")
    if value.get("source_information_hash") != source_hash:
        errors.append(f"{scope}.source")
    if value.get("private_mental_truth_claimed") is not False:
        errors.append(f"{scope}.private_truth")
    availability = value.get("availability")
    if stage_id in POST_OR_SURFACE_STAGES and availability != "unavailable":
        errors.append(f"{scope}.preoutcome_availability")
    if availability == "unavailable":
        if value.get("contributions") != [] or value.get("adjudication") is not None or value.get("resolved_payload") is not None:
            errors.append(f"{scope}.unavailable_payload")
        if not isinstance(value.get("unavailable_reason"), str) or not value.get("unavailable_reason"):
            errors.append(f"{scope}.unavailable_reason")
        expected_timing = "post_outcome_only" if stage_id == "decision" else (
            "independent_human_surface_ratings_required" if stage_id == "realization" else "preoutcome_missing"
        )
        if value.get("evidence_timing") != expected_timing:
            errors.append(f"{scope}.unavailable_timing")
        return errors
    if availability != "available" or stage_id not in PREOUTCOME_STAGES:
        return errors + [f"{scope}.availability"]
    if value.get("evidence_timing") != "preoutcome_committed":
        errors.append(f"{scope}.timing")
    if value.get("unavailable_reason") is not None:
        errors.append(f"{scope}.available_reason")
    contributions = value.get("contributions")
    if not isinstance(contributions, list):
        return errors + [f"{scope}.contributions"]
    for index, contribution in enumerate(contributions):
        errors.extend(_validate_contribution(contribution, source_hash=source_hash, scope=f"{scope}.contribution[{index}]"))
    resolved = value.get("resolved_payload")
    errors.extend(_validate_resolved_payload(stage_id, resolved, source, f"{scope}.resolved"))
    if stage_id in {"perception", "retrieval"}:
        ids = [row.get("contributor_id") for row in contributions if isinstance(row, dict)]
        roles = [row.get("contributor_role") for row in contributions if isinstance(row, dict)]
        contribution_ids = [row.get("contribution_id") for row in contributions if isinstance(row, dict)]
        if (
            len(contributions) != 2
            or len(set(ids)) != 2
            or len(set(contribution_ids)) != 2
            or roles != ["independent_coder", "independent_coder"]
        ):
            errors.append(f"{scope}.independence")
        adjudication = value.get("adjudication")
        adj_fields = {
            "adjudicator_id", "selected_contribution_ids", "replacement_payload",
            "created_before_outcome", "adjudication_hash",
        }
        if not isinstance(adjudication, dict) or set(adjudication) != adj_fields:
            errors.append(f"{scope}.adjudication.fields")
        else:
            unhashed_adj = {key: child for key, child in adjudication.items() if key != "adjudication_hash"}
            if adjudication.get("adjudication_hash") != digest(unhashed_adj):
                errors.append(f"{scope}.adjudication.hash")
            if adjudication.get("adjudicator_id") in ids or not adjudication.get("adjudicator_id"):
                errors.append(f"{scope}.adjudication.independence")
            if set(adjudication.get("selected_contribution_ids") or []) != set(contribution_ids):
                errors.append(f"{scope}.adjudication.inputs")
            if adjudication.get("replacement_payload") != resolved:
                errors.append(f"{scope}.adjudication.payload")
            if adjudication.get("created_before_outcome") is not True:
                errors.append(f"{scope}.adjudication.timing")
    else:
        if len(contributions) != 1 or (contributions[0] if contributions else {}).get("contributor_role") != "observable_proxy_builder":
            errors.append(f"{scope}.proxy_builder")
        if value.get("adjudication") is not None:
            errors.append(f"{scope}.proxy_adjudication")
        if contributions and contributions[0].get("payload") != resolved:
            errors.append(f"{scope}.proxy_payload")
    return errors


def validate_evidence_manifest(
    manifest: dict[str, Any], run_id: str, context: dict[str, Any], *, allow_forged: bool = False,
) -> dict[str, Any]:
    errors: list[str] = []
    fields = {
        "schema", "version", "status", "data_kind", "run_id", "dataset_hash",
        "prediction_packet_hash", "m57_1_mode_commitment_hash", "sample_count",
        "stage_order", "rows", "evidence_created_before_outcome",
        "private_state_fact_created", "post_cutoff_evidence_used",
        "formal_authorization", "manifest_hash",
    }
    if not isinstance(manifest, dict) or set(manifest) != fields:
        return {"valid": False, "errors": ["manifest.fields"]}
    unhashed = {key: child for key, child in manifest.items() if key != "manifest_hash"}
    if manifest.get("manifest_hash") != digest(unhashed):
        errors.append("manifest.hash")
    if manifest.get("schema") != EVIDENCE_SCHEMA or manifest.get("version") != "1.0.0":
        errors.append("manifest.schema")
    if manifest.get("status") != "all_component_evidence_resolved_or_unavailable_before_outcome":
        errors.append("manifest.status")
    kind = manifest.get("data_kind")
    if kind not in {"real_independent_preoutcome_component_evidence", "author_constructed_engineering_only"}:
        errors.append("manifest.data_kind")
    if kind == "real_independent_preoutcome_component_evidence":
        if manifest.get("formal_authorization") is not True:
            errors.append("manifest.real_authorization")
    else:
        if manifest.get("formal_authorization") is not False:
            errors.append("manifest.forged_authorization")
        if not allow_forged:
            errors.append("manifest.author_constructed_not_formal")
    rows = context["rows"]
    mode = context["mode"]
    bindings = {
        "run_id": run_id,
        "dataset_hash": mode["dataset_hash"],
        "prediction_packet_hash": mode["prediction_packet_hash"],
        "m57_1_mode_commitment_hash": mode["mode_commitment_hash"],
    }
    for name, expected in bindings.items():
        if manifest.get(name) != expected:
            errors.append(f"manifest.{name}")
    if manifest.get("sample_count") != 30 or manifest.get("sample_count") != mode["sample_count"]:
        errors.append("manifest.sample_count")
    if tuple(manifest.get("stage_order") or ()) != STAGE_IDS:
        errors.append("manifest.stage_order")
    if manifest.get("evidence_created_before_outcome") is not True:
        errors.append("manifest.timing")
    if manifest.get("private_state_fact_created") is not False or manifest.get("post_cutoff_evidence_used") is not False:
        errors.append("manifest.boundary")
    forbidden = _find_keys(manifest)
    errors.extend(f"manifest.forbidden:{name}" for name in forbidden)
    task_map = _ours_task_map(rows)
    expected_order = _sample_order(rows)
    manifest_rows = manifest.get("rows")
    if not isinstance(manifest_rows, list) or len(manifest_rows) != 30:
        errors.append("rows.count")
        manifest_rows = []
    if [row.get("sample_id") for row in manifest_rows if isinstance(row, dict)] != expected_order:
        errors.append("rows.order")
    for index, row in enumerate(manifest_rows):
        scope = f"row[{index}]"
        if not isinstance(row, dict) or set(row) != {"sample_id", "source_information_hash", "stage_evidence", "row_hash"}:
            errors.append(f"{scope}.fields")
            continue
        unhashed_row = {key: child for key, child in row.items() if key != "row_hash"}
        if row.get("row_hash") != digest(unhashed_row):
            errors.append(f"{scope}.hash")
        sample_id = row.get("sample_id")
        task = task_map.get(sample_id)
        if task is None:
            errors.append(f"{scope}.sample")
            continue
        source = task["view"]["source_information"]
        source_hash = task["view"]["source_information_hash"]
        if row.get("source_information_hash") != source_hash:
            errors.append(f"{scope}.source")
        stage_evidence = row.get("stage_evidence")
        if not isinstance(stage_evidence, dict) or tuple(stage_evidence) != STAGE_IDS:
            errors.append(f"{scope}.stages")
            continue
        for stage_id in STAGE_IDS:
            errors.extend(_validate_stage_evidence(
                stage_evidence[stage_id], stage_id=stage_id,
                source_hash=source_hash, source=source, scope=f"{scope}.{stage_id}",
            ))
    return {
        "valid": not errors,
        "errors": errors,
        "manifest_hash": manifest.get("manifest_hash"),
        "available_prediction_count": sum(
            int(((row.get("stage_evidence") or {}).get(stage_id) or {}).get("availability") == "available")
            for row in manifest_rows if isinstance(row, dict) for stage_id in PREOUTCOME_STAGES
        ),
    }


def _contribution(
    contributor_id: str, role: str, contribution_id: str,
    source_hash: str, payload: dict[str, Any],
) -> dict[str, Any]:
    value = {
        "contributor_id": contributor_id,
        "contributor_role": role,
        "contribution_id": contribution_id,
        "source_information_hash": source_hash,
        "payload": deepcopy(payload),
        "created_before_outcome": True,
    }
    value["contribution_hash"] = digest(value)
    return value


def _available_stage(
    stage_id: str, source_hash: str, payload: dict[str, Any],
    contributions: list[dict[str, Any]], adjudication: dict[str, Any] | None,
) -> dict[str, Any]:
    frozen = next(stage for stage in localization_m57.load_contract()["stages"] if stage["id"] == stage_id)
    value = {
        "stage_id": stage_id,
        "availability": "available",
        "oracle_kind": frozen["oracle_kind"],
        "source_information_hash": source_hash,
        "evidence_timing": "preoutcome_committed",
        "contributions": deepcopy(contributions),
        "adjudication": deepcopy(adjudication),
        "resolved_payload": deepcopy(payload),
        "unavailable_reason": None,
        "private_mental_truth_claimed": False,
    }
    value["evidence_hash"] = digest(value)
    return value


def _unavailable_stage(stage_id: str, source_hash: str, reason: str) -> dict[str, Any]:
    frozen = next(stage for stage in localization_m57.load_contract()["stages"] if stage["id"] == stage_id)
    timing = "post_outcome_only" if stage_id == "decision" else (
        "independent_human_surface_ratings_required" if stage_id == "realization" else "preoutcome_missing"
    )
    value = {
        "stage_id": stage_id,
        "availability": "unavailable",
        "oracle_kind": frozen["oracle_kind"],
        "source_information_hash": source_hash,
        "evidence_timing": timing,
        "contributions": [],
        "adjudication": None,
        "resolved_payload": None,
        "unavailable_reason": reason,
        "private_mental_truth_claimed": False,
    }
    value["evidence_hash"] = digest(value)
    return value


def build_forged_engineering_evidence_manifest(run_id: str, context: dict[str, Any]) -> dict[str, Any]:
    """Build author-constructed evidence for isolated mechanics only."""

    rows = context["rows"]
    task_map = _ours_task_map(rows)
    artifact_map = _artifact_map(rows)
    manifest_rows: list[dict[str, Any]] = []
    for index, sample_id in enumerate(_sample_order(rows)):
        task = task_map[sample_id]
        source = task["view"]["source_information"]
        source_hash = task["view"]["source_information_hash"]
        perception_payload = {
            "observable_features": [
                f"text_character_count:{len(source['current_pre_cutoff_event'])}",
                "input_modality:text_paraphrase",
            ],
            "representation_note": "Author-constructed observable-only mechanics fixture.",
        }
        pc = [
            _contribution(f"forged-coder-{side}", "independent_coder", f"p-{index:02d}-{side}", source_hash, perception_payload)
            for side in ("a", "b")
        ]
        pa = {
            "adjudicator_id": "forged-adjudicator",
            "selected_contribution_ids": [row["contribution_id"] for row in pc],
            "replacement_payload": deepcopy(perception_payload),
            "created_before_outcome": True,
        }
        pa["adjudication_hash"] = digest(pa)
        history_ids = [row["history_id"] for row in source["all_pre_cutoff_history"]]
        retrieval_payload = {
            "selected_history_ids": history_ids[-4:],
            "selection_rule": "Author-constructed last-four visible histories for mechanics only.",
        }
        rc = [
            _contribution(f"forged-coder-{side}", "independent_coder", f"r-{index:02d}-{side}", source_hash, retrieval_payload)
            for side in ("a", "b")
        ]
        ra = {
            "adjudicator_id": "forged-adjudicator",
            "selected_contribution_ids": [row["contribution_id"] for row in rc],
            "replacement_payload": deepcopy(retrieval_payload),
            "created_before_outcome": True,
        }
        ra["adjudication_hash"] = digest(ra)
        state_variables = {
            row["id"]: deepcopy(row["value"])
            for row in artifact_map[sample_id]["state_snapshot"]["variables"]
            if row["id"] in OBSERVABLE_STATE_IDS
        }
        state_payload = {
            "observable_proxy_variables": state_variables,
            "source_refs": ["source_information.current_pre_cutoff_event"],
        }
        if history_ids:
            state_payload["source_refs"].append(f"history:{history_ids[-1]}")
        sc = [_contribution(
            "forged-observable-proxy-builder", "observable_proxy_builder",
            f"s-{index:02d}", source_hash, state_payload,
        )]
        stages = {
            "perception": _available_stage("perception", source_hash, perception_payload, pc, pa),
            "retrieval": _available_stage("retrieval", source_hash, retrieval_payload, rc, ra),
            "state": _available_stage("state", source_hash, state_payload, sc, None),
            "decision": _unavailable_stage("decision", source_hash, "withheld behavior is post-outcome only"),
            "realization": _unavailable_stage("realization", source_hash, "independent blind human surface ratings are absent"),
        }
        row = {
            "sample_id": sample_id,
            "source_information_hash": source_hash,
            "stage_evidence": stages,
        }
        row["row_hash"] = digest(row)
        manifest_rows.append(row)
    mode = context["mode"]
    value = {
        "schema": EVIDENCE_SCHEMA,
        "version": "1.0.0",
        "status": "all_component_evidence_resolved_or_unavailable_before_outcome",
        "data_kind": "author_constructed_engineering_only",
        "run_id": run_id,
        "dataset_hash": mode["dataset_hash"],
        "prediction_packet_hash": mode["prediction_packet_hash"],
        "m57_1_mode_commitment_hash": mode["mode_commitment_hash"],
        "sample_count": 30,
        "stage_order": list(STAGE_IDS),
        "rows": manifest_rows,
        "evidence_created_before_outcome": True,
        "private_state_fact_created": False,
        "post_cutoff_evidence_used": False,
        "formal_authorization": False,
    }
    value["manifest_hash"] = digest(value)
    validation = validate_evidence_manifest(value, run_id, context, allow_forged=True)
    if not validation["valid"]:
        raise AssertionError("forged evidence manifest invalid: " + "; ".join(validation["errors"]))
    return value


def _intervention_view(
    task: dict[str, Any], artifact: dict[str, Any], stage: dict[str, Any],
) -> dict[str, Any]:
    stage_id = stage["stage_id"]
    source = deepcopy(task["view"]["source_information"])
    replacement = deepcopy(stage["resolved_payload"])
    if stage_id == "perception":
        source.pop("current_pre_cutoff_event", None)
        downstream = {
            "source_information_without_replaced_input": source,
            "unchanged_fit_artifact": deepcopy(artifact["fit_artifact"]),
            "replacement_observable_input_representation": replacement,
            "removed_for_downstream_recomputation": ["state_snapshot", "transition_trace", "decision"],
        }
    elif stage_id == "retrieval":
        selected = set(replacement["selected_history_ids"])
        source["all_pre_cutoff_history"] = [
            row for row in source["all_pre_cutoff_history"] if row["history_id"] in selected
        ]
        downstream = {
            "source_information_with_substituted_history": source,
            "replacement_retrieval_annotation": replacement,
            "removed_for_downstream_recomputation": ["fit_artifact", "state_snapshot", "transition_trace", "decision"],
        }
    elif stage_id == "state":
        downstream = {
            "unchanged_source_information": source,
            "unchanged_fit_artifact": deepcopy(artifact["fit_artifact"]),
            "replacement_observable_state_proxy": replacement,
            "removed_for_downstream_recomputation": ["state_snapshot", "transition_trace", "decision"],
        }
    else:
        raise ValueError("only pre-outcome stages can build an intervention view")
    return {
        "sample_id": task["sample_id"],
        "candidate_behavior_labels": deepcopy(task["view"]["candidate_behavior_labels"]),
        "original_source_information_hash": task["view"]["source_information_hash"],
        "single_changed_component": stage_id,
        "component_evidence_hash": stage["evidence_hash"],
        "downstream_recomputation": downstream,
        "future_outcome_used": False,
        "private_mental_truth_claimed": False,
    }


def build_component_prompt(
    task: dict[str, Any], artifact: dict[str, Any], stage: dict[str, Any],
) -> dict[str, Any]:
    view = _intervention_view(task, artifact, stage)
    labels = task["view"]["candidate_behavior_labels"]
    payload = {
        "instruction": (
            "Predict the next observable behavior category after replacing exactly the named component. "
            "Treat the replacement as authoritative, ignore the removed original and downstream artifacts, "
            "and recompute all listed downstream stages. Use no future event or private mental fact. "
            "Return JSON only; probabilities must cover every label and sum to 1."
        ),
        "intervention_view": view,
        "output_schema": {
            "probabilities": {label: "number" for label in labels},
            "brief_evidence": "string_max_500",
        },
    }
    prompt = canonical(payload)
    return {
        "prompt": prompt,
        "prompt_hash": sha256(prompt.encode("utf-8")).hexdigest(),
        "intervention_view_hash": digest(view),
    }


def _component_output_schema(labels: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["probabilities", "brief_evidence"],
        "properties": {
            "probabilities": {
                "type": "object",
                "additionalProperties": False,
                "required": labels,
                "properties": {label: {"type": "number", "minimum": 0, "maximum": 1} for label in labels},
            },
            "brief_evidence": {"type": "string", "maxLength": 500},
        },
    }


def _validate_distribution(value: Any, labels: list[str]) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict) or list(value) != labels:
        return ["distribution.labels_or_order"]
    numbers = list(value.values())
    if any(type(number) not in (int, float) or not math.isfinite(float(number)) for number in numbers):
        errors.append("distribution.finite")
    elif any(float(number) < 0 or float(number) > 1 for number in numbers):
        errors.append("distribution.range")
    elif abs(sum(float(number) for number in numbers) - 1.0) > 0.000001:
        errors.append("distribution.sum")
    return errors


def _validate_component_output(parsed: Any, labels: list[str]) -> tuple[dict[str, float], str]:
    if not isinstance(parsed, dict) or set(parsed) != {"probabilities", "brief_evidence"}:
        raise ValueError("component prediction output fields invalid")
    distribution_errors = _validate_distribution(parsed["probabilities"], labels)
    if distribution_errors:
        raise ValueError("component prediction distribution invalid: " + "; ".join(distribution_errors))
    brief = parsed["brief_evidence"]
    if not isinstance(brief, str) or len(brief) > 500:
        raise ValueError("component prediction evidence invalid")
    return {label: float(parsed["probabilities"][label]) for label in labels}, brief


def build_schedule(
    run_id: str, context: dict[str, Any], manifest: dict[str, Any],
) -> dict[str, Any]:
    evidence_validation = validate_evidence_manifest(manifest, run_id, context, allow_forged=True)
    if not evidence_validation["valid"]:
        raise ValueError("evidence manifest invalid: " + "; ".join(evidence_validation["errors"]))
    rows = context["rows"]
    task_map = _ours_task_map(rows)
    prediction_map = _ours_prediction_map(rows)
    artifacts = _artifact_map(rows)
    evidence_map = {row["sample_id"]: row for row in manifest["rows"]}
    steps: list[dict[str, Any]] = []
    for sample_id in _sample_order(rows):
        for stage_id in STAGE_IDS:
            evidence = evidence_map[sample_id]["stage_evidence"][stage_id]
            available = stage_id in PREOUTCOME_STAGES and evidence["availability"] == "available"
            prompt = build_component_prompt(task_map[sample_id], artifacts[sample_id], evidence) if available else None
            steps.append({
                "step_index": len(steps),
                "step_id": f"m57-2::{sample_id}::{stage_id}",
                "sample_id": sample_id,
                "stage_id": stage_id,
                "source_information_hash": task_map[sample_id]["view"]["source_information_hash"],
                "evidence_hash": evidence["evidence_hash"],
                "original_output_hash": digest(prediction_map[sample_id]["probabilities"]),
                "availability": "available" if available else "unavailable",
                "model_call_required": available,
                "prompt_hash": prompt["prompt_hash"] if prompt else None,
                "intervention_view_hash": prompt["intervention_view_hash"] if prompt else None,
                "future_outcome_used": False,
            })
    mode = context["mode"]
    value = {
        "schema": SCHEDULE_SCHEMA,
        "version": "1.0.0",
        "status": "component_schedule_committed_before_first_call_and_outcome",
        "data_kind": manifest["data_kind"],
        "run_id": run_id,
        "contract_hash": validate_contract()["contract_hash"],
        "m57_1_mode_commitment_hash": mode["mode_commitment_hash"],
        "evidence_manifest_hash": manifest["manifest_hash"],
        "dataset_hash": mode["dataset_hash"],
        "prediction_commitment_hash": mode["prediction_commitment_hash"],
        "label_order": list(localization_m57.LABELS),
        "sample_count": 30,
        "stage_count": 5,
        "steps": steps,
        "required_model_call_count": sum(int(row["model_call_required"]) for row in steps),
        "target_outcome_access_count": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "formal_result_authorized": False,
    }
    value["schedule_hash"] = digest(value)
    validation = validate_schedule(value, run_id, context, manifest)
    if not validation["valid"]:
        raise AssertionError("M57.2 schedule invalid: " + "; ".join(validation["errors"]))
    return value


def validate_schedule(
    value: dict[str, Any], run_id: str, context: dict[str, Any], manifest: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        expected = deepcopy(value)
        expected.pop("schedule_hash", None)
        if value.get("schedule_hash") != digest(expected):
            errors.append("schedule.hash")
        if value.get("schema") != SCHEDULE_SCHEMA or value.get("status") != "component_schedule_committed_before_first_call_and_outcome":
            errors.append("schedule.schema_or_status")
        rebuilt = build_schedule_unvalidated(run_id, context, manifest)
        if value != rebuilt:
            errors.append("schedule.content")
        if value.get("required_model_call_count", 91) > 90:
            errors.append("schedule.call_count")
        if value.get("target_outcome_access_count") != 0:
            errors.append("schedule.outcome")
        if value.get("retry_count") != 0 or value.get("fallback_count") != 0:
            errors.append("schedule.retry")
        if value.get("formal_result_authorized") is not False:
            errors.append("schedule.formal_result")
        forbidden = _find_keys(value)
        errors.extend(f"schedule.forbidden:{name}" for name in forbidden)
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"schedule.structure:{exc}")
    return {
        "valid": not errors,
        "errors": errors,
        "schedule_hash": value.get("schedule_hash"),
        "required_model_call_count": value.get("required_model_call_count"),
    }


def build_schedule_unvalidated(
    run_id: str, context: dict[str, Any], manifest: dict[str, Any],
) -> dict[str, Any]:
    """Rebuild the deterministic schedule without recursive validation."""
    rows = context["rows"]
    task_map = _ours_task_map(rows)
    prediction_map = _ours_prediction_map(rows)
    artifacts = _artifact_map(rows)
    evidence_map = {row["sample_id"]: row for row in manifest["rows"]}
    steps: list[dict[str, Any]] = []
    for sample_id in _sample_order(rows):
        for stage_id in STAGE_IDS:
            evidence = evidence_map[sample_id]["stage_evidence"][stage_id]
            available = stage_id in PREOUTCOME_STAGES and evidence["availability"] == "available"
            prompt = build_component_prompt(task_map[sample_id], artifacts[sample_id], evidence) if available else None
            steps.append({
                "step_index": len(steps),
                "step_id": f"m57-2::{sample_id}::{stage_id}",
                "sample_id": sample_id,
                "stage_id": stage_id,
                "source_information_hash": task_map[sample_id]["view"]["source_information_hash"],
                "evidence_hash": evidence["evidence_hash"],
                "original_output_hash": digest(prediction_map[sample_id]["probabilities"]),
                "availability": "available" if available else "unavailable",
                "model_call_required": available,
                "prompt_hash": prompt["prompt_hash"] if prompt else None,
                "intervention_view_hash": prompt["intervention_view_hash"] if prompt else None,
                "future_outcome_used": False,
            })
    mode = context["mode"]
    value = {
        "schema": SCHEDULE_SCHEMA,
        "version": "1.0.0",
        "status": "component_schedule_committed_before_first_call_and_outcome",
        "data_kind": manifest["data_kind"],
        "run_id": run_id,
        "contract_hash": validate_contract()["contract_hash"],
        "m57_1_mode_commitment_hash": mode["mode_commitment_hash"],
        "evidence_manifest_hash": manifest["manifest_hash"],
        "dataset_hash": mode["dataset_hash"],
        "prediction_commitment_hash": mode["prediction_commitment_hash"],
        "label_order": list(localization_m57.LABELS),
        "sample_count": 30,
        "stage_count": 5,
        "steps": steps,
        "required_model_call_count": sum(int(row["model_call_required"]) for row in steps),
        "target_outcome_access_count": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "formal_result_authorized": False,
    }
    value["schedule_hash"] = digest(value)
    return value


def _empty_substitution(stage_id: str, evidence: dict[str, Any], plan_hash: str) -> dict[str, Any]:
    return {
        "stage_id": stage_id,
        "availability": "unavailable",
        "changed_component": stage_id,
        "plan_hash": plan_hash,
        "evidence_hash": evidence["evidence_hash"],
        "downstream_recomputed": False,
        "probabilities": None,
        "downstream_output_hash": None,
        "prompt_hash": None,
        "resource_call_id": None,
        "brief_evidence": None,
        "evidence_available_before_outcome": False,
        "future_outcome_used": False,
    }


def build_prediction_capsule(
    run_id: str, context: dict[str, Any], manifest: dict[str, Any],
    schedule: dict[str, Any], prediction_by_step: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    rows = context["rows"]
    mode = context["mode"]
    prediction_map = _ours_prediction_map(rows)
    evidence_map = {row["sample_id"]: row for row in manifest["rows"]}
    schedule_map = {row["step_id"]: row for row in schedule["steps"]}
    capsule_rows = []
    for sample_id in _sample_order(rows):
        original = prediction_map[sample_id]["probabilities"]
        substitutions: dict[str, dict[str, Any]] = {}
        for stage_id in STAGE_IDS:
            evidence = evidence_map[sample_id]["stage_evidence"][stage_id]
            plan_hash = mode["stage_plans"][stage_id]["plan_hash"]
            step_id = f"m57-2::{sample_id}::{stage_id}"
            if schedule_map[step_id]["model_call_required"]:
                prediction = prediction_by_step[step_id]
                substitutions[stage_id] = {
                    "stage_id": stage_id,
                    "availability": "available",
                    "changed_component": stage_id,
                    "plan_hash": plan_hash,
                    "evidence_hash": evidence["evidence_hash"],
                    "downstream_recomputed": True,
                    "probabilities": deepcopy(prediction["probabilities"]),
                    "downstream_output_hash": digest(prediction["probabilities"]),
                    "prompt_hash": schedule_map[step_id]["prompt_hash"],
                    "resource_call_id": prediction["resource_call_id"],
                    "brief_evidence": prediction["brief_evidence"],
                    "evidence_available_before_outcome": True,
                    "future_outcome_used": False,
                }
            else:
                substitutions[stage_id] = _empty_substitution(stage_id, evidence, plan_hash)
        capsule_rows.append({
            "sample_id": sample_id,
            "source_information_hash": evidence_map[sample_id]["source_information_hash"],
            "original_probabilities": deepcopy(original),
            "original_output_hash": digest(original),
            "substitutions": substitutions,
        })
    snapshot = rows["snapshot"]
    run = next(row for row in rows["manifest"]["condition_runs"] if row["condition_id"] == capsule_m56.PRIMARY_SYSTEM)
    value = {
        "schema": CAPSULE_SCHEMA,
        "version": "1.0.0",
        "status": "all_available_component_predictions_committed_before_outcome",
        "data_kind": manifest["data_kind"],
        "run_id": run_id,
        "contract_hash": validate_contract()["contract_hash"],
        "m57_1_mode_commitment_hash": mode["mode_commitment_hash"],
        "evidence_manifest_hash": manifest["manifest_hash"],
        "schedule_hash": schedule["schedule_hash"],
        "dataset_hash": mode["dataset_hash"],
        "m56_prediction_commitment_hash": mode["prediction_commitment_hash"],
        "model_name": run["model_name"],
        "model_artifact_digest": run["model_artifact_digest"],
        "hardware_fingerprint": snapshot["hardware_fingerprint"],
        "provider_options": deepcopy(run["provider_options"]),
        "input_token_budget": run["input_token_budget"],
        "output_token_budget": run["output_token_budget"],
        "label_order": list(localization_m57.LABELS),
        "sample_count": 30,
        "rows": capsule_rows,
        "available_prediction_count": len(prediction_by_step),
        "all_available_predictions_complete": len(prediction_by_step) == schedule["required_model_call_count"],
        "outcome_access_count_before_commitment": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "formal_m57_result_created": False,
        "m58_authorized": False,
        "claim_boundary": load_contract()["claim_boundary"],
    }
    value["capsule_hash"] = digest(value)
    return value


def _validate_capsule_and_ledger(
    capsule: dict[str, Any], ledger: dict[str, Any], run_id: str,
    context: dict[str, Any], manifest: dict[str, Any], schedule: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    capsule_fields = {
        "schema", "version", "status", "data_kind", "run_id", "contract_hash",
        "m57_1_mode_commitment_hash", "evidence_manifest_hash", "schedule_hash",
        "dataset_hash", "m56_prediction_commitment_hash", "model_name",
        "model_artifact_digest", "hardware_fingerprint", "provider_options",
        "input_token_budget", "output_token_budget", "label_order", "sample_count",
        "rows", "available_prediction_count", "all_available_predictions_complete",
        "outcome_access_count_before_commitment", "retry_count", "fallback_count",
        "formal_m57_result_created", "m58_authorized", "claim_boundary", "capsule_hash",
    }
    if not isinstance(capsule, dict) or set(capsule) != capsule_fields:
        errors.append("capsule.fields")
    unhashed_capsule = {key: child for key, child in capsule.items() if key != "capsule_hash"}
    if capsule.get("capsule_hash") != digest(unhashed_capsule):
        errors.append("capsule.hash")
    if capsule.get("schema") != CAPSULE_SCHEMA or capsule.get("status") != "all_available_component_predictions_committed_before_outcome":
        errors.append("capsule.schema_or_status")
    mode = context["mode"]
    expected_capsule_bindings = {
        "run_id": run_id,
        "contract_hash": validate_contract()["contract_hash"],
        "m57_1_mode_commitment_hash": mode["mode_commitment_hash"],
        "evidence_manifest_hash": manifest["manifest_hash"],
        "schedule_hash": schedule["schedule_hash"],
        "dataset_hash": mode["dataset_hash"],
        "m56_prediction_commitment_hash": mode["prediction_commitment_hash"],
        "data_kind": manifest["data_kind"],
    }
    for name, expected in expected_capsule_bindings.items():
        if capsule.get(name) != expected:
            errors.append(f"capsule.{name}")
    if capsule.get("sample_count") != 30 or tuple(capsule.get("label_order") or ()) != localization_m57.LABELS:
        errors.append("capsule.counts_or_labels")
    if capsule.get("available_prediction_count") != schedule.get("required_model_call_count"):
        errors.append("capsule.prediction_count")
    if capsule.get("all_available_predictions_complete") is not True:
        errors.append("capsule.complete")
    if capsule.get("outcome_access_count_before_commitment") != 0:
        errors.append("capsule.outcome")
    if capsule.get("retry_count") != 0 or capsule.get("fallback_count") != 0:
        errors.append("capsule.retry")
    if capsule.get("formal_m57_result_created") is not False or capsule.get("m58_authorized") is not False:
        errors.append("capsule.authority")
    forbidden = _find_keys(capsule)
    errors.extend(f"capsule.forbidden:{name}" for name in forbidden)
    rows = context["rows"]
    snapshot = rows["snapshot"]
    ours_run = next(row for row in rows["manifest"]["condition_runs"] if row["condition_id"] == capsule_m56.PRIMARY_SYSTEM)
    resource_bindings = {
        "model_name": ours_run["model_name"],
        "model_artifact_digest": ours_run["model_artifact_digest"],
        "hardware_fingerprint": snapshot["hardware_fingerprint"],
        "provider_options": ours_run["provider_options"],
        "input_token_budget": ours_run["input_token_budget"],
        "output_token_budget": ours_run["output_token_budget"],
    }
    for name, expected in resource_bindings.items():
        if capsule.get(name) != expected:
            errors.append(f"capsule.resource:{name}")
    expected_order = _sample_order(rows)
    prediction_map = _ours_prediction_map(rows)
    evidence_map = {row["sample_id"]: row for row in manifest["rows"]}
    schedule_map = {row["step_id"]: row for row in schedule["steps"]}
    capsule_rows = capsule.get("rows")
    if not isinstance(capsule_rows, list) or [row.get("sample_id") for row in capsule_rows if isinstance(row, dict)] != expected_order:
        errors.append("capsule.rows")
        capsule_rows = []
    call_ids: set[str] = set()
    for index, row in enumerate(capsule_rows):
        scope = f"capsule.row[{index}]"
        fields = {"sample_id", "source_information_hash", "original_probabilities", "original_output_hash", "substitutions"}
        if not isinstance(row, dict) or set(row) != fields:
            errors.append(f"{scope}.fields")
            continue
        sample_id = row["sample_id"]
        if sample_id not in evidence_map or sample_id not in prediction_map:
            errors.append(f"{scope}.sample")
            continue
        if row.get("source_information_hash") != evidence_map[sample_id]["source_information_hash"]:
            errors.append(f"{scope}.source")
        labels = list(localization_m57.LABELS)
        errors.extend(f"{scope}.original.{name}" for name in _validate_distribution(row.get("original_probabilities"), labels))
        expected_original = prediction_map[sample_id]["probabilities"]
        if row.get("original_probabilities") != expected_original or row.get("original_output_hash") != digest(expected_original):
            errors.append(f"{scope}.original_binding")
        substitutions = row.get("substitutions") or {}
        if tuple(substitutions) != STAGE_IDS:
            errors.append(f"{scope}.stages")
            continue
        for stage_id in STAGE_IDS:
            sub = substitutions[stage_id]
            sub_fields = {
                "stage_id", "availability", "changed_component", "plan_hash", "evidence_hash",
                "downstream_recomputed", "probabilities", "downstream_output_hash", "prompt_hash",
                "resource_call_id", "brief_evidence", "evidence_available_before_outcome", "future_outcome_used",
            }
            if not isinstance(sub, dict) or set(sub) != sub_fields:
                errors.append(f"{scope}.{stage_id}.fields")
                continue
            evidence = evidence_map[sample_id]["stage_evidence"][stage_id]
            step = schedule_map[f"m57-2::{sample_id}::{stage_id}"]
            if sub.get("stage_id") != stage_id or sub.get("changed_component") != stage_id:
                errors.append(f"{scope}.{stage_id}.component")
            if sub.get("plan_hash") != mode["stage_plans"][stage_id]["plan_hash"] or sub.get("evidence_hash") != evidence["evidence_hash"]:
                errors.append(f"{scope}.{stage_id}.binding")
            if sub.get("future_outcome_used") is not False:
                errors.append(f"{scope}.{stage_id}.future")
            if step["model_call_required"]:
                if sub.get("availability") != "available" or sub.get("downstream_recomputed") is not True:
                    errors.append(f"{scope}.{stage_id}.availability")
                errors.extend(f"{scope}.{stage_id}.{name}" for name in _validate_distribution(sub.get("probabilities"), labels))
                if sub.get("downstream_output_hash") != digest(sub.get("probabilities")):
                    errors.append(f"{scope}.{stage_id}.output_hash")
                if sub.get("prompt_hash") != step["prompt_hash"]:
                    errors.append(f"{scope}.{stage_id}.prompt")
                call_id = sub.get("resource_call_id")
                if not isinstance(call_id, str) or not call_id or call_id in call_ids:
                    errors.append(f"{scope}.{stage_id}.call_id")
                else:
                    call_ids.add(call_id)
                if sub.get("evidence_available_before_outcome") is not True:
                    errors.append(f"{scope}.{stage_id}.timing")
                if not isinstance(sub.get("brief_evidence"), str) or len(sub["brief_evidence"]) > 500:
                    errors.append(f"{scope}.{stage_id}.brief")
            else:
                if sub != _empty_substitution(stage_id, evidence, mode["stage_plans"][stage_id]["plan_hash"]):
                    errors.append(f"{scope}.{stage_id}.unavailable")
    unhashed_ledger = {key: child for key, child in ledger.items() if key != "ledger_hash"}
    ledger_fields = {
        "schema", "version", "status", "run_id", "schedule_hash",
        "evidence_manifest_hash", "required_call_count", "call_count", "calls",
        "target_outcome_access_count", "retry_count", "fallback_count", "ledger_hash",
    }
    if not isinstance(ledger, dict) or set(ledger) != ledger_fields:
        errors.append("ledger.fields")
    if ledger.get("ledger_hash") != digest(unhashed_ledger):
        errors.append("ledger.hash")
    if ledger.get("schema") != CALL_LEDGER_SCHEMA or ledger.get("status") != "complete_before_prediction_capsule_commitment":
        errors.append("ledger.schema_or_status")
    expected_ledger_bindings = {
        "run_id": run_id,
        "schedule_hash": schedule["schedule_hash"],
        "evidence_manifest_hash": manifest["manifest_hash"],
        "required_call_count": schedule["required_model_call_count"],
        "call_count": schedule["required_model_call_count"],
        "target_outcome_access_count": 0,
        "retry_count": 0,
        "fallback_count": 0,
    }
    for name, expected in expected_ledger_bindings.items():
        if ledger.get(name) != expected:
            errors.append(f"ledger.{name}")
    calls = ledger.get("calls")
    if not isinstance(calls, list) or len(calls) != schedule["required_model_call_count"]:
        errors.append("ledger.calls")
        calls = []
    ledger_ids: set[str] = set()
    for index, call in enumerate(calls):
        scope = f"ledger.call[{index}]"
        call_id = call.get("call_id") if isinstance(call, dict) else None
        if not isinstance(call_id, str) or call_id in ledger_ids:
            errors.append(f"{scope}.id")
            continue
        ledger_ids.add(call_id)
        unhashed_call = {key: child for key, child in call.items() if key != "call_hash"}
        if call.get("call_hash") != digest(unhashed_call):
            errors.append(f"{scope}.hash")
        step = schedule_map.get(call.get("step_id"))
        if step is None or not step["model_call_required"]:
            errors.append(f"{scope}.step")
        else:
            if call.get("sample_id") != step["sample_id"] or call.get("stage_id") != step["stage_id"] or call.get("prompt_hash") != step["prompt_hash"]:
                errors.append(f"{scope}.binding")
        resource_errors = runner_m56._validate_call_resources(
            call,
            input_budget=int(ours_run["input_token_budget"]),
            output_budget=int(ours_run["output_token_budget"]),
        )
        errors.extend(f"{scope}.{name}" for name in resource_errors)
        if call.get("model_reported") != ours_run["model_name"]:
            errors.append(f"{scope}.model")
    if ledger_ids != call_ids:
        errors.append("ledger.capsule_call_set")
    return {
        "valid": not errors,
        "errors": errors,
        "capsule_hash": capsule.get("capsule_hash"),
        "ledger_hash": ledger.get("ledger_hash"),
        "call_count": len(calls),
    }


def build_prediction_commitment(
    run_id: str, context: dict[str, Any], manifest: dict[str, Any],
    schedule: dict[str, Any], capsule: dict[str, Any], ledger: dict[str, Any],
    validation: dict[str, Any],
) -> dict[str, Any]:
    if not validation["valid"]:
        raise ValueError("cannot commit invalid component prediction capsule")
    mode = context["mode"]
    value = {
        "schema": COMMITMENT_SCHEMA,
        "version": "1.0.0",
        "status": "component_predictions_hash_committed_before_outcome",
        "run_id": run_id,
        "contract_hash": validate_contract()["contract_hash"],
        "m57_1_mode_commitment_hash": mode["mode_commitment_hash"],
        "evidence_manifest_hash": manifest["manifest_hash"],
        "schedule_hash": schedule["schedule_hash"],
        "capsule_hash": capsule["capsule_hash"],
        "call_ledger_hash": ledger["ledger_hash"],
        "available_prediction_count": capsule["available_prediction_count"],
        "target_outcome_access_count_before_commitment": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "formal_m57_result_created": False,
        "m58_authorized": False,
    }
    value["commitment_hash"] = digest(value)
    return value


def validate_prediction_commitment(
    value: dict[str, Any], run_id: str, context: dict[str, Any],
    manifest: dict[str, Any], schedule: dict[str, Any], capsule: dict[str, Any], ledger: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    unhashed = {key: child for key, child in value.items() if key != "commitment_hash"}
    if value.get("commitment_hash") != digest(unhashed):
        errors.append("commitment.hash")
    expected = {
        "schema": COMMITMENT_SCHEMA,
        "version": "1.0.0",
        "status": "component_predictions_hash_committed_before_outcome",
        "run_id": run_id,
        "contract_hash": validate_contract()["contract_hash"],
        "m57_1_mode_commitment_hash": context["mode"]["mode_commitment_hash"],
        "evidence_manifest_hash": manifest["manifest_hash"],
        "schedule_hash": schedule["schedule_hash"],
        "capsule_hash": capsule["capsule_hash"],
        "call_ledger_hash": ledger["ledger_hash"],
        "available_prediction_count": capsule["available_prediction_count"],
        "target_outcome_access_count_before_commitment": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "formal_m57_result_created": False,
        "m58_authorized": False,
    }
    expected["commitment_hash"] = digest(expected)
    if value != expected:
        errors.append("commitment.content")
    return {"valid": not errors, "errors": errors, "commitment_hash": value.get("commitment_hash")}


def _terminal_failure(paths: dict[str, Path], phase: str, exc: Exception) -> None:
    value = {
        "schema": FAILURE_SCHEMA,
        "version": "1.0.0",
        "status": "terminal_no_retry_component_generation_failure",
        "phase": phase,
        "error_type": type(exc).__name__,
        "error_message_digest": sha256(str(exc).encode("utf-8")).hexdigest(),
        "retry_authorized": False,
        "fallback_authorized": False,
        "prediction_commitment_created": False,
        "target_outcome_access_count": 0,
    }
    value["failure_hash"] = digest(value)
    try:
        durable_m56._durable_atomic_write_json(paths["m57_2_failure"], value, exclusive=True)
    except FileExistsError:
        pass


def _execute(run_id: str, *, allow_forged: bool) -> dict[str, Any]:
    contract = validate_contract()
    if not contract["valid"]:
        raise PermissionError("M57.2 contract invalid: " + "; ".join(contract["errors"]))
    single_writer_m56._validate_permitted_run(run_id)
    paths = _paths(run_id)
    phase = "input_validation"
    try:
        with single_writer_m56._exclusive_scoring_lock(single_writer_m56._lock_path(run_id)):
            context = _load_preoutcome_context(run_id)
            attempted_paths = (
                paths["m57_2_schedule"], paths["m57_2_capsule"], paths["m57_2_commitment"],
                paths["m57_2_ledger"], paths["m57_2_failure"],
            )
            if any(path.exists() for path in attempted_paths):
                raise FileExistsError("M57.2 run already attempted; retry is forbidden")
            prior_outcome = commitment_m57._present_outcome_state(paths)
            if prior_outcome:
                raise PermissionError("M57.2 cannot first execute after M56 outcome state: " + ", ".join(prior_outcome))
            if not paths["evidence"].exists():
                raise FileNotFoundError("M57.2 component evidence manifest is absent")
            manifest = load_json(paths["evidence"])
            evidence_validation = validate_evidence_manifest(manifest, run_id, context, allow_forged=allow_forged)
            if not evidence_validation["valid"]:
                raise PermissionError("M57.2 evidence invalid: " + "; ".join(evidence_validation["errors"]))
            phase = "schedule_commitment"
            schedule = build_schedule(run_id, context, manifest)
            durable_m56._durable_atomic_write_json(paths["m57_2_schedule"], schedule, exclusive=True)
            task_map = _ours_task_map(context["rows"])
            artifact_map = _artifact_map(context["rows"])
            evidence_map = {row["sample_id"]: row for row in manifest["rows"]}
            ours_run = next(
                row for row in context["rows"]["manifest"]["condition_runs"]
                if row["condition_id"] == capsule_m56.PRIMARY_SYSTEM
            )
            phase = "component_predictions"
            predictions: dict[str, dict[str, Any]] = {}
            calls: list[dict[str, Any]] = []
            for step in schedule["steps"]:
                if not step["model_call_required"]:
                    continue
                task = task_map[step["sample_id"]]
                evidence = evidence_map[step["sample_id"]]["stage_evidence"][step["stage_id"]]
                prompt = build_component_prompt(task, artifact_map[step["sample_id"]], evidence)
                call = runner_m56._ollama_generate(
                    prompt["prompt"],
                    _component_output_schema(task["view"]["candidate_behavior_labels"]),
                    ours_run["provider_options"],
                )
                call["prompt_hash"] = prompt["prompt_hash"]
                resource_errors = runner_m56._validate_call_resources(
                    call,
                    input_budget=int(ours_run["input_token_budget"]),
                    output_budget=int(ours_run["output_token_budget"]),
                )
                if resource_errors:
                    raise ValueError("component resource gate failed: " + "; ".join(resource_errors))
                runner_m56._validate_model_identity(call, ours_run["model_name"])
                probabilities, brief = _validate_component_output(
                    call["parsed"], task["view"]["candidate_behavior_labels"]
                )
                call_id = f"m57-2-call-{len(calls) + 1:03d}"
                predictions[step["step_id"]] = {
                    "probabilities": probabilities,
                    "brief_evidence": brief,
                    "resource_call_id": call_id,
                }
                ledger_call = {
                    "call_id": call_id,
                    "step_id": step["step_id"],
                    "sample_id": step["sample_id"],
                    "stage_id": step["stage_id"],
                    **{key: value for key, value in call.items() if key != "parsed"},
                }
                ledger_call["call_hash"] = digest(ledger_call)
                calls.append(ledger_call)
            phase = "capsule_and_ledger"
            ledger = {
                "schema": CALL_LEDGER_SCHEMA,
                "version": "1.0.0",
                "status": "complete_before_prediction_capsule_commitment",
                "run_id": run_id,
                "schedule_hash": schedule["schedule_hash"],
                "evidence_manifest_hash": manifest["manifest_hash"],
                "required_call_count": schedule["required_model_call_count"],
                "call_count": len(calls),
                "calls": calls,
                "target_outcome_access_count": 0,
                "retry_count": 0,
                "fallback_count": 0,
            }
            ledger["ledger_hash"] = digest(ledger)
            capsule = build_prediction_capsule(run_id, context, manifest, schedule, predictions)
            validation = _validate_capsule_and_ledger(capsule, ledger, run_id, context, manifest, schedule)
            if not validation["valid"]:
                raise ValueError("component capsule invalid: " + "; ".join(validation["errors"]))
            durable_m56._durable_atomic_write_json(paths["m57_2_capsule"], capsule, exclusive=True)
            durable_m56._durable_atomic_write_json(paths["m57_2_ledger"], ledger, exclusive=True)
            phase = "prediction_commitment"
            commitment = build_prediction_commitment(
                run_id, context, manifest, schedule, capsule, ledger, validation
            )
            durable_m56._durable_atomic_write_json(paths["m57_2_commitment"], commitment, exclusive=True)
            return {
                "status": "m57_2_component_predictions_committed_before_outcome",
                "schedule_hash": schedule["schedule_hash"],
                "capsule_hash": capsule["capsule_hash"],
                "call_ledger_hash": ledger["ledger_hash"],
                "commitment_hash": commitment["commitment_hash"],
                "model_call_count": len(calls),
                "target_outcome_access_count": 0,
                "formal_m57_result_created": False,
                "m58_authorized": False,
            }
    except Exception as exc:
        if paths["telemetry"].is_dir() and phase != "input_validation":
            _terminal_failure(paths, phase, exc)
        raise


def execute_m57_preoutcome_component_predictions(run_id: str) -> dict[str, Any]:
    """Execute only with real independent evidence; accepts no injectable inputs."""
    return _execute(run_id, allow_forged=False)


def _validate_m57_preoutcome_component_predictions(
    run_id: str, *, allow_forged: bool,
) -> dict[str, Any]:
    """Validate an existing capsule under an explicit internal evidence boundary."""
    contract = validate_contract()
    if not contract["valid"]:
        raise PermissionError("M57.2 contract invalid: " + "; ".join(contract["errors"]))
    context = _load_preoutcome_context(run_id)
    paths = context["paths"]
    for name in ("evidence", "m57_2_schedule", "m57_2_capsule", "m57_2_ledger", "m57_2_commitment"):
        if not paths[name].exists():
            raise PermissionError(f"M57.2 artifact missing: {name}")
    manifest = load_json(paths["evidence"])
    evidence_validation = validate_evidence_manifest(manifest, run_id, context, allow_forged=allow_forged)
    schedule = load_json(paths["m57_2_schedule"])
    schedule_validation = validate_schedule(schedule, run_id, context, manifest)
    capsule = load_json(paths["m57_2_capsule"])
    ledger = load_json(paths["m57_2_ledger"])
    capsule_validation = _validate_capsule_and_ledger(capsule, ledger, run_id, context, manifest, schedule)
    commitment = load_json(paths["m57_2_commitment"])
    commitment_validation = validate_prediction_commitment(
        commitment, run_id, context, manifest, schedule, capsule, ledger
    )
    errors = (
        [f"evidence:{name}" for name in evidence_validation["errors"]]
        + [f"schedule:{name}" for name in schedule_validation["errors"]]
        + [f"capsule:{name}" for name in capsule_validation["errors"]]
        + [f"commitment:{name}" for name in commitment_validation["errors"]]
    )
    return {
        "status": "m57_2_component_prediction_capsule_validated" if not errors else "m57_2_component_prediction_capsule_invalid",
        "valid": not errors,
        "errors": errors,
        "data_kind": manifest.get("data_kind"),
        "available_prediction_count": capsule.get("available_prediction_count"),
        "model_call_count": ledger.get("call_count"),
        "target_outcome_access_count": 0,
        "outcome_state_artifacts_now": commitment_m57._present_outcome_state(paths),
        "formal_m57_result_created": False,
        "m58_authorized": False,
        "claim_boundary": load_contract()["claim_boundary"],
    }


def validate_m57_preoutcome_component_predictions(run_id: str) -> dict[str, Any]:
    """Validate only formal-evidence capsules; forged fixtures remain invalid."""
    return _validate_m57_preoutcome_component_predictions(run_id, allow_forged=False)


def _mock_ollama_call(prompt: str, output_schema: dict[str, Any], options: dict[str, Any]) -> dict[str, Any]:
    del prompt, options
    labels = list(output_schema["properties"]["probabilities"]["required"])
    weights = {label: float(index + 1) for index, label in enumerate(labels)}
    total = sum(weights.values())
    return {
        "parsed": {
            "probabilities": {label: value / total for label, value in weights.items()},
            "brief_evidence": "Author-constructed no-model mechanics fixture.",
        },
        "raw_response_hash": "a" * 64,
        "prompt_tokens": 256,
        "completion_tokens": 64,
        "latency_seconds": 0.001,
        "process_cpu_seconds": 0.0005,
        "process_peak_rss_bytes": 1024,
        "ollama_rss_bytes": 2048,
        "total_duration_ns": 1000,
        "load_duration_ns": 100,
        "prompt_eval_duration_ns": 400,
        "eval_duration_ns": 500,
        "model_reported": "qwen3.5:9b",
        "transport_attempt_count": 1,
        "retry_count": 0,
        "fallback_count": 0,
    }


def build_engineering_rehearsal() -> dict[str, Any]:
    from test_m56_9_single_writer_formal_scoring import materialize_scoring_run
    from test_m56_10_crash_safe_outcome_join import m5610_private_roots

    with TemporaryDirectory(prefix="uruha-m57-2-component-capsule-") as temp:
        root = Path(temp)
        run_id = "m57-2-forged-component-capsule"
        with m5610_private_roots(root):
            run_root = materialize_scoring_run(root, run_id)
            commitment_m57.commit_m57_preoutcome_diagnostic_mode(run_id)
            context = _load_preoutcome_context(run_id)
            manifest = build_forged_engineering_evidence_manifest(run_id, context)
            durable_m56._durable_atomic_write_json(
                run_root / "generation" / EVIDENCE_FILENAME, manifest, exclusive=True
            )
            started = time.perf_counter()
            with mock.patch.object(runner_m56, "_ollama_generate", side_effect=_mock_ollama_call):
                execution = _execute(run_id, allow_forged=True)
            elapsed = time.perf_counter() - started
            validation = _validate_m57_preoutcome_component_predictions(run_id, allow_forged=True)
            sizes = {
                "evidence_manifest": (run_root / "generation" / EVIDENCE_FILENAME).stat().st_size,
                "schedule": (run_root / "generation" / SCHEDULE_FILENAME).stat().st_size,
                "prediction_capsule": (run_root / "generation" / CAPSULE_FILENAME).stat().st_size,
                "call_ledger": (run_root / "telemetry" / CALL_LEDGER_FILENAME).stat().st_size,
                "prediction_commitment": (run_root / "commitments" / COMMITMENT_FILENAME).stat().st_size,
            }
            public_run_id = "m57-2-public-rejects-forged-evidence"
            public_root = materialize_scoring_run(root, public_run_id)
            commitment_m57.commit_m57_preoutcome_diagnostic_mode(public_run_id)
            public_context = _load_preoutcome_context(public_run_id)
            forged_public = build_forged_engineering_evidence_manifest(public_run_id, public_context)
            durable_m56._durable_atomic_write_json(
                public_root / "generation" / EVIDENCE_FILENAME, forged_public, exclusive=True
            )
            model_calls = {"count": 0}

            def counted_call(*args: Any, **kwargs: Any) -> dict[str, Any]:
                model_calls["count"] += 1
                return _mock_ollama_call(*args, **kwargs)

            with mock.patch.object(runner_m56, "_ollama_generate", side_effect=counted_call):
                try:
                    execute_m57_preoutcome_component_predictions(public_run_id)
                    public_rejection = False
                except PermissionError:
                    public_rejection = True
            public_schedule_created = (public_root / "generation" / SCHEDULE_FILENAME).exists()
    value = {
        "schema": REHEARSAL_SCHEMA,
        "version": "1.0.0",
        "status": "forged_90_prediction_mechanics_complete_public_formal_path_denied",
        "contract_hash": validate_contract()["contract_hash"],
        "fixture_kind": "temporary_author_constructed_30_row_evidence_and_mocked_model_calls_engineering_only",
        "sample_count": 30,
        "stage_count": 5,
        "available_preoutcome_stage_count": 3,
        "available_prediction_count": validation["available_prediction_count"],
        "mocked_model_call_count": execution["model_call_count"],
        "expected_maximum_model_call_count": 90,
        "public_formal_path_rejected_author_constructed_evidence": public_rejection,
        "public_rejection_model_call_count": model_calls["count"],
        "public_rejection_schedule_created": public_schedule_created,
        "capsule_validation_passed": validation["valid"],
        "schedule_committed_before_calls": True,
        "target_outcome_access_count": 0,
        "elapsed_seconds": elapsed,
        "artifact_utf8_bytes": sizes,
        "decision_stage_preoutcome_available": False,
        "realization_stage_available_without_human_ratings": False,
        "formal_m57_result_created": False,
        "m58_authorized": False,
        "claim_boundary": load_contract()["claim_boundary"],
    }
    value["rehearsal_hash"] = digest(value)
    report = validate_rehearsal(value)
    if not report["valid"]:
        raise AssertionError("M57.2 rehearsal invalid: " + "; ".join(report["errors"]))
    return value


def validate_rehearsal(value: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    unhashed = {key: child for key, child in value.items() if key != "rehearsal_hash"}
    if value.get("rehearsal_hash") != digest(unhashed):
        errors.append("rehearsal.hash")
    if value.get("schema") != REHEARSAL_SCHEMA or value.get("status") != "forged_90_prediction_mechanics_complete_public_formal_path_denied":
        errors.append("rehearsal.schema_or_status")
    if value.get("contract_hash") != validate_contract()["contract_hash"]:
        errors.append("rehearsal.contract")
    if value.get("sample_count") != 30 or value.get("stage_count") != 5 or value.get("available_preoutcome_stage_count") != 3:
        errors.append("rehearsal.counts")
    if value.get("available_prediction_count") != 90 or value.get("mocked_model_call_count") != 90:
        errors.append("rehearsal.predictions")
    if value.get("expected_maximum_model_call_count") != 90:
        errors.append("rehearsal.maximum")
    if value.get("public_formal_path_rejected_author_constructed_evidence") is not True:
        errors.append("rehearsal.public_rejection")
    if value.get("public_rejection_model_call_count") != 0 or value.get("public_rejection_schedule_created") is not False:
        errors.append("rehearsal.reject_before_call")
    if value.get("capsule_validation_passed") is not True or value.get("schedule_committed_before_calls") is not True:
        errors.append("rehearsal.validation_or_order")
    if value.get("target_outcome_access_count") != 0:
        errors.append("rehearsal.outcome")
    if value.get("decision_stage_preoutcome_available") is not False or value.get("realization_stage_available_without_human_ratings") is not False:
        errors.append("rehearsal.stage_boundary")
    if value.get("formal_m57_result_created") is not False or value.get("m58_authorized") is not False:
        errors.append("rehearsal.authority")
    sizes = value.get("artifact_utf8_bytes") or {}
    if set(sizes) != {"evidence_manifest", "schedule", "prediction_capsule", "call_ledger", "prediction_commitment"}:
        errors.append("rehearsal.sizes")
    elif any(not isinstance(size, int) or size <= 0 for size in sizes.values()):
        errors.append("rehearsal.size_values")
    return {"valid": not errors, "errors": errors, "rehearsal_hash": value.get("rehearsal_hash")}


def build_live_audit() -> dict[str, Any]:
    upstream = commitment_m57.build_live_audit()
    value = {
        "schema": AUDIT_SCHEMA,
        "version": "1.0.0",
        "status": "m57_2_mechanism_ready_but_live_evidence_and_formal_capsule_absent",
        "contract_valid": validate_contract()["valid"],
        "contract_hash": validate_contract()["contract_hash"],
        "counts": deepcopy(upstream["counts"]),
        "live_component_evidence_manifests": 0,
        "live_component_prediction_capsules": 0,
        "formal_m57_execution_authorized": False,
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
        raise PermissionError("invalid saved M57.2 rehearsal: " + "; ".join(validation["errors"]))
    return value


def render_dashboard(
    rehearsal: dict[str, Any] | None = None, audit: dict[str, Any] | None = None,
) -> str:
    rehearsal = deepcopy(rehearsal or load_saved_rehearsal())
    audit = deepcopy(audit or build_live_audit())
    if not validate_rehearsal(rehearsal)["valid"]:
        raise PermissionError("invalid M57.2 rehearsal cannot be rendered")
    counts = audit["counts"]
    total_bytes = sum(rehearsal["artifact_utf8_bytes"].values())
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>M57.2 元件預測膠囊</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#07131a;color:#f1fbff;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}main{{max-width:1180px;margin:auto;padding:28px}}section{{border:1px solid #34596c;border-radius:20px;background:#0d202a;padding:24px;margin-bottom:18px;overflow:hidden}}.hero{{background:linear-gradient(135deg,#123c48,#382844)}}h1{{font-size:clamp(30px,5vw,48px);margin:12px 0}}p{{color:#c7dce5;line-height:1.65}}.deny{{display:inline-block;background:#6e2635;color:#ffe2e8;padding:8px 12px;border-radius:999px;font-weight:850}}.flow{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}}.card{{min-width:0;border:1px solid #466b7e;border-radius:16px;background:#081922;padding:17px}}.card b,.card span{{display:block;overflow-wrap:anywhere}}.card b{{color:#86ebca;font-size:18px}}.card span{{color:#bdd4de;margin-top:8px;line-height:1.5}}.metric{{font-size:34px;font-weight:900;color:#79e6c2}}.stages{{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px}}.yes{{border-color:#48af8a}}.no{{border-color:#aa6470}}.compare{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}.before{{border-color:#b96772}}.after{{border-color:#4fb88f}}.boundary{{border-left:6px solid #dfaa55;background:#282115}}@media(max-width:900px){{.flow,.stages,.compare{{grid-template-columns:1fr}}}}
</style></head><body><main><section class="hero"><span class="deny">FORMAL M57 DENIED · V7 {counts['v7_slots_by_ledger'][0]}/18 + {counts['v7_slots_by_ledger'][1]}/18</span><h1>M57.2 · 不只先寫計畫，連替換後答案也先封存</h1><p>每一題都先綁定「替換哪個元件、證據從哪來、替換後預測如何變」，之後才允許碰真正結果。</p></section>
<section><h2>答案前的資料流</h2><div class="flow"><div class="card"><b>① M56 原始預測</b><span>30 題 Ours distributions 已封存</span></div><div class="card"><b>② 元件證據</b><span>逐題來源 hash、兩位 coder／proxy、adjudication</span></div><div class="card"><b>③ 下游重算</b><span>同模型、同參數、最多 3 × 30 calls</span></div><div class="card"><b>④ 預測膠囊</b><span>schedule → ledger → capsule → commitment，全在答案前</span></div></div></section>
<section><h2>五層不是都能現在假裝有答案</h2><div class="stages"><div class="card yes"><b>感知</b><span>可用：兩 coder + adjudicator</span></div><div class="card yes"><b>檢索</b><span>可用：只選 cutoff 前 history ID</span></div><div class="card yes"><b>狀態</b><span>可用：僅 observable proxy</span></div><div class="card no"><b>決策</b><span>不可用：要等 withheld outcome</span></div><div class="card no"><b>表達</b><span>不可用：缺獨立盲式人評</span></div></div></section>
<section><h2>修改前後</h2><div class="compare"><div class="card before"><b>M57.1</b><div class="metric">5 個 generic plans</div><p>能證明計畫比答案早，還沒有逐題 evidence 或 substitution prediction。</p></div><div class="card after"><b>M57.2 工程驗證</b><div class="metric">{rehearsal['available_prediction_count']} 個 predictions</div><p>30 題 × 3 個可用層；{rehearsal['mocked_model_call_count']} 次 mocked calls，0 次 target outcome access。作者造的資料被正式入口拒絕。</p></div></div></section>
<section><h2>成本與可追溯性</h2><p>隔離 fixture 五個封存檔合計 {total_bytes:,} bytes；工程執行 {rehearsal['elapsed_seconds']:.3f} 秒。正式執行上限為 90 次本機模型呼叫，實際 tokens／延遲／CPU／記憶體必須逐次記錄。</p></section>
<section class="boundary"><h2>這仍不是 Uruha 的正式錯誤定位</h2><p>畫面中的 90 個預測只驗證機制，標註與模型回覆都是 author-constructed／mocked。真實 temporal rows 仍是 {counts['real_temporal_rows']}/30，live capsule 0，formal M57 result 0，M58 denied。</p></section></main></body></html>"""


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
    parser = argparse.ArgumentParser(description="M57.2 component prediction capsule")
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
