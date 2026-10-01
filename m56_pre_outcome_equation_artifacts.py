#!/usr/bin/env python3
"""M56.1 outcome-blind Equation V1 artifact materialization and binding.

The frozen M56 capsule requires three Ours provenance hashes.  This overlay
turns the exact pre-cutoff source shared by B5 and Ours into real,
content-addressed fit/state/transition artifacts.  It does not change the
frozen capsule and it does not authorize real-data execution.
"""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
from typing import Any

import m55_temporal_row_contract as temporal_m55
import m56_blinded_execution_capsule as capsule_m56
import m56_fair_comparison_preflight as preflight_m56
import uruha_human_response_equation_m54 as equation_m54


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/m56_pre_outcome_equation_artifacts_v1.json"
FIT_SCHEMA = "uruha_m56_equation_v1_pre_outcome_fit_artifact_v1"
STATE_SCHEMA = "uruha_m56_equation_v1_pre_outcome_state_snapshot_v1"
TRANSITION_SCHEMA = "uruha_m56_equation_v1_pre_outcome_transition_trace_v1"
BUNDLE_SCHEMA = "uruha_m56_equation_v1_pre_outcome_artifact_bundle_v1"
REQUEST_SCHEMA = "uruha_m56_equation_bound_generation_request_v1"
RECEIPT_SCHEMA = "uruha_m56_equation_bound_commitment_receipt_v1"
EXPECTED_VARIABLE_IDS = equation_m54.EXPECTED_VARIABLE_IDS


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


def validate_contract(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors: list[str] = []
    if contract.get("schema") != "uruha_m56_pre_outcome_equation_artifact_contract_v1":
        errors.append("schema")
    if contract.get("version") != "1.0.0":
        errors.append("version")
    if contract.get("status") != "frozen_before_real_m55_rows_or_target_outcome_access":
        errors.append("status")
    bindings = contract.get("bindings")
    if not isinstance(bindings, dict) or len(bindings) != 7:
        errors.append("bindings")
    else:
        for name, binding in bindings.items():
            if not _binding_valid(binding):
                errors.append(f"binding:{name}")
    schemas = contract.get("schemas") or {}
    expected_schemas = {
        "fit_artifact": FIT_SCHEMA,
        "state_snapshot": STATE_SCHEMA,
        "transition_trace": TRANSITION_SCHEMA,
        "artifact_bundle": BUNDLE_SCHEMA,
        "generation_request": REQUEST_SCHEMA,
        "commitment_receipt": RECEIPT_SCHEMA,
    }
    if schemas != expected_schemas:
        errors.append("schemas")
    fit = contract.get("fit") or {}
    if fit.get("method") != "observable_history_dirichlet_and_sparse_transition_counts_v1":
        errors.append("fit.method")
    if fit.get("dirichlet_alpha") != 1.0:
        errors.append("fit.alpha")
    for field in (
        "current_sample_outcome_allowed",
        "private_state_target_allowed",
        "history_available_after_cutoff_allowed",
        "raw_text_persisted",
    ):
        if fit.get(field) is not False:
            errors.append(f"fit.{field}")
    state = contract.get("state") or {}
    if tuple(state.get("variable_ids") or []) != EXPECTED_VARIABLE_IDS:
        errors.append("state.variable_ids")
    if set(state.get("unavailable_private_variables") or []) != {
        "transient_state", "relationship_state", "goal_need_state"
    }:
        errors.append("state.unavailable_private_variables")
    if state.get("unknown_may_be_imputed") is not False:
        errors.append("state.unknown_may_be_imputed")
    transition = contract.get("transition") or {}
    if transition.get("method") != "observable_pre_cutoff_snapshot_delta_v1":
        errors.append("transition.method")
    if transition.get("history_must_be_monotonic_for_same_target") is not True:
        errors.append("transition.history_monotonicity")
    if transition.get("private_psychological_transition_claimed") is not False:
        errors.append("transition.private_claim")
    binding = contract.get("binding") or {}
    for field in (
        "B5_and_Ours_source_hash_must_match",
        "Ours_receives_validated_artifact_payload",
        "submission_hashes_must_match_artifact_content",
        "wrapper_receipt_binds_frozen_submission_receipt_and_bundle",
        "wrapper_scorer_revalidates_bundle_before_outcome_join",
    ):
        if binding.get(field) is not True:
            errors.append(f"binding_rule:{field}")
    if binding.get("B5_receives_equation_artifacts") is not False:
        errors.append("binding_rule:B5_artifact_exposure")
    resources = contract.get("resource_accounting") or {}
    for field in ("artifact_model_calls", "artifact_target_outcome_access", "artifact_production_memory_writes"):
        if resources.get(field) != 0:
            errors.append(f"resources:{field}")
    authorization = contract.get("authorization") or {}
    if not authorization or any(value is not False for value in authorization.values()):
        errors.append("authorization")
    return {
        "valid": not errors,
        "errors": errors,
        "contract_hash": digest(contract),
        "binding_count": len(bindings or {}),
        "variable_count": len(state.get("variable_ids") or []),
    }


def _find_forbidden_keys(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if key in capsule_m56.OUTCOME_KEYS:
                found.append(path)
            found.extend(_find_forbidden_keys(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_find_forbidden_keys(child, f"{prefix}[{index}]"))
    return found


def _time(value: Any, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO datetime") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return parsed


def _normalized_prior(labels: list[str], counts: Counter[str], alpha: float) -> dict[str, float]:
    total = sum(counts[label] + alpha for label in labels)
    values = {label: round((counts[label] + alpha) / total, 12) for label in labels}
    correction = round(1.0 - sum(values.values()), 12)
    values[labels[-1]] = round(values[labels[-1]] + correction, 12)
    return values


def _project_source(source: dict[str, Any]) -> dict[str, Any]:
    required = {
        "sample_id", "prediction_time", "available_history_cutoff",
        "candidate_behavior_labels", "current_pre_cutoff_event", "participants",
        "target", "all_pre_cutoff_history",
    }
    if set(source) != required:
        raise ValueError("source information fields do not match frozen B5/Ours view")
    labels = source.get("candidate_behavior_labels")
    if not isinstance(labels, list) or not labels or len(labels) != len(set(labels)):
        raise ValueError("candidate behavior labels must be unique and nonempty")
    if any(not isinstance(label, str) or not label for label in labels):
        raise ValueError("candidate behavior labels must be text")
    cutoff = _time(source.get("available_history_cutoff"), "available_history_cutoff")
    prediction_time = _time(source.get("prediction_time"), "prediction_time")
    if prediction_time != cutoff:
        raise ValueError("prediction time and available-history cutoff must match")
    event = source.get("current_pre_cutoff_event")
    if not isinstance(event, str) or not event.strip():
        raise ValueError("current pre-cutoff event must be nonempty text")
    participants = source.get("participants")
    if not isinstance(participants, list):
        raise ValueError("participants must be an array")
    target = source.get("target")
    if not isinstance(target, dict) or set(target) != {"target_id", "display_name", "persona_summary"}:
        raise ValueError("target identity shape mismatch")
    if not str(target.get("target_id") or ""):
        raise ValueError("target ID is required")
    history = source.get("all_pre_cutoff_history")
    if not isinstance(history, list):
        raise ValueError("history must be an array")
    projected_history: list[dict[str, Any]] = []
    seen: set[str] = set()
    previous_available: datetime | None = None
    for index, row in enumerate(history):
        if not isinstance(row, dict):
            raise ValueError(f"history[{index}] must be an object")
        expected = {
            "history_id", "event_time", "available_at", "observable_summary",
            "behavior_label", "evidence_type",
        }
        if set(row) != expected:
            raise ValueError(f"history[{index}] fields mismatch")
        history_id = str(row.get("history_id") or "")
        if not history_id or history_id in seen:
            raise ValueError("history IDs must be nonempty and unique")
        seen.add(history_id)
        event_time = _time(row.get("event_time"), f"history[{index}].event_time")
        available_at = _time(row.get("available_at"), f"history[{index}].available_at")
        if event_time > available_at or available_at > cutoff:
            raise ValueError("history must be completed and available before cutoff")
        if previous_available is not None and available_at < previous_available:
            raise ValueError("history must be ordered by availability")
        previous_available = available_at
        label = str(row.get("behavior_label") or "")
        if label not in labels:
            raise ValueError("history behavior label is outside the frozen taxonomy")
        summary = row.get("observable_summary")
        if not isinstance(summary, str) or not summary.strip():
            raise ValueError("history observable summary must be nonempty text")
        projected_history.append(
            {
                "history_id": history_id,
                "event_time": event_time.isoformat(),
                "available_at": available_at.isoformat(),
                "behavior_label": label,
                "evidence_type": str(row.get("evidence_type") or ""),
                "observable_summary_digest": digest(summary),
                "source_record_digest": digest(row),
                "raw_summary_persisted": False,
            }
        )
    return {
        "sample_id": str(source["sample_id"]),
        "prediction_time": prediction_time.isoformat(),
        "available_history_cutoff": cutoff.isoformat(),
        "candidate_behavior_labels": list(labels),
        "current_event_digest": digest(event),
        "current_event_character_count": len(event),
        "participants_digest": digest(participants),
        "participant_count": len(participants),
        "target_id": str(target["target_id"]),
        "target_display_name_digest": digest(target.get("display_name")),
        "persona_summary_digest": digest(target.get("persona_summary")),
        "history": projected_history,
        "raw_current_or_history_text_persisted": False,
    }


def _fit_artifact(
    projection: dict[str, Any],
    *,
    source_hash: str,
    equation_contract_hash: str,
    artifact_contract_hash: str,
    contract: dict[str, Any],
) -> dict[str, Any]:
    labels = projection["candidate_behavior_labels"]
    history = projection["history"]
    counts = Counter(row["behavior_label"] for row in history)
    alpha = float(contract["fit"]["dirichlet_alpha"])
    transitions = Counter(
        (left["behavior_label"], right["behavior_label"])
        for left, right in zip(history, history[1:])
    )
    equation = equation_m54.load_contract()
    artifact = {
        "schema": FIT_SCHEMA,
        "version": "1.0.0",
        "sample_id": projection["sample_id"],
        "target_id": projection["target_id"],
        "prediction_time": projection["prediction_time"],
        "available_history_cutoff": projection["available_history_cutoff"],
        "source_information_hash": source_hash,
        "equation_contract_hash": equation_contract_hash,
        "artifact_contract_hash": artifact_contract_hash,
        "fit_method": contract["fit"]["method"],
        "dirichlet_alpha": alpha,
        "fit_basis": {
            "history_ids": [row["history_id"] for row in history],
            "history_record_digests": [row["source_record_digest"] for row in history],
            "effective_sample_count": len(history),
            "behavior_label_counts": {label: counts[label] for label in labels},
            "observable_transition_counts": [
                {"from_label": left, "to_label": right, "count": transitions[(left, right)]}
                for left, right in sorted(transitions)
            ],
        },
        "person_parameter_estimate": {
            "parameter_id": equation["person_parameter"]["id"],
            "target_id": projection["target_id"],
            "public_persona_summary_digest": projection["persona_summary_digest"],
            "fit_status": "pre_cutoff_observable_behavior_only",
            "smoothed_behavior_prior": _normalized_prior(labels, counts, alpha),
            "private_or_unpublished_parameter_space": "unknown",
        },
        "data_boundary": {
            "current_target_behavior_used": False,
            "post_cutoff_history_used": False,
            "private_state_target_used": False,
            "raw_text_persisted": False,
        },
        "resource_accounting": {
            "model_calls": 0,
            "target_access_count": 0,
            "production_memory_writes": 0,
            "method": "deterministic_local_numeric_projection",
        },
    }
    artifact["fit_artifact_hash"] = digest(artifact)
    return artifact


def _variable(
    definition: dict[str, Any],
    *,
    status: str,
    evidence_refs: list[str],
    value: Any,
) -> dict[str, Any]:
    return {
        "id": definition["id"],
        "symbol": definition["symbol"],
        "epistemic_status": definition["epistemic_status"],
        "status": status,
        "evidence_refs": list(evidence_refs),
        "value": deepcopy(value),
        "value_hash": digest(value),
        "raw_text_persisted": False,
    }


def _state_snapshot(
    projection: dict[str, Any],
    fit: dict[str, Any],
    *,
    source_hash: str,
    equation_contract_hash: str,
    artifact_contract_hash: str,
) -> dict[str, Any]:
    equation = equation_m54.load_contract()
    definitions = {row["id"]: row for row in equation["variables"]}
    history = projection["history"]
    fit_basis = fit["fit_basis"]
    most_recent = history[-1]["behavior_label"] if history else None
    values: dict[str, tuple[str, list[str], Any]] = {
        "current_observable_input": (
            "observed_pre_cutoff",
            ["source_information.current_pre_cutoff_event"],
            {
                "event_digest": projection["current_event_digest"],
                "character_count": projection["current_event_character_count"],
                "input_representation": "researcher_paraphrased_text",
            },
        ),
        "observable_history": (
            "observed_pre_cutoff",
            [f"history:{row['history_id']}" for row in history],
            {
                "history_ids": [row["history_id"] for row in history],
                "history_record_digests": [row["source_record_digest"] for row in history],
                "history_count": len(history),
                "cutoff": projection["available_history_cutoff"],
            },
        ),
        "structured_memory": (
            "derived_pre_cutoff" if history else "derived_empty_pre_cutoff",
            [f"history:{row['history_id']}" for row in history],
            {
                "behavior_label_counts": deepcopy(fit_basis["behavior_label_counts"]),
                "most_recent_observable_behavior": most_recent,
                "observable_transition_count": sum(
                    row["count"] for row in fit_basis["observable_transition_counts"]
                ),
            },
        ),
        "transient_state": ("unavailable_not_inferred", [], None),
        "relationship_state": ("unavailable_not_inferred", [], None),
        "goal_need_state": ("unavailable_not_inferred", [], None),
        "observable_context": (
            "observed_pre_cutoff",
            ["source_information.prediction_time", "source_information.participants"],
            {
                "prediction_time": projection["prediction_time"],
                "available_history_cutoff": projection["available_history_cutoff"],
                "participant_count": projection["participant_count"],
                "participants_digest": projection["participants_digest"],
                "input_modality": "text_paraphrase",
                "acoustic_evidence_status": "unavailable",
            },
        ),
        "person_parameter": (
            "declared_and_pre_cutoff_fitted",
            ["equation_v1.person_parameter", "pre_outcome_fit_artifact"],
            {
                "parameter_id": fit["person_parameter_estimate"]["parameter_id"],
                "target_id": projection["target_id"],
                "persona_summary_digest": projection["persona_summary_digest"],
                "fit_artifact_hash": fit["fit_artifact_hash"],
                "effective_sample_count": fit_basis["effective_sample_count"],
                "private_or_unpublished_parameter_space": "unknown",
            },
        ),
        "uncertainty_calibration": (
            "derived_not_holdout_calibrated",
            ["pre_outcome_fit_artifact", "variable_availability"],
            {
                "effective_sample_count": fit_basis["effective_sample_count"],
                "unknown_variable_ids": [
                    "transient_state", "relationship_state", "goal_need_state"
                ],
                "available_variable_fraction": round(6 / 9, 6),
                "calibration_status": "not_holdout_calibrated",
            },
        ),
    }
    variables = [
        _variable(
            definitions[variable_id],
            status=values[variable_id][0],
            evidence_refs=values[variable_id][1],
            value=values[variable_id][2],
        )
        for variable_id in EXPECTED_VARIABLE_IDS
    ]
    snapshot = {
        "schema": STATE_SCHEMA,
        "version": "1.0.0",
        "sample_id": projection["sample_id"],
        "target_id": projection["target_id"],
        "prediction_time": projection["prediction_time"],
        "available_history_cutoff": projection["available_history_cutoff"],
        "source_information_hash": source_hash,
        "equation_contract_hash": equation_contract_hash,
        "artifact_contract_hash": artifact_contract_hash,
        "fit_artifact_hash": fit["fit_artifact_hash"],
        "variables": variables,
        "coverage": {
            "available_or_derived_variable_count": 6,
            "unknown_variable_count": 3,
            "unknown_variable_ids": [
                "transient_state", "relationship_state", "goal_need_state"
            ],
            "private_state_fabrication_count": 0,
        },
        "data_boundary": {
            "current_target_behavior_used": False,
            "post_cutoff_history_used": False,
            "private_state_fact_created": False,
            "raw_text_persisted": False,
        },
        "resource_accounting": {
            "model_calls": 0,
            "target_access_count": 0,
            "production_memory_writes": 0,
        },
    }
    snapshot["state_snapshot_hash"] = digest(snapshot)
    return snapshot


def _value_by_id(snapshot: dict[str, Any], variable_id: str) -> Any:
    row = next(item for item in snapshot["variables"] if item["id"] == variable_id)
    return row["value"]


def _transition_trace(
    current: dict[str, Any],
    fit: dict[str, Any],
    previous: dict[str, Any] | None,
    *,
    artifact_contract_hash: str,
    contract: dict[str, Any],
) -> dict[str, Any]:
    current_history = _value_by_id(current, "observable_history")["history_ids"]
    current_counts = _value_by_id(current, "structured_memory")["behavior_label_counts"]
    previous_history: list[str] = []
    previous_counts = {label: 0 for label in current_counts}
    prior_hash = None
    prior_sample_id = None
    transition_origin = "declared_empty_prior"
    if previous is not None and previous.get("target_id") == current.get("target_id"):
        previous_history = _value_by_id(previous, "observable_history")["history_ids"]
        previous_counts = _value_by_id(previous, "structured_memory")["behavior_label_counts"]
        if not set(previous_history).issubset(set(current_history)):
            raise ValueError("same-target pre-cutoff history must be monotonic")
        prior_hash = previous["state_snapshot_hash"]
        prior_sample_id = previous["sample_id"]
        transition_origin = "previous_pre_cutoff_snapshot"
    current_by_id = {row["id"]: row for row in current["variables"]}
    previous_by_id = {row["id"]: row for row in previous["variables"]} if prior_hash else {}
    changes = []
    for variable_id in EXPECTED_VARIABLE_IDS:
        now = current_by_id[variable_id]
        before = previous_by_id.get(variable_id)
        before_status = before["status"] if before else "declared_prior_unmaterialized"
        before_hash = before["value_hash"] if before else None
        if before_hash != now["value_hash"] or before_status != now["status"]:
            changes.append(
                {
                    "variable_id": variable_id,
                    "before_status": before_status,
                    "after_status": now["status"],
                    "before_value_hash": before_hash,
                    "after_value_hash": now["value_hash"],
                }
            )
    delta_counts = {
        label: int(current_counts[label]) - int(previous_counts.get(label, 0))
        for label in current_counts
    }
    trace = {
        "schema": TRANSITION_SCHEMA,
        "version": "1.0.0",
        "sample_id": current["sample_id"],
        "target_id": current["target_id"],
        "prediction_time": current["prediction_time"],
        "available_history_cutoff": current["available_history_cutoff"],
        "artifact_contract_hash": artifact_contract_hash,
        "transition_method": contract["transition"]["method"],
        "transition_origin": transition_origin,
        "previous_sample_id": prior_sample_id,
        "previous_state_snapshot_hash": prior_hash,
        "current_state_snapshot_hash": current["state_snapshot_hash"],
        "fit_artifact_hash": fit["fit_artifact_hash"],
        "observable_delta": {
            "newly_available_history_ids": [
                history_id for history_id in current_history if history_id not in previous_history
            ],
            "removed_history_ids": [
                history_id for history_id in previous_history if history_id not in current_history
            ],
            "behavior_label_count_delta": delta_counts,
            "fit_effective_sample_count_delta": len(current_history) - len(previous_history),
            "changed_variable_count": len(changes),
            "variable_changes": changes,
        },
        "data_boundary": {
            "current_target_behavior_used": False,
            "post_cutoff_history_used": False,
            "private_psychological_transition_inferred": False,
            "raw_text_persisted": False,
        },
        "execution": {
            "behavior_prediction_performed": False,
            "language_generation_performed": False,
            "model_calls": 0,
            "target_access_count": 0,
            "production_memory_writes": 0,
        },
    }
    trace["transition_trace_hash"] = digest(trace)
    return trace


def _materialize_bundle_unchecked(
    packet: dict[str, Any],
    capsule: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    contract_report = validate_contract(contract)
    equation_report = equation_m54.validate_contract_m54(equation_m54.load_contract())
    ours_tasks = {
        task["sample_id"]: task
        for task in capsule["prediction_tasks"]
        if task["condition_id"] == capsule_m56.PRIMARY_SYSTEM
    }
    previous_by_target: dict[str, dict[str, Any]] = {}
    artifacts = []
    for packet_row in packet["model_inputs"]:
        sample_id = packet_row["sample_id"]
        task = ours_tasks.get(sample_id)
        if task is None:
            raise ValueError(f"missing Ours task for {sample_id}")
        view = task["view"]
        source = view["source_information"]
        source_hash = view["source_information_hash"]
        if source_hash != capsule_m56.digest(source):
            raise ValueError("Ours source information hash is stale")
        projection = _project_source(source)
        fit = _fit_artifact(
            projection,
            source_hash=source_hash,
            equation_contract_hash=equation_report["contract_hash"],
            artifact_contract_hash=contract_report["contract_hash"],
            contract=contract,
        )
        state = _state_snapshot(
            projection,
            fit,
            source_hash=source_hash,
            equation_contract_hash=equation_report["contract_hash"],
            artifact_contract_hash=contract_report["contract_hash"],
        )
        previous = previous_by_target.get(state["target_id"])
        transition = _transition_trace(
            state,
            fit,
            previous,
            artifact_contract_hash=contract_report["contract_hash"],
            contract=contract,
        )
        previous_by_target[state["target_id"]] = state
        artifacts.append(
            {
                "sample_id": sample_id,
                "source_information_hash": source_hash,
                "fit_artifact": fit,
                "state_snapshot": state,
                "transition_trace": transition,
            }
        )
    bundle = {
        "schema": BUNDLE_SCHEMA,
        "version": "1.0.0",
        "status": "synthetic_engineering_artifacts_only",
        "data_kind": packet["data_kind"],
        "artifact_contract_hash": contract_report["contract_hash"],
        "equation_contract_hash": equation_report["contract_hash"],
        "prediction_packet_hash": capsule_m56.digest(packet),
        "capsule_hash": capsule["capsule_hash"],
        "sample_count": len(artifacts),
        "sample_artifacts": artifacts,
        "resource_accounting": {
            "artifact_model_calls": 0,
            "artifact_target_access_count": 0,
            "artifact_production_memory_writes": 0,
            "deterministic_local_artifact_count": len(artifacts) * 3,
        },
        "privacy": {
            "raw_current_or_history_text_persisted": False,
            "private_state_fact_created": False,
            "post_cutoff_evidence_used": False,
        },
        "authorization": {
            "formal_model_execution": False,
            "formal_scoring": False,
            "formal_claim": False,
        },
        "claim_boundary": contract["claim_boundary"],
    }
    bundle["artifact_bundle_hash"] = digest(bundle)
    return bundle


def materialize_artifact_bundle(
    packet: dict[str, Any],
    capsule: dict[str, Any],
    manifest: dict[str, Any],
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    contract_report = validate_contract(contract)
    capsule_report = capsule_m56.validate_execution_capsule(capsule, packet, manifest)
    if not contract_report["valid"]:
        raise ValueError("invalid artifact contract: " + "; ".join(contract_report["errors"]))
    if not capsule_report["valid"]:
        raise ValueError("invalid frozen M56 capsule: " + "; ".join(capsule_report["errors"]))
    if packet.get("data_kind") != temporal_m55.SYNTHETIC_KIND:
        raise PermissionError("real artifact materialization remains blocked until the human-data gate and a separately authorized real execution path")
    bundle = _materialize_bundle_unchecked(packet, capsule, contract)
    report = validate_artifact_bundle(bundle, capsule, packet, manifest, contract)
    if not report["valid"]:
        raise ValueError("materialized artifact bundle is invalid: " + "; ".join(report["errors"]))
    return bundle


def validate_artifact_bundle(
    bundle: dict[str, Any],
    capsule: dict[str, Any],
    packet: dict[str, Any],
    manifest: dict[str, Any],
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    contract_report = validate_contract(contract)
    capsule_report = capsule_m56.validate_execution_capsule(capsule, packet, manifest)
    errors = [f"contract:{error}" for error in contract_report["errors"]]
    errors += [f"capsule:{error}" for error in capsule_report["errors"]]
    forbidden = _find_forbidden_keys(bundle)
    errors.extend(f"bundle.forbidden_key:{path}" for path in forbidden)
    if not isinstance(bundle, dict):
        return {"valid": False, "errors": errors + ["bundle.object_required"]}
    if packet.get("data_kind") != temporal_m55.SYNTHETIC_KIND:
        errors.append("bundle.real_materialization_not_authorized")
    try:
        expected = _materialize_bundle_unchecked(packet, capsule, contract)
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"bundle.source_projection:{exc}")
        expected = None
    if expected is not None and bundle != expected:
        errors.append("bundle.content_or_hash_mismatch")
    rows = bundle.get("sample_artifacts") if isinstance(bundle, dict) else []
    if not isinstance(rows, list):
        rows = []
        errors.append("bundle.sample_artifacts")
    return {
        "valid": not errors,
        "errors": errors,
        "sample_count": len(rows),
        "fit_artifact_count": sum(isinstance(row.get("fit_artifact"), dict) for row in rows if isinstance(row, dict)),
        "state_snapshot_count": sum(isinstance(row.get("state_snapshot"), dict) for row in rows if isinstance(row, dict)),
        "transition_trace_count": sum(isinstance(row.get("transition_trace"), dict) for row in rows if isinstance(row, dict)),
        "forbidden_key_count": len(forbidden),
        "private_state_fabrication_count": sum(
            int(((row.get("state_snapshot") or {}).get("coverage") or {}).get("private_state_fabrication_count") or 0)
            for row in rows if isinstance(row, dict)
        ),
        "artifact_bundle_hash": bundle.get("artifact_bundle_hash") if isinstance(bundle, dict) else None,
    }


def _artifact_map(bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["sample_id"]: row for row in bundle["sample_artifacts"]}


def materialize_equation_generation_request(
    task_id: str,
    bundle: dict[str, Any],
    capsule: dict[str, Any],
    packet: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    report = validate_artifact_bundle(bundle, capsule, packet, manifest)
    if not report["valid"]:
        raise ValueError("invalid Equation artifact bundle: " + "; ".join(report["errors"]))
    task = next((row for row in capsule["prediction_tasks"] if row["task_id"] == task_id), None)
    if task is None:
        raise KeyError(f"unknown task ID: {task_id}")
    if task["condition_id"] != capsule_m56.PRIMARY_SYSTEM:
        raise PermissionError("Equation artifact payload is authorized only for Ours")
    base = capsule_m56.materialize_generation_request(task_id, capsule, packet, manifest)
    model_input = deepcopy(base["model_input"])
    required = model_input.pop("required_pre_outcome_artifacts", None)
    if required != ["fit_artifact_hash", "state_snapshot_hash", "transition_trace_hash"]:
        raise ValueError("frozen Ours request did not declare the exact three artifacts")
    artifacts = _artifact_map(bundle)[task["sample_id"]]
    model_input["pre_outcome_fit_artifact"] = deepcopy(artifacts["fit_artifact"])
    model_input["pre_outcome_state_snapshot"] = deepcopy(artifacts["state_snapshot"])
    model_input["pre_outcome_transition_trace"] = deepcopy(artifacts["transition_trace"])
    request = {
        "schema": REQUEST_SCHEMA,
        "version": "1.0.0",
        "task_id": task["task_id"],
        "sample_id": task["sample_id"],
        "condition_id": task["condition_id"],
        "source_view_hash": task["view_hash"],
        "source_information_hash": artifacts["source_information_hash"],
        "artifact_bundle_hash": bundle["artifact_bundle_hash"],
        "model_input": model_input,
        "target_access_count": 0,
        "formal_execution_authorized": False,
    }
    request["request_hash"] = digest(request)
    return request


def bind_submission_to_artifacts(
    submission: dict[str, Any],
    bundle: dict[str, Any],
    capsule: dict[str, Any],
    packet: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    base_report = capsule_m56.validate_submission(submission, capsule, packet, manifest)
    bundle_report = validate_artifact_bundle(bundle, capsule, packet, manifest)
    if not base_report["valid"]:
        raise ValueError("invalid base submission: " + "; ".join(base_report["errors"]))
    if not bundle_report["valid"]:
        raise ValueError("invalid artifact bundle: " + "; ".join(bundle_report["errors"]))
    updated = deepcopy(submission)
    artifact_map = _artifact_map(bundle)
    for row in updated["prediction_rows"]:
        if row["condition_id"] != capsule_m56.PRIMARY_SYSTEM:
            continue
        artifact_row = artifact_map[row["sample_id"]]
        row["fit_artifact_hash"] = artifact_row["fit_artifact"]["fit_artifact_hash"]
        row["state_snapshot_hash"] = artifact_row["state_snapshot"]["state_snapshot_hash"]
        row["transition_trace_hash"] = artifact_row["transition_trace"]["transition_trace_hash"]
        task_id = row["task_id"]
        request = materialize_equation_generation_request(
            task_id, bundle, capsule, packet, manifest
        )
        row["prompt_hash"] = request["request_hash"]
    updated["submission_hash"] = capsule_m56.digest(
        {key: value for key, value in updated.items() if key != "submission_hash"}
    )
    report = validate_bound_submission(updated, bundle, capsule, packet, manifest)
    if not report["valid"]:
        raise ValueError("artifact-bound submission is invalid: " + "; ".join(report["errors"]))
    return updated


def validate_bound_submission(
    submission: dict[str, Any],
    bundle: dict[str, Any],
    capsule: dict[str, Any],
    packet: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    base = capsule_m56.validate_submission(submission, capsule, packet, manifest)
    bundle_report = validate_artifact_bundle(bundle, capsule, packet, manifest)
    errors = [f"submission:{error}" for error in base["errors"]]
    errors += [f"bundle:{error}" for error in bundle_report["errors"]]
    artifact_map = _artifact_map(bundle) if bundle_report["valid"] else {}
    bound_count = 0
    for row in submission.get("prediction_rows") or []:
        condition = row.get("condition_id")
        if condition == capsule_m56.PRIMARY_SYSTEM:
            artifact_row = artifact_map.get(row.get("sample_id"))
            if not artifact_row:
                errors.append("binding.missing_sample_artifacts")
                continue
            expected_hashes = {
                "fit_artifact_hash": artifact_row["fit_artifact"]["fit_artifact_hash"],
                "state_snapshot_hash": artifact_row["state_snapshot"]["state_snapshot_hash"],
                "transition_trace_hash": artifact_row["transition_trace"]["transition_trace_hash"],
            }
            for field, expected in expected_hashes.items():
                if row.get(field) != expected:
                    errors.append(f"binding.{row.get('sample_id')}.{field}")
            try:
                request = materialize_equation_generation_request(
                    row["task_id"], bundle, capsule, packet, manifest
                )
            except (KeyError, PermissionError, ValueError) as exc:
                errors.append(f"binding.request:{exc}")
            else:
                if row.get("prompt_hash") != request["request_hash"]:
                    errors.append(f"binding.{row.get('sample_id')}.prompt_hash")
            bound_count += 1
        elif any(
            row.get(field) is not None
            for field in ("fit_artifact_hash", "state_snapshot_hash", "transition_trace_hash")
        ):
            errors.append(f"binding.non_ours_artifact_exposure:{row.get('task_id')}")
    if bound_count != packet.get("sample_count"):
        errors.append("binding.ours_row_count")
    return {
        "valid": not errors,
        "errors": errors,
        "bound_ours_row_count": bound_count,
        "artifact_bundle_hash": bundle.get("artifact_bundle_hash"),
        "base_submission_valid": base["valid"],
        "artifact_bundle_valid": bundle_report["valid"],
        "formal_execution_authorized": False,
    }


def create_equation_bound_receipt(
    submission: dict[str, Any],
    bundle: dict[str, Any],
    capsule: dict[str, Any],
    packet: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    report = validate_bound_submission(submission, bundle, capsule, packet, manifest)
    if not report["valid"]:
        raise ValueError("cannot commit unbound Equation submission: " + "; ".join(report["errors"]))
    base_receipt = capsule_m56.create_commitment_receipt(submission, capsule, packet, manifest)
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "version": "1.0.0",
        "status": "synthetic_equation_bound_commitment_only",
        "submission_hash": submission["submission_hash"],
        "artifact_bundle_hash": bundle["artifact_bundle_hash"],
        "base_m56_receipt": base_receipt,
        "target_access_count_before_commitment": 0,
        "formal_result_authorized": False,
    }
    receipt["receipt_hash"] = digest(receipt)
    return receipt


def validate_equation_bound_receipt(
    receipt: dict[str, Any],
    submission: dict[str, Any],
    bundle: dict[str, Any],
    capsule: dict[str, Any],
    packet: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    bound = validate_bound_submission(submission, bundle, capsule, packet, manifest)
    errors = [f"binding:{error}" for error in bound["errors"]]
    expected_fields = {
        "schema", "version", "status", "submission_hash", "artifact_bundle_hash",
        "base_m56_receipt", "target_access_count_before_commitment",
        "formal_result_authorized", "receipt_hash",
    }
    if not isinstance(receipt, dict) or set(receipt) != expected_fields:
        errors.append("receipt.fields")
        receipt = receipt if isinstance(receipt, dict) else {}
    if receipt.get("schema") != RECEIPT_SCHEMA or receipt.get("version") != "1.0.0":
        errors.append("receipt.schema_or_version")
    if receipt.get("status") != "synthetic_equation_bound_commitment_only":
        errors.append("receipt.status")
    if receipt.get("submission_hash") != submission.get("submission_hash"):
        errors.append("receipt.submission_hash")
    if receipt.get("artifact_bundle_hash") != bundle.get("artifact_bundle_hash"):
        errors.append("receipt.artifact_bundle_hash")
    if receipt.get("target_access_count_before_commitment") != 0:
        errors.append("receipt.target_access")
    if receipt.get("formal_result_authorized") is not False:
        errors.append("receipt.formal_authorization")
    unhashed = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    if receipt.get("receipt_hash") != digest(unhashed):
        errors.append("receipt.receipt_hash")
    base_receipt = receipt.get("base_m56_receipt")
    if not isinstance(base_receipt, dict):
        errors.append("receipt.base_m56_receipt")
    else:
        base_report = capsule_m56.validate_commitment_receipt(base_receipt, submission, capsule)
        errors.extend(f"receipt.base:{error}" for error in base_report["errors"])
    return {"valid": not errors, "errors": errors, "artifact_bundle_hash": bundle.get("artifact_bundle_hash")}


def score_equation_bound_submission(
    submission: dict[str, Any],
    receipt: dict[str, Any],
    bundle: dict[str, Any],
    capsule: dict[str, Any],
    packet: dict[str, Any],
    manifest: dict[str, Any],
    split_report: dict[str, Any],
    outcome_key: dict[str, Any],
) -> dict[str, Any]:
    receipt_report = validate_equation_bound_receipt(
        receipt, submission, bundle, capsule, packet, manifest
    )
    if not receipt_report["valid"]:
        raise ValueError("invalid Equation-bound receipt: " + "; ".join(receipt_report["errors"]))
    result = capsule_m56.score_committed_submission(
        submission,
        receipt["base_m56_receipt"],
        capsule,
        packet,
        manifest,
        split_report,
        outcome_key,
    )
    result.pop("report_hash", None)
    result["equation_artifact_audit"] = {
        "artifact_bundle_hash": bundle["artifact_bundle_hash"],
        "artifact_bundle_valid_before_score": True,
        "bound_ours_row_count": packet["sample_count"],
        "artifact_model_calls": 0,
        "artifact_target_access_count": 0,
        "private_state_fabrication_count": 0,
        "formal_artifact_claim": False,
    }
    result["report_hash"] = digest(result)
    return result


def build_demo_packet() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Build an outcome-free two-cutoff demonstration; never a scored dataset."""

    preflight_contract = preflight_m56.load_contract()
    contract_hash = preflight_m56.validate_contract(preflight_contract)["contract_hash"]
    m55_contract = temporal_m55.load_contract()
    codebook_binding = m55_contract["bindings"]["behavior_codebook"]
    labels = load_json(ROOT / codebook_binding["path"])["dialogue_act_or_action_labels"]
    target = {
        "target_id": "synthetic_equation_artifact_subject",
        "display_name": "Synthetic equation artifact subject",
        "persona_summary": "A development-only public-observable parameter placeholder.",
    }
    first_input = {
        "dataset_id": "m56-equation-artifact-demo-no-outcome",
        "sample_id": "artifact-demo-01",
        "prediction_time": "2026-01-01T00:00:10+00:00",
        "available_history_cutoff": "2026-01-01T00:00:10+00:00",
        "candidate_behavior_labels": list(labels),
        "target": deepcopy(target),
        "event_context": "A visible event is paraphrased before any completed history is available.",
        "participants": [],
        "available_history": [],
    }
    second_input = {
        "dataset_id": "m56-equation-artifact-demo-no-outcome",
        "sample_id": "artifact-demo-02",
        "prediction_time": "2026-01-02T00:00:10+00:00",
        "available_history_cutoff": "2026-01-02T00:00:10+00:00",
        "candidate_behavior_labels": list(labels),
        "target": deepcopy(target),
        "event_context": "A later visible event is paraphrased after one earlier behavior became historical.",
        "participants": [],
        "available_history": [
            {
                "history_id": "artifact-demo-history-01",
                "event_time": "2026-01-01T00:00:01+00:00",
                "available_at": "2026-01-01T00:00:18+00:00",
                "observable_summary": "A synthetic observable action became historical before the next cutoff.",
                "behavior_label": "ask_or_check",
                "evidence_type": "synthetic_engineering_only",
            }
        ],
    }
    dataset_hash = digest({"dataset_id": first_input["dataset_id"], "sample_ids": [first_input["sample_id"], second_input["sample_id"]]})
    model_inputs = []
    for model_input in (first_input, second_input):
        model_inputs.append(
            {
                "sample_id": model_input["sample_id"],
                "condition_order": preflight_m56._condition_order(model_input["sample_id"], preflight_contract),
                "model_input": model_input,
                "model_input_hash": preflight_m56.digest(model_input),
            }
        )
    packet = {
        "schema": preflight_m56.PREDICTION_PACKET_SCHEMA,
        "version": "1.0.0",
        "status": "synthetic_engineering_only",
        "data_kind": temporal_m55.SYNTHETIC_KIND,
        "contract_hash": contract_hash,
        "dataset_hash": dataset_hash,
        "sample_count": 2,
        "conditions": list(preflight_m56.CONDITION_IDS),
        "model_inputs": model_inputs,
        "data_boundary": {
            "outcome_key_available_to_generation": False,
            "post_cutoff_evidence_available": False,
            "private_mental_fact_available": False,
            "raw_or_verbatim_content_available": False,
        },
    }
    packet_report = preflight_m56.validate_prediction_packet(packet)
    if not packet_report["valid"]:
        raise ValueError("invalid demo packet: " + "; ".join(packet_report["errors"]))
    manifest = preflight_m56.build_fixture_run_manifest(packet, hardware_fingerprint="synthetic-artifact-demo")
    capsule = capsule_m56.build_execution_capsule(packet, manifest)
    return packet, manifest, capsule


def build_live_report() -> dict[str, Any]:
    packet, manifest, capsule = build_demo_packet()
    bundle = materialize_artifact_bundle(packet, capsule, manifest)
    validation = validate_artifact_bundle(bundle, capsule, packet, manifest)
    readiness = capsule_m56.build_live_report()
    samples = []
    for row in bundle["sample_artifacts"]:
        state = row["state_snapshot"]
        transition = row["transition_trace"]
        samples.append(
            {
                "sample_id": row["sample_id"],
                "history_count": row["fit_artifact"]["fit_basis"]["effective_sample_count"],
                "unknown_variable_ids": state["coverage"]["unknown_variable_ids"],
                "newly_available_history_ids": transition["observable_delta"]["newly_available_history_ids"],
                "fit_hash": row["fit_artifact"]["fit_artifact_hash"],
                "state_hash": state["state_snapshot_hash"],
                "transition_hash": transition["transition_trace_hash"],
            }
        )
    report = {
        "schema": "uruha_m56_pre_outcome_equation_artifact_live_report_v1",
        "status": "outcome_blind_artifact_engineering_ready_formal_execution_blocked",
        "contract_valid": validate_contract()["valid"],
        "artifact_bundle_valid": validation["valid"],
        "artifact_bundle_hash": bundle["artifact_bundle_hash"],
        "sample_count": validation["sample_count"],
        "artifact_count": validation["fit_artifact_count"] + validation["state_snapshot_count"] + validation["transition_trace_count"],
        "private_state_fabrication_count": validation["private_state_fabrication_count"],
        "artifact_model_calls": 0,
        "artifact_target_access_count": 0,
        "production_memory_writes": 0,
        "samples": samples,
        "counts": readiness.get("counts") or {},
        "blocking_gate": readiness.get("blocking_gate"),
        "formal_execution_authorized": False,
        "formal_result_created": False,
        "claim_boundary": load_contract()["claim_boundary"],
    }
    report["report_hash"] = digest(report)
    return report


def render_dashboard(report: dict[str, Any] | None = None) -> str:
    report = deepcopy(report or build_live_report())
    counts = report.get("counts") or {}
    slots = list(counts.get("v7_completed_slots_by_ledger") or [0, 0])
    while len(slots) < 2:
        slots.append(0)
    samples = report.get("samples") or []
    sample_cards = "".join(
        '<div class="sample"><b>{}</b><span>cutoff 前歷史：{} 筆</span><span>仍未知：{}</span><span>本輪新進歷史：{} 筆</span><code>{}… / {}… / {}…</code></div>'.format(
            html.escape(str(row.get("sample_id") or "?")),
            int(row.get("history_count") or 0),
            html.escape("、".join(row.get("unknown_variable_ids") or [])),
            len(row.get("newly_available_history_ids") or []),
            html.escape(str(row.get("fit_hash") or "")[:10]),
            html.escape(str(row.get("state_hash") or "")[:10]),
            html.escape(str(row.get("transition_hash") or "")[:10]),
        )
        for row in samples
    )
    blocker = html.escape(str(report.get("blocking_gate") or "complete_two_independent_v7_18_slot_ledgers"))
    return f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M56.1 真實方程式產物</title><style>body{{margin:0;background:#06101d;color:#edf7ff;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}main{{max-width:1320px;margin:auto;padding:28px}}section{{background:#101d31;border:1px solid #315070;border-radius:20px;padding:22px;margin:16px 0}}.hero{{background:linear-gradient(135deg,#0d3b4a,#291d49)}}h1{{font-size:34px;margin:8px 0 12px}}.sub{{color:#a8bfd5;line-height:1.6}}.flow{{display:grid;grid-template-columns:repeat(11,minmax(70px,1fr));gap:8px;align-items:center}}.node{{background:#071729;border:1px solid #3f6384;border-radius:14px;padding:15px 8px;text-align:center;min-height:74px;display:flex;align-items:center;justify-content:center;flex-direction:column}}.arrow{{text-align:center;color:#69e1c3;font-size:23px}}.same{{border-color:#5bd8ff}}.fit{{border-color:#8bdb7d}}.state{{border-color:#c9a7ff}}.transition{{border-color:#ffb55f}}.commit{{border-color:#ff789c}}.samples{{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}}.sample{{background:#081629;border-radius:14px;padding:17px;border:1px solid #355776}}.sample b,.sample span,.sample code{{display:block}}.sample span{{margin-top:8px;color:#afc2d6}}.sample code{{margin-top:12px;color:#67e2c5;font-size:12px}}.checks{{display:grid;grid-template-columns:repeat(5,1fr);gap:9px}}.check{{background:#09182a;border-radius:12px;padding:14px;border:1px solid #304d70}}.good{{color:#69e1c3;font-weight:800}}.warn{{color:#ff93ab;font-weight:800}}@media(max-width:980px){{.flow,.checks,.samples{{grid-template-columns:1fr}}.arrow{{transform:rotate(90deg)}}}}</style></head><body><main><section class="hero"><small>M56.1 · PRE-OUTCOME EQUATION ARTIFACTS</small><h1>不再只放三串雜湊：方程式真的先形成可檢查的內部狀態</h1><p class="sub">B5 與 Ours 先拿到完全相同的 cutoff 前資料；只有 Ours 再把它變成可回驗的 fit、九變數 state 與跨輪 transition。答案仍封住，之後的模型輸出與分數都不能反過來修改它。</p><p class="good">產物 {int(report.get('artifact_count') or 0)} 個 · bundle PASS：{'是' if report.get('artifact_bundle_valid') else '否'} · 私人心理捏造 {int(report.get('private_state_fabrication_count') or 0)}</p></section><section><h2>資料怎麼流</h2><div class="flow"><div class="node same"><b>B5 / Ours</b><small>同一份來源</small></div><div class="arrow">→</div><div class="node fit"><b>Fit</b><small>只看已完成歷史</small></div><div class="arrow">→</div><div class="node state"><b>State</b><small>9 變數，未知留白</small></div><div class="arrow">→</div><div class="node transition"><b>Transition</b><small>只記可觀察變化</small></div><div class="arrow">→</div><div class="node"><b>Ours 一次呼叫</b><small>產物隨請求送入</small></div><div class="arrow">→</div><div class="node commit"><b>SHA 封存</b><small>再解鎖計分</small></div></div></section><section><h2>兩個 cutoff 的真實產物變化</h2><div class="samples">{sample_cards}</div><p class="sub">第一個 cutoff 沒有歷史，所以 fit 樣本數是 0；第二個 cutoff 才能使用第一個已完成行為。S（瞬時心理）、R（關係）與 N（需求）沒有可靠來源，兩輪都保持 unknown。</p></section><section><h2>會直接失敗的路徑</h2><div class="checks"><div class="check">用當前答案回填 fit</div><div class="check">history 晚於 cutoff</div><div class="check">內容改了但雜湊沒改</div><div class="check">把假 aaaa 雜湊當產物</div><div class="check">讓 B5 偷看 Equation state</div></div></section><section><h2>目前研究邊界</h2><p><span class="good">已完成：</span>三個 Ours 產物可重建、可追溯、可隨 submission 一起封存，而且產物建立新增模型呼叫為 0。</p><p class="warn">仍未完成：</p><p>V7 {slots[0]}/18 + {slots[1]}/18；real rows {counts.get('temporally_valid_prediction_row_count',0)}/30；正式模型呼叫 0；正式結果不存在。</p><p>阻擋點：{blocker}</p><p class="sub">這證明工程上真的有 Equation artifact，不證明它就是人類思考、能預測一ノ瀬うるは，或勝過一般 LLM。</p></section></main></body></html>'''


def serve_demo(port: int) -> None:
    page = render_dashboard().encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
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
    parser.add_argument("--format", choices=("contract", "report", "bundle", "html"), default="report")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--port", type=int, default=7909)
    args = parser.parse_args()
    if args.serve:
        serve_demo(args.port)
        return
    if args.format == "contract":
        payload = validate_contract()
    elif args.format == "bundle":
        packet, manifest, capsule = build_demo_packet()
        payload = materialize_artifact_bundle(packet, capsule, manifest)
    elif args.format == "html":
        print(render_dashboard())
        return
    else:
        payload = build_live_report()
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
