#!/usr/bin/env python3
"""M56 capability-separated execution capsule and independent scorer.

The module turns an already validated M56 prediction packet into seven
condition-specific views.  It validates a complete prediction submission,
commits that submission before any outcome access, and joins the separately
withheld outcome key only inside the scoring function.  The built-in fixture
path is synthetic engineering QA only and never authorizes a formal claim.
"""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import random
import re
from typing import Any

import m55_temporal_row_contract as temporal_m55
import m56_fair_comparison_preflight as preflight_m56
from longitudinal_human_model.metrics import evaluate_predictions
from longitudinal_human_model.statistical_evaluation import (
    exact_mcnemar_pvalue,
    exact_sign_flip_pvalue,
    percentile_bootstrap_ci,
    probability_losses,
)


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/m56_blinded_execution_capsule_v1.json"
CAPSULE_SCHEMA = "uruha_m56_blinded_execution_capsule_v1"
SUMMARY_SCHEMA = "uruha_m56_b4_summary_artifact_v1"
SUBMISSION_SCHEMA = "uruha_m56_prediction_submission_v1"
RECEIPT_SCHEMA = "uruha_m56_prediction_commitment_receipt_v1"
SCORE_SCHEMA = "uruha_m56_separate_score_report_v1"
GENERATION_REQUEST_SCHEMA = "uruha_m56_isolated_generation_request_v1"
CONDITION_IDS = preflight_m56.CONDITION_IDS
MODEL_CONDITIONS = preflight_m56.MODEL_CONDITIONS
PRIMARY_CONTROL = preflight_m56.PRIMARY_CONTROL
PRIMARY_SYSTEM = preflight_m56.PRIMARY_SYSTEM

COMMON_VIEW_KEYS = {
    "sample_id",
    "prediction_time",
    "available_history_cutoff",
    "candidate_behavior_labels",
}
OUTCOME_KEYS = preflight_m56.FORBIDDEN_PACKET_KEYS | {
    "outcomes",
    "actual",
    "ground_truth",
    "score",
    "scores",
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
            location = f"{prefix}.{key}" if prefix else str(key)
            if key in forbidden:
                found.append(location)
            found.extend(_find_keys(child, forbidden, location))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_find_keys(child, forbidden, f"{prefix}[{index}]"))
    return found


def validate_contract(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors: list[str] = []
    if contract.get("schema") != "uruha_m56_blinded_execution_capsule_contract_v1":
        errors.append("schema")
    if contract.get("version") != "1.0.0":
        errors.append("version")
    if contract.get("status") != "frozen_before_real_m55_rows_m56_generation_or_target_outcome_access":
        errors.append("status")
    bindings = contract.get("bindings")
    if not isinstance(bindings, dict) or len(bindings) != 9:
        errors.append("bindings")
    else:
        for name, binding in bindings.items():
            if not _binding_valid(binding):
                errors.append(f"binding:{name}")
    expected_schemas = {
        "execution_capsule": CAPSULE_SCHEMA,
        "summary_artifact": SUMMARY_SCHEMA,
        "prediction_submission": SUBMISSION_SCHEMA,
        "commitment_receipt": RECEIPT_SCHEMA,
        "score_report": SCORE_SCHEMA,
    }
    if contract.get("schemas") != expected_schemas:
        errors.append("schemas")
    views = contract.get("condition_views") or {}
    if tuple(views) != CONDITION_IDS:
        errors.append("condition_views")
    invariants = contract.get("view_invariants") or {}
    for key in (
        "all_views_cutoff_bound",
        "outcome_fields_forbidden",
        "B5_and_Ours_source_information_hash_equal",
        "B5_must_not_receive_equation_state_or_transition",
        "Ours_requires_pre_outcome_fit_artifact_hash",
        "Ours_requires_state_snapshot_and_transition_trace_hashes",
    ):
        if invariants.get(key) is not True:
            errors.append(f"invariant:{key}")
    if invariants.get("B1_and_B2_history_count_required") != 0:
        errors.append("invariant:B1_B2_history")
    if invariants.get("B3_history_limit") != 4:
        errors.append("invariant:B3_limit")
    if invariants.get("B4_prediction_view_contains_raw_history") is not False:
        errors.append("invariant:B4_raw_history")
    ordering = contract.get("ordering_and_commitment") or {}
    if ordering.get("task_order") != "packet_sample_order_then_sample_specific_condition_order":
        errors.append("task_order")
    for key in (
        "every_sample_condition_pair_required",
        "missing_or_duplicate_row_invalidates_submission",
        "probability_labels_exact",
        "selected_behavior_must_equal_frozen_argmax",
        "outcome_key_access_before_commitment_forbidden",
        "commitment_receipt_created_before_scoring",
        "submission_change_after_commitment_invalidates_scoring",
    ):
        if ordering.get(key) is not True:
            errors.append(f"ordering:{key}")
    if ordering.get("probability_sum_tolerance") != 0.000001:
        errors.append("probability_tolerance")
    resources = contract.get("resource_execution") or {}
    if resources.get("B0_prediction_model_calls_per_sample") != 0:
        errors.append("B0_call_count")
    if resources.get("B1_B2_B3_B4_B5_prediction_model_calls_per_sample") != 1:
        errors.append("B1_B5_call_count")
    if resources.get("Ours_semantic_model_calls_per_sample") != 1:
        errors.append("Ours_call_count")
    if resources.get("retry_count_required") != 0 or resources.get("fallback_count_required") != 0:
        errors.append("retry_fallback")
    scoring = contract.get("scoring") or {}
    if scoring.get("bootstrap_repetitions") != 20000 or scoring.get("bootstrap_seed") != 560901:
        errors.append("bootstrap")
    if scoring.get("sign_flip_exact_pair_limit") != 20:
        errors.append("sign_flip_limit")
    if scoring.get("sign_flip_monte_carlo_draws") != 20000 or scoring.get("sign_flip_seed") != 560902:
        errors.append("sign_flip_monte_carlo")
    authorization = contract.get("authorization") or {}
    if not authorization or any(value is not False for value in authorization.values()):
        errors.append("authorization")
    return {
        "valid": not errors,
        "errors": errors,
        "contract_hash": digest(contract),
        "binding_count": len(bindings or {}),
        "condition_count": len(views),
    }


def _lexical_tokens(text: str) -> set[str]:
    return set(re.findall(r"[\w\u3040-\u30ff\u3400-\u9fff]+", text.lower()))


def _retrieve_history(model_input: dict[str, Any], top_n: int = 4) -> list[dict[str, Any]]:
    query = _lexical_tokens(str(model_input["event_context"]))
    ranked = []
    for item in model_input["available_history"]:
        tokens = _lexical_tokens(str(item["observable_summary"]))
        union = query | tokens
        similarity = len(query & tokens) / len(union) if union else 0.0
        ranked.append((similarity, item["available_at"], item["history_id"], item))
    ranked.sort(key=lambda row: (-row[0], row[1], row[2]))
    return [deepcopy(item) for _, _, _, item in ranked[:top_n]]


def _history_counts(model_input: dict[str, Any]) -> dict[str, int]:
    counts = Counter(item["behavior_label"] for item in model_input["available_history"])
    return {label: int(counts[label]) for label in model_input["candidate_behavior_labels"]}


def _minimal_identity(model_input: dict[str, Any]) -> dict[str, Any]:
    target = model_input.get("target") or {}
    return {"target_id": target.get("target_id"), "display_name": target.get("display_name")}


def _persona_summary(model_input: dict[str, Any]) -> Any:
    target = model_input.get("target") or {}
    return deepcopy(target.get("persona_summary"))


def _common(model_input: dict[str, Any]) -> dict[str, Any]:
    return {
        "sample_id": model_input["sample_id"],
        "prediction_time": model_input["prediction_time"],
        "available_history_cutoff": model_input["available_history_cutoff"],
        "candidate_behavior_labels": deepcopy(model_input["candidate_behavior_labels"]),
    }


def _source_information(model_input: dict[str, Any]) -> dict[str, Any]:
    source = _common(model_input)
    source.update(
        {
            "current_pre_cutoff_event": deepcopy(model_input["event_context"]),
            "participants": deepcopy(model_input["participants"]),
            "target": deepcopy(model_input["target"]),
            "all_pre_cutoff_history": deepcopy(model_input["available_history"]),
        }
    )
    return source


def _summary_task_id(history_signature: str) -> str:
    return "m56-b4-summary::" + history_signature[:16]


def _prediction_task_id(sample_id: str, condition_id: str) -> str:
    return f"m56-predict::{sample_id}::{condition_id}"


def build_execution_capsule(
    packet: dict[str, Any], manifest: dict[str, Any], contract: dict[str, Any] | None = None
) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    contract_report = validate_contract(contract)
    packet_report = preflight_m56.validate_prediction_packet(packet)
    manifest_report = preflight_m56.validate_run_manifest(manifest, packet)
    errors = contract_report["errors"] + packet_report["errors"] + manifest_report["errors"]
    if errors:
        raise ValueError("invalid M56 inputs: " + "; ".join(errors))
    if packet.get("data_kind") != temporal_m55.SYNTHETIC_KIND:
        raise PermissionError("real execution capsule remains blocked until M55 and formal authorization")

    summaries: list[dict[str, Any]] = []
    summary_by_signature: dict[str, dict[str, Any]] = {}
    tasks: list[dict[str, Any]] = []
    for packet_row in packet["model_inputs"]:
        model_input = packet_row["model_input"]
        history = deepcopy(model_input["available_history"])
        history_signature = digest(history)
        if history_signature not in summary_by_signature:
            empty = not history
            summary_task = {
                "summary_task_id": _summary_task_id(history_signature),
                "history_signature": history_signature,
                "source_history": history,
                "source_history_ids": [item["history_id"] for item in history],
                "model_call_required": not empty,
                "empty_history_artifact": empty,
            }
            summary_task["summary_view_hash"] = digest(summary_task)
            summary_by_signature[history_signature] = summary_task
            summaries.append(summary_task)

        common = _common(model_input)
        source = _source_information(model_input)
        source_hash = digest(source)
        for condition_id in packet_row["condition_order"]:
            view = deepcopy(common)
            if condition_id == "B0_PRIOR":
                view["pre_cutoff_historical_behavior_counts"] = _history_counts(model_input)
            elif condition_id == "B1_BASE_LLM":
                view.update(
                    current_pre_cutoff_event=deepcopy(model_input["event_context"]),
                    minimal_target_identity=_minimal_identity(model_input),
                )
            elif condition_id == "B2_PERSONA_PROMPT":
                view.update(
                    current_pre_cutoff_event=deepcopy(model_input["event_context"]),
                    minimal_target_identity=_minimal_identity(model_input),
                    frozen_pre_target_persona_summary=_persona_summary(model_input),
                )
            elif condition_id == "B3_RAG":
                view.update(
                    current_pre_cutoff_event=deepcopy(model_input["event_context"]),
                    minimal_target_identity=_minimal_identity(model_input),
                    frozen_pre_target_persona_summary=_persona_summary(model_input),
                    deterministic_top4_pre_cutoff_history=_retrieve_history(model_input),
                )
            elif condition_id == "B4_FULL_HISTORY_SUMMARY":
                view.update(
                    current_pre_cutoff_event=deepcopy(model_input["event_context"]),
                    minimal_target_identity=_minimal_identity(model_input),
                    summary_task_id=summary_by_signature[history_signature]["summary_task_id"],
                    summary_artifact_hash_required=True,
                )
            elif condition_id == "B5_STRUCTURED_HISTORY":
                view["source_information"] = deepcopy(source)
                view["source_information_hash"] = source_hash
            elif condition_id == "OURS_HYBRID":
                view["source_information"] = deepcopy(source)
                view["source_information_hash"] = source_hash
                view["equation_definition_binding"] = deepcopy(
                    contract["bindings"]["equation_v1_contract"]
                )
                view["required_pre_outcome_artifacts"] = [
                    "fit_artifact_hash",
                    "state_snapshot_hash",
                    "transition_trace_hash",
                ]
            else:
                raise ValueError(f"unsupported condition {condition_id}")
            task = {
                "task_id": _prediction_task_id(model_input["sample_id"], condition_id),
                "sample_id": model_input["sample_id"],
                "condition_id": condition_id,
                "source_model_input_hash": packet_row["model_input_hash"],
                "view": view,
            }
            task["view_hash"] = digest(view)
            tasks.append(task)

    capsule = {
        "schema": CAPSULE_SCHEMA,
        "version": "1.0.0",
        "status": "synthetic_engineering_capsule_only",
        "data_kind": packet["data_kind"],
        "contract_hash": contract_report["contract_hash"],
        "preflight_contract_hash": preflight_m56.validate_contract()["contract_hash"],
        "dataset_hash": packet["dataset_hash"],
        "prediction_packet_hash": digest(packet),
        "run_manifest_hash": digest(manifest),
        "sample_count": packet["sample_count"],
        "condition_count": len(CONDITION_IDS),
        "summary_tasks": summaries,
        "prediction_tasks": tasks,
        "outcome_access_count": 0,
        "model_call_count": 0,
        "formal_execution_authorized": False,
    }
    capsule["capsule_hash"] = digest(capsule)
    report = validate_execution_capsule(capsule, packet, manifest, contract)
    if not report["valid"]:
        raise ValueError("invalid execution capsule: " + "; ".join(report["errors"]))
    return capsule


def _expected_view_keys(condition_id: str) -> set[str]:
    extras = {
        "B0_PRIOR": {"pre_cutoff_historical_behavior_counts"},
        "B1_BASE_LLM": {"current_pre_cutoff_event", "minimal_target_identity"},
        "B2_PERSONA_PROMPT": {
            "current_pre_cutoff_event",
            "minimal_target_identity",
            "frozen_pre_target_persona_summary",
        },
        "B3_RAG": {
            "current_pre_cutoff_event",
            "minimal_target_identity",
            "frozen_pre_target_persona_summary",
            "deterministic_top4_pre_cutoff_history",
        },
        "B4_FULL_HISTORY_SUMMARY": {
            "current_pre_cutoff_event",
            "minimal_target_identity",
            "summary_task_id",
            "summary_artifact_hash_required",
        },
        "B5_STRUCTURED_HISTORY": {"source_information", "source_information_hash"},
        "OURS_HYBRID": {
            "source_information",
            "source_information_hash",
            "equation_definition_binding",
            "required_pre_outcome_artifacts",
        },
    }
    return COMMON_VIEW_KEYS | extras[condition_id]


def validate_execution_capsule(
    capsule: dict[str, Any],
    packet: dict[str, Any],
    manifest: dict[str, Any],
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    contract_report = validate_contract(contract)
    packet_report = preflight_m56.validate_prediction_packet(packet)
    manifest_report = preflight_m56.validate_run_manifest(manifest, packet)
    errors = [f"contract:{e}" for e in contract_report["errors"]]
    errors += [f"packet:{e}" for e in packet_report["errors"]]
    errors += [f"manifest:{e}" for e in manifest_report["errors"]]
    if not isinstance(capsule, dict):
        return {"valid": False, "errors": errors + ["capsule:object_required"]}
    expected_fields = {
        "schema", "version", "status", "data_kind", "contract_hash",
        "preflight_contract_hash", "dataset_hash", "prediction_packet_hash",
        "run_manifest_hash", "sample_count", "condition_count", "summary_tasks",
        "prediction_tasks", "outcome_access_count", "model_call_count",
        "formal_execution_authorized", "capsule_hash",
    }
    if set(capsule) != expected_fields:
        errors.append("capsule.fields")
    if capsule.get("schema") != CAPSULE_SCHEMA or capsule.get("version") != "1.0.0":
        errors.append("capsule.schema_or_version")
    if capsule.get("status") != "synthetic_engineering_capsule_only":
        errors.append("capsule.status")
    if capsule.get("data_kind") != packet.get("data_kind"):
        errors.append("capsule.data_kind")
    if capsule.get("contract_hash") != contract_report["contract_hash"]:
        errors.append("capsule.contract_hash")
    if capsule.get("preflight_contract_hash") != preflight_m56.validate_contract()["contract_hash"]:
        errors.append("capsule.preflight_contract_hash")
    if capsule.get("dataset_hash") != packet.get("dataset_hash"):
        errors.append("capsule.dataset_hash")
    if capsule.get("prediction_packet_hash") != digest(packet):
        errors.append("capsule.prediction_packet_hash")
    if capsule.get("run_manifest_hash") != digest(manifest):
        errors.append("capsule.run_manifest_hash")
    unhashed = {key: value for key, value in capsule.items() if key != "capsule_hash"}
    if capsule.get("capsule_hash") != digest(unhashed):
        errors.append("capsule.capsule_hash")
    if capsule.get("outcome_access_count") != 0 or capsule.get("model_call_count") != 0:
        errors.append("capsule.execution_or_outcome_access")
    if capsule.get("formal_execution_authorized") is not False:
        errors.append("capsule.formal_authorization")
    forbidden = _find_keys(capsule, OUTCOME_KEYS)
    errors.extend(f"capsule.forbidden_key:{path}" for path in forbidden)

    summaries = capsule.get("summary_tasks")
    if not isinstance(summaries, list):
        summaries = []
        errors.append("capsule.summary_tasks")
    summary_map: dict[str, dict[str, Any]] = {}
    for index, summary in enumerate(summaries):
        scope = f"capsule.summary_tasks[{index}]"
        if not isinstance(summary, dict):
            errors.append(f"{scope}:object_required")
            continue
        if set(summary) != {
            "summary_task_id", "history_signature", "source_history",
            "source_history_ids", "model_call_required", "empty_history_artifact",
            "summary_view_hash",
        }:
            errors.append(f"{scope}.fields")
        sid = str(summary.get("summary_task_id") or "")
        if not sid or sid in summary_map:
            errors.append(f"{scope}.summary_task_id")
        summary_map[sid] = summary
        history = summary.get("source_history")
        if not isinstance(history, list):
            errors.append(f"{scope}.source_history")
            history = []
        if summary.get("history_signature") != digest(history):
            errors.append(f"{scope}.history_signature")
        if summary.get("source_history_ids") != [item.get("history_id") for item in history]:
            errors.append(f"{scope}.source_history_ids")
        empty = len(history) == 0
        if summary.get("model_call_required") is not (not empty):
            errors.append(f"{scope}.model_call_required")
        if summary.get("empty_history_artifact") is not empty:
            errors.append(f"{scope}.empty_history_artifact")
        unhashed_summary = {key: value for key, value in summary.items() if key != "summary_view_hash"}
        if summary.get("summary_view_hash") != digest(unhashed_summary):
            errors.append(f"{scope}.summary_view_hash")

    expected_pairs = [
        (row["sample_id"], condition)
        for row in packet.get("model_inputs") or []
        for condition in row["condition_order"]
    ]
    tasks = capsule.get("prediction_tasks")
    if not isinstance(tasks, list):
        tasks = []
        errors.append("capsule.prediction_tasks")
    actual_pairs = [
        (task.get("sample_id"), task.get("condition_id"))
        for task in tasks if isinstance(task, dict)
    ]
    if actual_pairs != expected_pairs:
        errors.append("capsule.task_order_or_matrix")
    if len(actual_pairs) != len(set(actual_pairs)):
        errors.append("capsule.duplicate_task")
    packet_map = {row["sample_id"]: row for row in packet.get("model_inputs") or []}
    primary_hashes: dict[str, dict[str, str]] = {}
    for index, task in enumerate(tasks):
        scope = f"capsule.prediction_tasks[{index}]"
        if not isinstance(task, dict):
            errors.append(f"{scope}:object_required")
            continue
        if set(task) != {
            "task_id", "sample_id", "condition_id", "source_model_input_hash",
            "view", "view_hash",
        }:
            errors.append(f"{scope}.fields")
        sample_id = str(task.get("sample_id") or "")
        condition = str(task.get("condition_id") or "")
        expected_task_id = _prediction_task_id(sample_id, condition) if condition in CONDITION_IDS else ""
        if task.get("task_id") != expected_task_id:
            errors.append(f"{scope}.task_id")
        packet_row = packet_map.get(sample_id)
        if not packet_row or task.get("source_model_input_hash") != packet_row.get("model_input_hash"):
            errors.append(f"{scope}.source_model_input_hash")
        view = task.get("view")
        if not isinstance(view, dict) or condition not in CONDITION_IDS:
            errors.append(f"{scope}.view")
            continue
        if set(view) != _expected_view_keys(condition):
            errors.append(f"{scope}.view_fields")
        if task.get("view_hash") != digest(view):
            errors.append(f"{scope}.view_hash")
        if view.get("sample_id") != sample_id:
            errors.append(f"{scope}.view_sample_id")
        if _find_keys(view, OUTCOME_KEYS):
            errors.append(f"{scope}.outcome_leak")
        if condition in ("B1_BASE_LLM", "B2_PERSONA_PROMPT"):
            if any(
                key in view
                for key in (
                    "available_history",
                    "all_pre_cutoff_history",
                    "source_history",
                    "deterministic_top4_pre_cutoff_history",
                    "pre_cutoff_historical_behavior_counts",
                    "summary_task_id",
                )
            ):
                errors.append(f"{scope}.history_leak")
        if condition == "B3_RAG" and len(view.get("deterministic_top4_pre_cutoff_history") or []) > 4:
            errors.append(f"{scope}.rag_limit")
        if condition == "B4_FULL_HISTORY_SUMMARY":
            summary = summary_map.get(str(view.get("summary_task_id") or ""))
            if not summary or view.get("summary_artifact_hash_required") is not True:
                errors.append(f"{scope}.summary_reference")
            if any(key in view for key in ("available_history", "all_pre_cutoff_history", "source_history")):
                errors.append(f"{scope}.raw_history")
        if condition in (PRIMARY_CONTROL, PRIMARY_SYSTEM):
            source = view.get("source_information")
            source_hash = str(view.get("source_information_hash") or "")
            if not isinstance(source, dict) or source_hash != digest(source):
                errors.append(f"{scope}.source_information_hash")
            primary_hashes.setdefault(sample_id, {})[condition] = source_hash
        if condition == PRIMARY_CONTROL:
            if any(key in view for key in ("equation_definition_binding", "required_pre_outcome_artifacts")):
                errors.append(f"{scope}.equation_leak")
        if condition == PRIMARY_SYSTEM:
            required = view.get("required_pre_outcome_artifacts")
            if required != ["fit_artifact_hash", "state_snapshot_hash", "transition_trace_hash"]:
                errors.append(f"{scope}.required_artifacts")
    for sample_id, hashes in primary_hashes.items():
        if hashes.get(PRIMARY_CONTROL) != hashes.get(PRIMARY_SYSTEM):
            errors.append(f"capsule.primary_source_hash_mismatch:{sample_id}")
    if capsule.get("sample_count") != len(packet.get("model_inputs") or []):
        errors.append("capsule.sample_count")
    if capsule.get("condition_count") != len(CONDITION_IDS):
        errors.append("capsule.condition_count")
    return {
        "valid": not errors,
        "errors": errors,
        "task_count": len(tasks),
        "summary_task_count": len(summaries),
        "forbidden_key_count": len(forbidden),
        "capsule_hash": digest(capsule),
    }


def materialize_generation_request(
    task_id: str,
    capsule: dict[str, Any],
    packet: dict[str, Any],
    manifest: dict[str, Any],
    *,
    summary_artifacts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return only one task's authorized view for a future model call."""

    report = validate_execution_capsule(capsule, packet, manifest)
    if not report["valid"]:
        raise ValueError("invalid capsule: " + "; ".join(report["errors"]))
    task = next((row for row in capsule["prediction_tasks"] if row["task_id"] == task_id), None)
    if task is None:
        raise KeyError(f"unknown task_id: {task_id}")
    if task["condition_id"] == "B0_PRIOR":
        raise ValueError("B0 is deterministic and must not create a model request")
    isolated_view = deepcopy(task["view"])
    if task["condition_id"] == "B4_FULL_HISTORY_SUMMARY":
        artifacts = {
            row.get("summary_task_id"): row
            for row in (summary_artifacts or [])
            if isinstance(row, dict)
        }
        summary_task_id = str(isolated_view.pop("summary_task_id"))
        isolated_view.pop("summary_artifact_hash_required", None)
        artifact = artifacts.get(summary_task_id)
        if artifact is None:
            raise ValueError("B4 generation requires its completed summary artifact")
        summary_task = next(
            row for row in capsule["summary_tasks"]
            if row["summary_task_id"] == summary_task_id
        )
        unhashed = {key: value for key, value in artifact.items() if key != "summary_artifact_hash"}
        if (
            artifact.get("schema") != SUMMARY_SCHEMA
            or artifact.get("summary_view_hash") != summary_task["summary_view_hash"]
            or artifact.get("source_history_ids") != summary_task["source_history_ids"]
            or artifact.get("summary_artifact_hash") != digest(unhashed)
        ):
            raise ValueError("B4 summary artifact is invalid or stale")
        isolated_view["frozen_model_summary_artifact"] = {
            "summary_text": artifact.get("summary_text"),
            "summary_artifact_hash": artifact["summary_artifact_hash"],
        }
    request = {
        "schema": GENERATION_REQUEST_SCHEMA,
        "task_id": task["task_id"],
        "sample_id": task["sample_id"],
        "condition_id": task["condition_id"],
        "source_view_hash": task["view_hash"],
        "model_input": isolated_view,
    }
    request["request_hash"] = digest(request)
    return request


def _argmax(probabilities: dict[str, float], labels: list[str]) -> str:
    return max(labels, key=lambda label: (probabilities[label], -labels.index(label)))


def _fixture_distribution(labels: list[str], sample_index: int, condition_index: int) -> dict[str, float]:
    weights = [1.0 + ((sample_index + 2 * condition_index + index) % len(labels)) for index in range(len(labels))]
    total = sum(weights)
    return {label: weight / total for label, weight in zip(labels, weights)}


def build_synthetic_fixture_submission(
    capsule: dict[str, Any], packet: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, Any]:
    capsule_report = validate_execution_capsule(capsule, packet, manifest)
    if not capsule_report["valid"]:
        raise ValueError("invalid capsule: " + "; ".join(capsule_report["errors"]))
    if capsule.get("data_kind") != temporal_m55.SYNTHETIC_KIND:
        raise PermissionError("fixture submission accepts synthetic engineering data only")
    run_map = {row["condition_id"]: row for row in manifest["condition_runs"]}
    sample_order = {row["sample_id"]: index for index, row in enumerate(packet["model_inputs"])}
    summary_artifacts = []
    for task in capsule["summary_tasks"]:
        empty = task["empty_history_artifact"]
        artifact = {
            "schema": SUMMARY_SCHEMA,
            "summary_task_id": task["summary_task_id"],
            "summary_view_hash": task["summary_view_hash"],
            "summary_text": "No pre-cutoff history available." if empty else "Synthetic pre-cutoff history summary.",
            "source_history_ids": deepcopy(task["source_history_ids"]),
            "model_call_count": 0 if empty else 1,
            "prompt_tokens": 0 if empty else 32 + len(task["source_history_ids"]),
            "completion_tokens": 0 if empty else 8,
            "latency_seconds": 0.0 if empty else 0.01,
            "peak_memory_bytes": 0 if empty else 1024,
            "retry_count": 0,
            "fallback_count": 0,
            "model_name": "deterministic_no_history" if empty else run_map["B4_FULL_HISTORY_SUMMARY"]["model_name"],
            "model_artifact_digest": "deterministic_no_history" if empty else run_map["B4_FULL_HISTORY_SUMMARY"]["model_artifact_digest"],
            "hardware_fingerprint": run_map["B4_FULL_HISTORY_SUMMARY"]["hardware_fingerprint"],
            "provider_options": {} if empty else deepcopy(run_map["B4_FULL_HISTORY_SUMMARY"]["provider_options"]),
        }
        artifact["summary_artifact_hash"] = digest(artifact)
        summary_artifacts.append(artifact)
    summary_map = {row["summary_task_id"]: row for row in summary_artifacts}

    rows = []
    for task in capsule["prediction_tasks"]:
        condition = task["condition_id"]
        labels = task["view"]["candidate_behavior_labels"]
        if condition == "B0_PRIOR":
            counts = task["view"]["pre_cutoff_historical_behavior_counts"]
            weights = {label: counts[label] + 1.0 for label in labels}
            total = sum(weights.values())
            probabilities = {label: weights[label] / total for label in labels}
        else:
            probabilities = _fixture_distribution(
                labels, sample_order[task["sample_id"]], CONDITION_IDS.index(condition)
            )
        model_used = condition != "B0_PRIOR"
        run = run_map[condition]
        row = {
            "task_id": task["task_id"],
            "sample_id": task["sample_id"],
            "condition_id": condition,
            "view_hash": task["view_hash"],
            "probabilities": probabilities,
            "selected_behavior": _argmax(probabilities, labels),
            "authorized_evidence_ids": [],
            "brief_evidence": "Synthetic execution-capsule validation fixture.",
            "prompt_hash": None if not model_used else digest({"view": task["view"], "fixture": True}),
            "prompt_tokens": 0 if not model_used else 64 + CONDITION_IDS.index(condition),
            "completion_tokens": 0 if not model_used else 12,
            "latency_seconds": 0.0 if not model_used else 0.02,
            "peak_memory_bytes": 0 if not model_used else 2048,
            "prediction_model_call_count": 0 if (not model_used or condition == PRIMARY_SYSTEM) else 1,
            "semantic_model_call_count": 1 if condition == PRIMARY_SYSTEM else 0,
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
        if condition == "B4_FULL_HISTORY_SUMMARY":
            row["b4_summary_artifact_hash"] = summary_map[task["view"]["summary_task_id"]]["summary_artifact_hash"]
        if condition == PRIMARY_SYSTEM:
            row["fit_artifact_hash"] = "a" * 64
            row["state_snapshot_hash"] = "b" * 64
            row["transition_trace_hash"] = "c" * 64
        rows.append(row)
    submission = {
        "schema": SUBMISSION_SCHEMA,
        "version": "1.0.0",
        "status": "synthetic_engineering_submission_only",
        "data_kind": capsule["data_kind"],
        "contract_hash": capsule["contract_hash"],
        "capsule_hash": capsule["capsule_hash"],
        "prediction_packet_hash": capsule["prediction_packet_hash"],
        "run_manifest_hash": capsule["run_manifest_hash"],
        "summary_artifacts": summary_artifacts,
        "prediction_rows": rows,
        "outcome_access_count_before_commitment": 0,
        "formal_result_authorized": False,
    }
    submission["submission_hash"] = digest(submission)
    report = validate_submission(submission, capsule, packet, manifest)
    if not report["valid"]:
        raise ValueError("invalid synthetic submission: " + "; ".join(report["errors"]))
    return submission


def _authorized_history_ids(task: dict[str, Any], summary_artifacts: dict[str, dict[str, Any]]) -> set[str]:
    condition = task["condition_id"]
    view = task["view"]
    if condition == "B3_RAG":
        return {row["history_id"] for row in view["deterministic_top4_pre_cutoff_history"]}
    if condition == "B4_FULL_HISTORY_SUMMARY":
        summary = summary_artifacts.get(str(view.get("summary_task_id") or "")) or {}
        return set(summary.get("source_history_ids") or [])
    if condition in (PRIMARY_CONTROL, PRIMARY_SYSTEM):
        source = view.get("source_information") or {}
        return {row["history_id"] for row in source.get("all_pre_cutoff_history") or []}
    return set()


def validate_submission(
    submission: dict[str, Any],
    capsule: dict[str, Any],
    packet: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    capsule_report = validate_execution_capsule(capsule, packet, manifest)
    errors = [f"capsule:{e}" for e in capsule_report["errors"]]
    if not isinstance(submission, dict):
        return {"valid": False, "errors": errors + ["submission:object_required"]}
    expected_fields = {
        "schema", "version", "status", "data_kind", "contract_hash", "capsule_hash",
        "prediction_packet_hash", "run_manifest_hash", "summary_artifacts",
        "prediction_rows", "outcome_access_count_before_commitment",
        "formal_result_authorized", "submission_hash",
    }
    if set(submission) != expected_fields:
        errors.append("submission.fields")
    if submission.get("schema") != SUBMISSION_SCHEMA or submission.get("version") != "1.0.0":
        errors.append("submission.schema_or_version")
    if submission.get("status") != "synthetic_engineering_submission_only":
        errors.append("submission.status")
    for field, expected in (
        ("data_kind", capsule.get("data_kind")),
        ("contract_hash", capsule.get("contract_hash")),
        ("capsule_hash", capsule.get("capsule_hash")),
        ("prediction_packet_hash", capsule.get("prediction_packet_hash")),
        ("run_manifest_hash", capsule.get("run_manifest_hash")),
    ):
        if submission.get(field) != expected:
            errors.append(f"submission.{field}")
    unhashed = {key: value for key, value in submission.items() if key != "submission_hash"}
    if submission.get("submission_hash") != digest(unhashed):
        errors.append("submission.submission_hash")
    if submission.get("outcome_access_count_before_commitment") != 0:
        errors.append("submission.outcome_access")
    if submission.get("formal_result_authorized") is not False:
        errors.append("submission.formal_authorization")
    forbidden = _find_keys(submission, OUTCOME_KEYS)
    errors.extend(f"submission.forbidden_key:{path}" for path in forbidden)

    run_map = {row["condition_id"]: row for row in manifest.get("condition_runs") or []}
    summary_tasks = {row["summary_task_id"]: row for row in capsule.get("summary_tasks") or []}
    artifacts = submission.get("summary_artifacts")
    if not isinstance(artifacts, list):
        artifacts = []
        errors.append("submission.summary_artifacts")
    artifact_map: dict[str, dict[str, Any]] = {}
    for index, artifact in enumerate(artifacts):
        scope = f"submission.summary_artifacts[{index}]"
        if not isinstance(artifact, dict):
            errors.append(f"{scope}:object_required")
            continue
        if set(artifact) != {
            "schema", "summary_task_id", "summary_view_hash", "summary_text",
            "source_history_ids", "model_call_count", "prompt_tokens",
            "completion_tokens", "latency_seconds", "peak_memory_bytes",
            "retry_count", "fallback_count", "model_name",
            "model_artifact_digest", "hardware_fingerprint", "provider_options",
            "summary_artifact_hash",
        }:
            errors.append(f"{scope}.fields")
        sid = str(artifact.get("summary_task_id") or "")
        if not sid or sid in artifact_map or sid not in summary_tasks:
            errors.append(f"{scope}.summary_task_id")
        artifact_map[sid] = artifact
        task = summary_tasks.get(sid) or {}
        if artifact.get("schema") != SUMMARY_SCHEMA:
            errors.append(f"{scope}.schema")
        if not isinstance(artifact.get("summary_text"), str):
            errors.append(f"{scope}.summary_text")
        if artifact.get("summary_view_hash") != task.get("summary_view_hash"):
            errors.append(f"{scope}.summary_view_hash")
        if artifact.get("source_history_ids") != task.get("source_history_ids"):
            errors.append(f"{scope}.source_history_ids")
        empty = bool(task.get("empty_history_artifact"))
        expected_calls = 0 if empty else 1
        if artifact.get("model_call_count") != expected_calls:
            errors.append(f"{scope}.model_call_count")
        for count_field in ("prompt_tokens", "completion_tokens", "peak_memory_bytes"):
            value = artifact.get(count_field)
            if not isinstance(value, int) or value < 0:
                errors.append(f"{scope}.{count_field}")
        latency = artifact.get("latency_seconds")
        if not isinstance(latency, (int, float)) or not math.isfinite(float(latency)) or latency < 0:
            errors.append(f"{scope}.latency_seconds")
        if artifact.get("retry_count") != 0 or artifact.get("fallback_count") != 0:
            errors.append(f"{scope}.retry_or_fallback")
        run = run_map.get("B4_FULL_HISTORY_SUMMARY") or {}
        if empty:
            if artifact.get("model_name") != "deterministic_no_history" or artifact.get("provider_options") != {}:
                errors.append(f"{scope}.empty_history_resources")
        else:
            for field in ("model_name", "model_artifact_digest", "hardware_fingerprint", "provider_options"):
                if artifact.get(field) != run.get(field):
                    errors.append(f"{scope}.{field}")
        unhashed_artifact = {key: value for key, value in artifact.items() if key != "summary_artifact_hash"}
        if artifact.get("summary_artifact_hash") != digest(unhashed_artifact):
            errors.append(f"{scope}.summary_artifact_hash")
    if set(artifact_map) != set(summary_tasks):
        errors.append("submission.summary_artifact_completeness")

    tasks = capsule.get("prediction_tasks") or []
    task_map = {task["task_id"]: task for task in tasks}
    rows = submission.get("prediction_rows")
    if not isinstance(rows, list):
        rows = []
        errors.append("submission.prediction_rows")
    if [row.get("task_id") for row in rows if isinstance(row, dict)] != [task["task_id"] for task in tasks]:
        errors.append("submission.row_order_or_completeness")
    if len({row.get("task_id") for row in rows if isinstance(row, dict)}) != len(rows):
        errors.append("submission.duplicate_rows")
    model_digests: set[str] = set()
    hardware_fingerprints: set[str] = set()
    b5_tokens: dict[str, int] = {}
    ours_tokens: dict[str, int] = {}
    unauthorized_evidence_count = 0
    resource_totals = {
        condition: {
            "prediction_model_calls": 0,
            "semantic_model_calls": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "latency_seconds": 0.0,
            "peak_memory_bytes": 0,
        }
        for condition in CONDITION_IDS
    }
    for index, row in enumerate(rows):
        scope = f"submission.prediction_rows[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{scope}:object_required")
            continue
        if set(row) != {
            "task_id", "sample_id", "condition_id", "view_hash", "probabilities",
            "selected_behavior", "authorized_evidence_ids", "brief_evidence",
            "prompt_hash", "prompt_tokens", "completion_tokens", "latency_seconds",
            "peak_memory_bytes", "prediction_model_call_count",
            "semantic_model_call_count", "retry_count", "fallback_count",
            "model_name", "model_artifact_digest", "hardware_fingerprint",
            "provider_options", "b4_summary_artifact_hash", "fit_artifact_hash",
            "state_snapshot_hash", "transition_trace_hash",
        }:
            errors.append(f"{scope}.fields")
        task = task_map.get(str(row.get("task_id") or ""))
        if not task:
            errors.append(f"{scope}.task_id")
            continue
        condition = task["condition_id"]
        if row.get("sample_id") != task["sample_id"] or row.get("condition_id") != condition:
            errors.append(f"{scope}.sample_or_condition")
        if row.get("view_hash") != task["view_hash"]:
            errors.append(f"{scope}.view_hash")
        labels = task["view"]["candidate_behavior_labels"]
        probabilities = row.get("probabilities")
        if not isinstance(probabilities, dict) or set(probabilities) != set(labels):
            errors.append(f"{scope}.probability_labels")
            probabilities = {}
        probability_valid = True
        for label in labels:
            value = probabilities.get(label)
            if not isinstance(value, (int, float)) or not math.isfinite(float(value)) or value < 0:
                probability_valid = False
        if not probability_valid or abs(sum(float(probabilities.get(label, 0)) for label in labels) - 1.0) > 0.000001:
            errors.append(f"{scope}.probability_mass")
        elif row.get("selected_behavior") != _argmax(probabilities, labels):
            errors.append(f"{scope}.selected_behavior")
        if not isinstance(row.get("brief_evidence"), str) or len(row.get("brief_evidence", "")) > 500:
            errors.append(f"{scope}.brief_evidence")
        evidence = row.get("authorized_evidence_ids")
        if not isinstance(evidence, list) or any(not isinstance(item, str) for item in evidence):
            errors.append(f"{scope}.authorized_evidence_ids")
            evidence = []
        unauthorized = set(evidence) - _authorized_history_ids(task, summary_tasks)
        if unauthorized:
            unauthorized_evidence_count += len(unauthorized)
            errors.append(f"{scope}.unauthorized_evidence")
        if row.get("retry_count") != 0 or row.get("fallback_count") != 0:
            errors.append(f"{scope}.retry_or_fallback")
        for field in ("prompt_tokens", "completion_tokens", "peak_memory_bytes", "prediction_model_call_count", "semantic_model_call_count"):
            value = row.get(field)
            if not isinstance(value, int) or value < 0:
                errors.append(f"{scope}.{field}")
        latency = row.get("latency_seconds")
        if not isinstance(latency, (int, float)) or not math.isfinite(float(latency)) or latency < 0:
            errors.append(f"{scope}.latency_seconds")
        run = run_map.get(condition) or {}
        for field in ("model_name", "model_artifact_digest", "hardware_fingerprint", "provider_options"):
            if row.get(field) != run.get(field):
                errors.append(f"{scope}.{field}")
        if condition == "B0_PRIOR":
            if row.get("prediction_model_call_count") != 0 or row.get("semantic_model_call_count") != 0:
                errors.append(f"{scope}.B0_calls")
            if any(row.get(field) not in (0, 0.0, None) for field in ("prompt_tokens", "completion_tokens", "latency_seconds", "peak_memory_bytes", "prompt_hash")):
                errors.append(f"{scope}.B0_resources")
            counts = task["view"]["pre_cutoff_historical_behavior_counts"]
            expected_weights = {label: counts[label] + 1.0 for label in labels}
            expected_total = sum(expected_weights.values())
            expected_prior = {label: expected_weights[label] / expected_total for label in labels}
            if probability_valid and any(
                abs(float(probabilities[label]) - expected_prior[label]) > 1e-12
                for label in labels
            ):
                errors.append(f"{scope}.B0_prior")
        else:
            model_digests.add(str(row.get("model_artifact_digest") or ""))
            hardware_fingerprints.add(str(row.get("hardware_fingerprint") or ""))
            if len(str(row.get("prompt_hash") or "")) != 64:
                errors.append(f"{scope}.prompt_hash")
            if condition == PRIMARY_SYSTEM:
                if row.get("prediction_model_call_count") != 0:
                    errors.append(f"{scope}.prediction_call_count")
                if row.get("semantic_model_call_count") != 1:
                    errors.append(f"{scope}.semantic_call_count")
                for field in ("fit_artifact_hash", "state_snapshot_hash", "transition_trace_hash"):
                    if len(str(row.get(field) or "")) != 64:
                        errors.append(f"{scope}.{field}")
                ours_tokens[task["sample_id"]] = int(row.get("prompt_tokens") or 0)
            else:
                if row.get("prediction_model_call_count") != 1:
                    errors.append(f"{scope}.prediction_call_count")
                if row.get("semantic_model_call_count") != 0:
                    errors.append(f"{scope}.semantic_call_count")
            if condition == PRIMARY_CONTROL:
                b5_tokens[task["sample_id"]] = int(row.get("prompt_tokens") or 0)
            if condition == "B4_FULL_HISTORY_SUMMARY":
                sid = task["view"]["summary_task_id"]
                expected_hash = (artifact_map.get(sid) or {}).get("summary_artifact_hash")
                if row.get("b4_summary_artifact_hash") != expected_hash:
                    errors.append(f"{scope}.b4_summary_artifact_hash")
            elif row.get("b4_summary_artifact_hash") is not None:
                errors.append(f"{scope}.unexpected_b4_summary")
        totals = resource_totals.get(condition)
        if totals is not None:
            totals["prediction_model_calls"] += int(row.get("prediction_model_call_count") or 0)
            totals["semantic_model_calls"] += int(row.get("semantic_model_call_count") or 0)
            totals["prompt_tokens"] += int(row.get("prompt_tokens") or 0)
            totals["completion_tokens"] += int(row.get("completion_tokens") or 0)
            totals["latency_seconds"] += float(row.get("latency_seconds") or 0.0)
            totals["peak_memory_bytes"] = max(
                totals["peak_memory_bytes"], int(row.get("peak_memory_bytes") or 0)
            )
    if len(model_digests) != 1:
        errors.append("submission.same_model_artifact")
    if len(hardware_fingerprints) != 1:
        errors.append("submission.same_hardware")
    primary_token_differences = []
    for sample_id in sorted(set(b5_tokens) | set(ours_tokens)):
        b5 = b5_tokens.get(sample_id, 0)
        ours = ours_tokens.get(sample_id, 0)
        denominator = max(b5, ours, 1)
        primary_token_differences.append(abs(ours - b5) / denominator)
    max_difference = max(primary_token_differences, default=0.0)
    b4_summary_totals = {
        "model_calls": sum(int(row.get("model_call_count") or 0) for row in artifacts),
        "prompt_tokens": sum(int(row.get("prompt_tokens") or 0) for row in artifacts),
        "completion_tokens": sum(int(row.get("completion_tokens") or 0) for row in artifacts),
        "latency_seconds": sum(float(row.get("latency_seconds") or 0.0) for row in artifacts),
        "peak_memory_bytes": max(
            (int(row.get("peak_memory_bytes") or 0) for row in artifacts), default=0
        ),
    }
    return {
        "valid": not errors,
        "errors": errors,
        "row_count": len(rows),
        "summary_artifact_count": len(artifacts),
        "unauthorized_evidence_count": unauthorized_evidence_count,
        "same_model_artifact": len(model_digests) == 1,
        "same_hardware": len(hardware_fingerprints) == 1,
        "max_primary_prompt_token_difference_fraction": max_difference,
        "exact_token_sensitivity_required": max_difference > 0.05,
        "condition_resource_totals": resource_totals,
        "b4_summary_build_resource_totals": b4_summary_totals,
        "submission_hash": digest(submission),
    }


def create_commitment_receipt(
    submission: dict[str, Any], capsule: dict[str, Any], packet: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, Any]:
    report = validate_submission(submission, capsule, packet, manifest)
    if not report["valid"]:
        raise ValueError("cannot commit invalid submission: " + "; ".join(report["errors"]))
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "version": "1.0.0",
        "status": "synthetic_commitment_for_scorer_qa_only",
        "data_kind": submission["data_kind"],
        "contract_hash": submission["contract_hash"],
        "capsule_hash": capsule["capsule_hash"],
        "prediction_packet_hash": submission["prediction_packet_hash"],
        "submission_hash": submission["submission_hash"],
        "committed_task_ids": [row["task_id"] for row in submission["prediction_rows"]],
        "committed_row_count": len(submission["prediction_rows"]),
        "outcome_access_count_at_commitment": 0,
        "scoring_allowed_after_commitment": True,
        "formal_scoring_authorized": False,
    }
    receipt["receipt_hash"] = digest(receipt)
    return receipt


def validate_commitment_receipt(
    receipt: dict[str, Any], submission: dict[str, Any], capsule: dict[str, Any]
) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(receipt, dict):
        return {"valid": False, "errors": ["receipt:object_required"]}
    if receipt.get("schema") != RECEIPT_SCHEMA or receipt.get("version") != "1.0.0":
        errors.append("receipt.schema_or_version")
    if receipt.get("status") != "synthetic_commitment_for_scorer_qa_only":
        errors.append("receipt.status")
    if receipt.get("submission_hash") != submission.get("submission_hash") or receipt.get("submission_hash") != digest({key: value for key, value in submission.items() if key != "submission_hash"}):
        errors.append("receipt.submission_hash")
    if receipt.get("capsule_hash") != capsule.get("capsule_hash"):
        errors.append("receipt.capsule_hash")
    if receipt.get("prediction_packet_hash") != capsule.get("prediction_packet_hash"):
        errors.append("receipt.prediction_packet_hash")
    task_ids = [row.get("task_id") for row in submission.get("prediction_rows") or []]
    if receipt.get("committed_task_ids") != task_ids or receipt.get("committed_row_count") != len(task_ids):
        errors.append("receipt.committed_rows")
    if receipt.get("outcome_access_count_at_commitment") != 0:
        errors.append("receipt.outcome_access")
    if receipt.get("scoring_allowed_after_commitment") is not True or receipt.get("formal_scoring_authorized") is not False:
        errors.append("receipt.authorization")
    unhashed = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    if receipt.get("receipt_hash") != digest(unhashed):
        errors.append("receipt.receipt_hash")
    return {"valid": not errors, "errors": errors, "receipt_hash": digest(receipt)}


def validate_outcome_key(
    outcome_key: dict[str, Any], packet: dict[str, Any], split_report: dict[str, Any]
) -> dict[str, Any]:
    errors: list[str] = []
    if split_report.get("schema") != "uruha_m56_blinded_split_report_v1":
        errors.append("split_report.schema")
    if split_report.get("outcome_key_exposed_to_generation") is not False:
        errors.append("split_report.outcome_exposure")
    if split_report.get("future_leakage_violations") != 0:
        errors.append("split_report.future_leakage")
    if outcome_key.get("schema") != preflight_m56.OUTCOME_KEY_SCHEMA:
        errors.append("outcome_key.schema")
    for field in ("data_kind", "contract_hash", "dataset_hash", "sample_count"):
        if outcome_key.get(field) != packet.get(field):
            errors.append(f"outcome_key.{field}")
    outcomes = outcome_key.get("outcomes")
    if not isinstance(outcomes, list):
        outcomes = []
        errors.append("outcome_key.outcomes")
    expected_ids = [row["sample_id"] for row in packet.get("model_inputs") or []]
    if [row.get("sample_id") for row in outcomes if isinstance(row, dict)] != expected_ids:
        errors.append("outcome_key.sample_order")
    packet_rows = {row["sample_id"]: row for row in packet.get("model_inputs") or []}
    expected_outcome_fields = {
        "sample_id", "actual_observed_behavior", "acceptable_behavior_labels",
        "actual_observed_at", "source_timestamp", "annotation_confidence",
    }
    for index, outcome in enumerate(outcomes):
        scope = f"outcome_key.outcomes[{index}]"
        if not isinstance(outcome, dict) or set(outcome) != expected_outcome_fields:
            errors.append(f"{scope}.fields")
            continue
        packet_row = packet_rows.get(str(outcome.get("sample_id") or "")) or {}
        labels = ((packet_row.get("model_input") or {}).get("candidate_behavior_labels") or [])
        actual = outcome.get("actual_observed_behavior")
        acceptable = outcome.get("acceptable_behavior_labels")
        if actual not in labels:
            errors.append(f"{scope}.actual_label")
        if (
            not isinstance(acceptable, list)
            or not acceptable
            or actual not in acceptable
            or not set(acceptable) <= set(labels)
        ):
            errors.append(f"{scope}.acceptable_labels")
        confidence = outcome.get("annotation_confidence")
        if (
            not isinstance(confidence, (int, float))
            or not math.isfinite(float(confidence))
            or not 0 <= float(confidence) <= 1
        ):
            errors.append(f"{scope}.annotation_confidence")
    if outcome_key.get("generation_process_access_allowed") is not False:
        errors.append("outcome_key.generation_access")
    if split_report.get("outcome_key_hash") != digest(outcome_key):
        errors.append("outcome_key.split_hash")
    if split_report.get("prediction_packet_hash") != digest(packet):
        errors.append("outcome_key.packet_hash")
    return {"valid": not errors, "errors": errors, "outcome_count": len(outcomes)}


def _monte_carlo_sign_flip(values: list[float], *, draws: int, seed: int) -> float:
    observed = abs(sum(values) / len(values))
    rng = random.Random(seed)
    extreme = 0
    for _ in range(draws):
        statistic = abs(sum(value if rng.randrange(2) else -value for value in values) / len(values))
        extreme += int(statistic >= observed - 1e-15)
    return (extreme + 1) / (draws + 1)


def _paired_primary(rows: list[dict[str, Any]], contract: dict[str, Any]) -> dict[str, Any]:
    controls = {row["sample_id"]: row for row in rows if row["condition_id"] == PRIMARY_CONTROL}
    systems = {row["sample_id"]: row for row in rows if row["condition_id"] == PRIMARY_SYSTEM}
    if set(controls) != set(systems):
        raise ValueError("primary conditions do not contain identical samples")
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
    scoring = contract["scoring"]
    repetitions = scoring["bootstrap_repetitions"]
    seed = scoring["bootstrap_seed"]
    brier_ci = percentile_bootstrap_ci(brier_deltas, repetitions=repetitions, seed=seed)
    nll_ci = percentile_bootstrap_ci(nll_deltas, repetitions=repetitions, seed=seed + 1)
    exact_limit = scoring["sign_flip_exact_pair_limit"]

    def sign_flip(values: list[float], metric_seed: int) -> tuple[float, str]:
        if len(values) <= exact_limit:
            return exact_sign_flip_pvalue(values), "exact"
        return _monte_carlo_sign_flip(
            values,
            draws=scoring["sign_flip_monte_carlo_draws"],
            seed=metric_seed,
        ), "prospective_deterministic_monte_carlo"

    brier_p, sign_flip_method = sign_flip(brier_deltas, scoring["sign_flip_seed"])
    nll_p, nll_method = sign_flip(nll_deltas, scoring["sign_flip_seed"] + 1)
    top1_delta = sum(top1_deltas) / len(top1_deltas)
    proper_gate = brier_ci[1] < 0 and nll_ci[1] < 0
    top1_gate = top1_delta >= -0.05
    return {
        "control": PRIMARY_CONTROL,
        "system": PRIMARY_SYSTEM,
        "sample_count": len(pairs),
        "delta_definition": "Ours minus B5; negative Brier/NLL is better",
        "brier": {
            "mean_delta": sum(brier_deltas) / len(brier_deltas),
            "bootstrap_95_ci": brier_ci,
            "sign_flip_two_sided_p": brier_p,
            "sign_flip_method": sign_flip_method,
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


def score_committed_submission(
    submission: dict[str, Any],
    receipt: dict[str, Any],
    capsule: dict[str, Any],
    packet: dict[str, Any],
    manifest: dict[str, Any],
    split_report: dict[str, Any],
    outcome_key: dict[str, Any],
    *,
    formal_authorization: dict[str, Any] | None = None,
) -> dict[str, Any]:
    contract = load_contract()
    submission_report = validate_submission(submission, capsule, packet, manifest)
    receipt_report = validate_commitment_receipt(receipt, submission, capsule)
    key_report = validate_outcome_key(outcome_key, packet, split_report)
    errors = submission_report["errors"] + receipt_report["errors"] + key_report["errors"]
    if errors:
        raise ValueError("separate scorer rejected artifacts: " + "; ".join(errors))
    if packet.get("data_kind") != temporal_m55.SYNTHETIC_KIND:
        if not (formal_authorization or {}).get("m56_formal_scoring_authorized"):
            raise PermissionError("real formal scoring requires a separate post-M55 authorization receipt")
    outcomes = {row["sample_id"]: row for row in outcome_key["outcomes"]}
    joined = []
    for row in submission["prediction_rows"]:
        outcome = outcomes[row["sample_id"]]
        joined.append({
            "sample_id": row["sample_id"],
            "condition_id": row["condition_id"],
            "probabilities": deepcopy(row["probabilities"]),
            "actual_observed_behavior": outcome["actual_observed_behavior"],
            "acceptable_behavior_labels": deepcopy(outcome["acceptable_behavior_labels"]),
        })
    labels = packet["model_inputs"][0]["model_input"]["candidate_behavior_labels"]
    by_condition = {}
    for condition in CONDITION_IDS:
        condition_rows = [row for row in joined if row["condition_id"] == condition]
        by_condition[condition] = evaluate_predictions(condition_rows, labels)
    comparison = _paired_primary(joined, contract)
    synthetic = packet.get("data_kind") == temporal_m55.SYNTHETIC_KIND
    sensitivity_required = submission_report["exact_token_sensitivity_required"]
    sensitivity_passed = not sensitivity_required or bool(
        (formal_authorization or {}).get("exact_token_sensitivity_passed")
    )
    formal_gate_passed = comparison["gates"]["formal_success"] and sensitivity_passed
    report = {
        "schema": SCORE_SCHEMA,
        "version": "1.0.0",
        "status": "synthetic_engineering_score_only" if synthetic else "formal_m56_score",
        "data_kind": packet["data_kind"],
        "contract_hash": capsule["contract_hash"],
        "capsule_hash": capsule["capsule_hash"],
        "submission_hash": submission["submission_hash"],
        "commitment_receipt_hash": receipt["receipt_hash"],
        "outcome_key_hash": digest(outcome_key),
        "sample_count": packet["sample_count"],
        "condition_metrics": by_condition,
        "primary_comparison": comparison,
        "evidence_audit": {
            "unauthorized_or_post_cutoff_evidence_count": submission_report["unauthorized_evidence_count"],
            "unauthorized_or_post_cutoff_evidence_rate": 0.0,
            "semantic_irrelevant_memory_ground_truth": "unavailable_without_separate_human_annotation",
        },
        "resource_audit": {
            "max_primary_prompt_token_difference_fraction": submission_report["max_primary_prompt_token_difference_fraction"],
            "exact_token_sensitivity_required": sensitivity_required,
            "exact_token_sensitivity_passed": sensitivity_passed,
            "condition_resource_totals": submission_report["condition_resource_totals"],
            "b4_summary_build_resource_totals": submission_report["b4_summary_build_resource_totals"],
            "all_b4_summary_artifacts_counted": True,
            "all_ours_semantic_calls_counted": True,
        },
        "formal_result": not synthetic,
        "decision": "synthetic_engineering_only_no_formal_claim" if synthetic else (
            "formal_gate_pass" if formal_gate_passed else "formal_gate_fail_retained"
        ),
        "claim_boundary": "Synthetic scoring validates scorer mechanics only; it is not human evidence, model advantage, Equation V1 validity, or production authorization." if synthetic else "A formal gate result is restricted to the frozen M55/M56 target, conditions, model, and hardware.",
    }
    report["report_hash"] = digest(report)
    return report


def build_live_report() -> dict[str, Any]:
    contract = load_contract()
    contract_report = validate_contract()
    preflight = preflight_m56.build_preflight_report()
    report = {
        "schema": "uruha_m56_blinded_execution_capsule_live_report_v1",
        "status": "capsule_protocol_ready_execution_blocked",
        "contract_valid": contract_report["valid"],
        "contract_hash": contract_report["contract_hash"],
        "preflight_contract_valid": preflight["contract_valid"],
        "condition_count": len(CONDITION_IDS),
        "current_execution_authorized": False,
        "blocking_gate": preflight["blocking_gate"],
        "counts": deepcopy(preflight.get("counts") or {}),
        "model_call_count": 0,
        "target_outcome_access_count": 0,
        "formal_result_created": False,
        "engineering_capabilities": [
            "condition_specific_views",
            "complete_submission_validation",
            "sha256_commitment_before_outcome",
            "separate_scorer",
            "resource_and_evidence_audit",
        ],
        "claim_boundary": contract["claim_boundary"],
    }
    report["report_hash"] = digest(report)
    return report


def render_dashboard(report: dict[str, Any] | None = None) -> str:
    report = deepcopy(report or build_live_report())
    counts = report.get("counts") or {}
    slots = list(counts.get("v7_completed_slots_by_ledger") or [0, 0])
    while len(slots) < 2:
        slots.append(0)
    cards = [
        ("B0", "只看歷史次數", "0 次模型"),
        ("B1", "只看現在事件", "看不到歷史"),
        ("B2", "現在＋人物摘要", "看不到歷史"),
        ("B3", "現在＋最相關 4 筆", "固定檢索"),
        ("B4", "現在＋獨立歷史摘要", "摘要成本另計"),
        ("B5", "全部結構化歷史", "固定主對照"),
        ("Ours", "與 B5 同資料＋狀態轉移", "候選方程式"),
    ]
    card_html = "".join(
        f'<div class="card"><b>{html.escape(name)}</b><span>{html.escape(view)}</span><em>{html.escape(note)}</em></div>'
        for name, view, note in cards
    )
    blocker = html.escape(str(report.get("blocking_gate") or "M55 real-person gate"))
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M56 盲式執行艙</title><style>body{{margin:0;background:#07111f;color:#f0f6ff;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}main{{max-width:1320px;margin:auto;padding:28px}}section{{background:#111d31;border:1px solid #2d466c;border-radius:20px;padding:22px;margin:16px 0}}.hero{{background:linear-gradient(135deg,#123552,#271a3b)}}h1{{font-size:34px;margin:8px 0 12px}}.sub{{color:#9cb2d2}}.cards{{display:grid;grid-template-columns:repeat(7,1fr);gap:8px}}.card{{background:#081528;border:1px solid #34547e;border-radius:14px;padding:15px;text-align:center;min-height:105px}}.card b,.card span,.card em{{display:block}}.card span{{margin:10px 0}}.card em{{font-style:normal;color:#68dbc6;font-size:13px}}.flow{{display:grid;grid-template-columns:1fr auto 1fr auto 1fr auto 1fr;align-items:center;gap:10px}}.node{{background:#081528;border:1px solid #3c5d89;border-radius:15px;padding:18px;text-align:center;min-height:74px}}.arrow{{font-size:25px;color:#68dbc6}}.lock{{border-color:#e3aa56}}.key{{border-color:#d86e8b}}.checks{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}}.check{{background:#0a1729;border-radius:13px;padding:15px;border:1px solid #304a6e}}.warn{{color:#ff9bb0;font-weight:800}}.zero{{color:#6de2c9;font-weight:800}}@media(max-width:960px){{.cards,.flow,.checks{{grid-template-columns:1fr}}.arrow{{transform:rotate(90deg);text-align:center}}}}</style></head><body><main><section class="hero"><small>M56 · CAPABILITY-SEPARATED EXECUTION</small><h1>不是把七個提示詞放在一起，而是真正把資訊權限切開</h1><p class="sub">預測程式只能拿到各組被允許的視圖；完整七組預測封存後，另一個計分器才可讀答案。</p><p class="warn">目前 V7 {slots[0]}/18 + {slots[1]}/18 · real rows {counts.get('temporally_valid_prediction_row_count',0)}/30 · 正式執行禁止</p></section><section><h2>七組資訊視圖</h2><div class="cards">{card_html}</div></section><section><h2>兩個隔離艙</h2><div class="flow"><div class="node"><b>安全題包</b><br>只有 cutoff 前資訊</div><div class="arrow">→</div><div class="node"><b>生成艙</b><br>七組逐列完成<br><span class="zero">答案讀取 0</span></div><div class="arrow">→</div><div class="node lock"><b>SHA-256 封存</b><br>漏一列或事後改動即失效</div><div class="arrow">→</div><div class="node key"><b>獨立計分艙</b><br>封存有效才解鎖答案</div></div></section><section><h2>會直接判無效的作弊路徑</h2><div class="checks"><div class="check">B1/B2 偷看歷史</div><div class="check">B4 摘要成本漏算</div><div class="check">B5/Ours 原始資訊不同</div><div class="check">漏列、重排、重試或改模型</div></div></section><section><h2>目前可說與不可說</h2><p><span class="zero">已完成協定：</span>資訊隔離、預測封存、獨立計分、成本與證據稽核可被程式驗證。</p><p class="warn">仍不能說：</p><p>還沒有真人 M55 資料、沒有正式模型呼叫、沒有 M56 勝負，也沒有證明人類方程式。</p><p>阻擋點：{blocker}</p></section></main></body></html>"""


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
    parser.add_argument("--format", choices=("contract", "report", "html"), default="report")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--port", type=int, default=7908)
    args = parser.parse_args()
    if args.serve:
        serve_demo(args.port)
        return
    if args.format == "contract":
        payload = validate_contract()
    elif args.format == "html":
        print(render_dashboard())
        return
    else:
        payload = build_live_report()
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
