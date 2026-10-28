#!/usr/bin/env python3
"""M56 blinded same-model fair-comparison preflight.

This module freezes and validates the comparison protocol, splits an explicitly
supplied temporal result into a model-safe prediction packet and a separate
private outcome key, and audits future run manifests.  It never invokes a model
and does not read a private M55 record pack by default.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
from typing import Any

import audit_m55_real_person_longitudinal_readiness as readiness_m55
import m55_temporal_row_contract as temporal_m55
from longitudinal_human_model.temporal import build_model_input, validate_temporal_dataset


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/m56_fair_comparison_preflight_v1.json"
CONDITION_IDS = (
    "B0_PRIOR",
    "B1_BASE_LLM",
    "B2_PERSONA_PROMPT",
    "B3_RAG",
    "B4_FULL_HISTORY_SUMMARY",
    "B5_STRUCTURED_HISTORY",
    "OURS_HYBRID",
)
MODEL_CONDITIONS = CONDITION_IDS[1:]
PRIMARY_CONTROL = "B5_STRUCTURED_HISTORY"
PRIMARY_SYSTEM = "OURS_HYBRID"
PREDICTION_PACKET_SCHEMA = "uruha_m56_blinded_prediction_packet_v1"
OUTCOME_KEY_SCHEMA = "uruha_m56_private_outcome_key_v1"
RUN_MANIFEST_SCHEMA = "uruha_m56_condition_run_manifest_v1"
FORBIDDEN_PACKET_KEYS = {
    "actual_observed_behavior",
    "acceptable_behavior_labels",
    "actual_observed_at",
    "source_timestamp",
    "annotation_confidence",
    "completed_event_summary",
    "outcome_key",
    "reference_answer",
    "answer_key",
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
    path_text = str(binding.get("path") or "")
    expected = str(binding.get("sha256") or "")
    path = Path(path_text)
    if not path.is_absolute():
        path = ROOT / path
    return bool(path_text) and len(expected) == 64 and path.is_file() and sha256_file(path) == expected


def _find_forbidden_keys(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if key in FORBIDDEN_PACKET_KEYS:
                found.append(path)
            found.extend(_find_forbidden_keys(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_find_forbidden_keys(child, f"{prefix}[{index}]"))
    return found


def validate_contract(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors: list[str] = []
    if contract.get("schema") != "uruha_m56_fair_comparison_preflight_contract_v1":
        errors.append("schema")
    if contract.get("version") != "1.0.0":
        errors.append("version")
    if contract.get("status") != "frozen_before_m55_real_rows_or_any_m56_model_generation":
        errors.append("status")
    bindings = contract.get("bindings")
    if not isinstance(bindings, dict) or len(bindings) != 11:
        errors.append("bindings")
    else:
        for name, binding in bindings.items():
            if not _binding_valid(binding):
                errors.append(f"binding:{name}")
    conditions = contract.get("conditions")
    ids = tuple(row.get("condition_id") for row in conditions or [] if isinstance(row, dict))
    if ids != CONDITION_IDS:
        errors.append("condition_ids_or_order")
    if len(ids) != len(set(ids)):
        errors.append("duplicate_condition")
    if conditions:
        model_flags = {row.get("condition_id"): row.get("foundation_model_used") for row in conditions}
        if model_flags.get("B0_PRIOR") is not False:
            errors.append("B0_model_exception")
        if any(model_flags.get(condition) is not True for condition in MODEL_CONDITIONS):
            errors.append("same_model_condition_flags")
        for row in conditions:
            if "current_or_future_outcome" not in (row.get("forbidden_information") or []):
                errors.append(f"outcome_boundary:{row.get('condition_id')}")
    primary = contract.get("primary_contrast") or {}
    if primary.get("control") != PRIMARY_CONTROL or primary.get("system") != PRIMARY_SYSTEM:
        errors.append("primary_contrast")
    if primary.get("control_selected_before_results") is not True:
        errors.append("primary_control_not_prospective")
    if primary.get("weaker_baseline_may_replace_control_after_results") is not False:
        errors.append("posthoc_control_replacement")
    if primary.get("same_pre_cutoff_source_information") is not True:
        errors.append("primary_information_mismatch")
    blinding = contract.get("blinding") or {}
    if blinding.get("prediction_packet_schema") != PREDICTION_PACKET_SCHEMA:
        errors.append("prediction_packet_schema")
    if blinding.get("outcome_key_schema") != OUTCOME_KEY_SCHEMA:
        errors.append("outcome_key_schema")
    if set(blinding.get("prediction_packet_forbidden_keys") or []) != FORBIDDEN_PACKET_KEYS:
        errors.append("prediction_packet_forbidden_keys")
    for field in (
        "generation_process_receives_outcome_key",
    ):
        if blinding.get(field) is not False:
            errors.append(f"blinding:{field}")
    for field in (
        "all_condition_predictions_committed_before_scoring",
        "outcome_join_only_in_separate_scorer",
    ):
        if blinding.get(field) is not True:
            errors.append(f"blinding:{field}")
    controls = contract.get("model_and_resource_controls") or {}
    if controls.get("model_name") != "qwen3.5:9b":
        errors.append("model_name")
    options = controls.get("provider_options") or {}
    if options != {"temperature": 0, "seed": 560901, "num_ctx": 16384, "num_predict": 384}:
        errors.append("provider_options")
    if controls.get("retry_policy") != "no_retry_no_condition_fallback":
        errors.append("retry_policy")
    for field in (
        "same_physical_machine",
        "same_hardware_snapshot",
        "same_model_artifact_for_B1_through_B5_and_Ours",
        "B4_summary_build_cost_included",
        "all_upstream_Ours_model_cost_included",
        "actual_prompt_completion_tokens_latency_and_peak_memory_reported_by_condition",
        "exact_token_matched_sensitivity_required_if_primary_difference_exceeds_max",
    ):
        if controls.get(field) is not True:
            errors.append(f"resource_control:{field}")
    if controls.get("B5_and_Ours_semantic_model_call_cap_per_sample") != 1:
        errors.append("primary_model_call_cap")
    if controls.get("per_sample_input_token_budget") != 8192:
        errors.append("input_token_budget")
    if controls.get("per_sample_output_token_budget") != 384:
        errors.append("output_token_budget")
    data_gate = contract.get("dataset_gate") or {}
    if data_gate.get("required_data_kind") != temporal_m55.REAL_KIND:
        errors.append("dataset_kind")
    if data_gate.get("required_record_count") != 30 or data_gate.get("prediction_packet_sample_count") != 30:
        errors.append("dataset_count")
    if data_gate.get("current_outcomes_may_fit_or_tune_any_condition") is not False:
        errors.append("outcome_tuning_forbidden")
    if data_gate.get("sealed_final_holdout_access") is not False:
        errors.append("sealed_holdout_access")
    metrics = contract.get("metrics") or {}
    if metrics.get("co_primary") != [
        "paired_brier_delta_ours_minus_b5",
        "paired_nll_delta_ours_minus_b5",
    ]:
        errors.append("co_primary_metrics")
    if metrics.get("paired_bootstrap_iterations") != 20000:
        errors.append("bootstrap_iterations")
    success = contract.get("success_and_failure") or {}
    if success.get("co_primary_rule") != "intersection_union_both_required_no_posthoc_metric_selection":
        errors.append("co_primary_rule")
    for field in (
        "failure_if_any_prediction_row_missing",
        "failure_if_any_condition_retry_or_fallback",
        "failure_if_outcome_key_visible_to_generation",
        "failure_if_primary_control_changed_after_results",
        "negative_result_retained",
    ):
        if success.get(field) is not True:
            errors.append(f"failure_policy:{field}")
    authorization = contract.get("authorization") or {}
    for field, value in authorization.items():
        if value is not False:
            errors.append(f"authorization:{field}")
    return {
        "valid": not errors,
        "errors": errors,
        "contract_hash": digest(contract),
        "binding_count": len(bindings or {}),
        "condition_count": len(conditions or []),
        "primary_control": primary.get("control"),
        "primary_system": primary.get("system"),
    }


def _condition_order(sample_id: str, contract: dict[str, Any]) -> list[str]:
    seed = int((contract.get("blinding") or {}).get("condition_order_seed") or 0)
    offset = (int(sha256(f"{seed}:{sample_id}".encode("utf-8")).hexdigest()[:16], 16) % len(CONDITION_IDS))
    return list(CONDITION_IDS[offset:] + CONDITION_IDS[:offset])


def validate_prediction_packet(
    packet: dict[str, Any], contract: dict[str, Any] | None = None
) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    contract_report = validate_contract(contract)
    errors = [f"contract:{error}" for error in contract_report["errors"]]
    if not isinstance(packet, dict):
        return {"valid": False, "errors": errors + ["packet:object_required"]}
    allowed_fields = {
        "schema",
        "version",
        "status",
        "data_kind",
        "contract_hash",
        "dataset_hash",
        "sample_count",
        "conditions",
        "model_inputs",
        "data_boundary",
    }
    if set(packet) - allowed_fields:
        errors.append("packet:unexpected_fields:" + ",".join(sorted(set(packet) - allowed_fields)))
    if packet.get("schema") != PREDICTION_PACKET_SCHEMA:
        errors.append("packet.schema")
    if packet.get("version") != "1.0.0":
        errors.append("packet.version")
    if packet.get("contract_hash") != contract_report["contract_hash"]:
        errors.append("packet.contract_hash")
    if tuple(packet.get("conditions") or []) != CONDITION_IDS:
        errors.append("packet.conditions")
    forbidden = _find_forbidden_keys(packet)
    errors.extend(f"packet.forbidden_key:{path}" for path in forbidden)
    model_inputs = packet.get("model_inputs")
    if not isinstance(model_inputs, list) or not model_inputs:
        errors.append("packet.model_inputs:nonempty_array_required")
        model_inputs = []
    if packet.get("sample_count") != len(model_inputs):
        errors.append("packet.sample_count")
    if packet.get("data_kind") == temporal_m55.REAL_KIND and len(model_inputs) != 30:
        errors.append("packet.real_sample_count")
    sample_ids: set[str] = set()
    required_input_fields = {
        "dataset_id",
        "sample_id",
        "prediction_time",
        "available_history_cutoff",
        "candidate_behavior_labels",
        "target",
        "event_context",
        "participants",
        "available_history",
    }
    for index, row in enumerate(model_inputs):
        scope = f"packet.model_inputs[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{scope}:object_required")
            continue
        if set(row) != {"sample_id", "condition_order", "model_input", "model_input_hash"}:
            errors.append(f"{scope}:fields")
            continue
        model_input = row.get("model_input")
        if not isinstance(model_input, dict) or set(model_input) != required_input_fields:
            errors.append(f"{scope}.model_input:fields")
            continue
        sample_id = str(row.get("sample_id") or "")
        if sample_id != model_input.get("sample_id") or not sample_id:
            errors.append(f"{scope}.sample_id")
        if sample_id in sample_ids:
            errors.append(f"{scope}.sample_id:duplicate")
        sample_ids.add(sample_id)
        if row.get("condition_order") != _condition_order(sample_id, contract):
            errors.append(f"{scope}.condition_order")
        if row.get("model_input_hash") != digest(model_input):
            errors.append(f"{scope}.model_input_hash")
    boundary = packet.get("data_boundary") or {}
    if boundary != {
        "outcome_key_available_to_generation": False,
        "post_cutoff_evidence_available": False,
        "private_mental_fact_available": False,
        "raw_or_verbatim_content_available": False,
    }:
        errors.append("packet.data_boundary")
    return {
        "valid": not errors,
        "errors": errors,
        "sample_count": len(model_inputs),
        "forbidden_key_count": len(forbidden),
        "packet_hash": digest(packet),
    }


def build_blinded_artifacts(
    compiled_temporal_result: dict[str, Any],
    *,
    readiness: dict[str, Any] | None = None,
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    contract_report = validate_contract(contract)
    if not contract_report["valid"]:
        raise ValueError("invalid M56 contract: " + "; ".join(contract_report["errors"]))
    if not isinstance(compiled_temporal_result, dict):
        raise ValueError("compiled temporal result must be an object")
    dataset = deepcopy(compiled_temporal_result.get("dataset") or {})
    audit = deepcopy(compiled_temporal_result.get("audit") or {})
    leakage = validate_temporal_dataset(dataset)
    if audit.get("future_leakage_violations") != 0 or leakage.get("future_leakage_violations") != 0:
        raise ValueError("future leakage must be zero before packet splitting")
    data_kind = str(audit.get("data_kind") or "")
    if data_kind not in (temporal_m55.SYNTHETIC_KIND, temporal_m55.REAL_KIND):
        raise ValueError("compiled result data kind is invalid")
    dataset_hash = str(dataset.get("dataset_hash") or "")
    expected_hash = digest({key: value for key, value in dataset.items() if key != "dataset_hash"})
    if len(dataset_hash) != 64 or dataset_hash != expected_hash:
        raise ValueError("compiled temporal dataset hash is missing or stale")
    if audit.get("record_count") != len(dataset.get("samples") or []):
        raise ValueError("compiled audit record count mismatch")
    if data_kind == temporal_m55.REAL_KIND:
        live = readiness or {}
        if not (
            live.get("m55_pilot_complete") is True
            and live.get("m56_authorized") is True
            and len(dataset.get("samples") or []) == int((contract.get("dataset_gate") or {}).get("required_record_count") or 0)
        ):
            raise PermissionError("real prediction packet requires completed M55 and explicit M56 authorization")
    model_inputs = []
    outcomes = []
    for sample in dataset["samples"]:
        safe = build_model_input(dataset, sample)
        sample_id = sample["sample_id"]
        model_inputs.append(
            {
                "sample_id": sample_id,
                "condition_order": _condition_order(sample_id, contract),
                "model_input": safe,
                "model_input_hash": digest(safe),
            }
        )
        outcomes.append(
            {
                "sample_id": sample_id,
                "actual_observed_behavior": sample["actual_observed_behavior"],
                "acceptable_behavior_labels": list(sample["acceptable_behavior_labels"]),
                "actual_observed_at": sample["actual_observed_at"],
                "source_timestamp": sample["source_timestamp"],
                "annotation_confidence": sample["annotation_confidence"],
            }
        )
    packet = {
        "schema": PREDICTION_PACKET_SCHEMA,
        "version": "1.0.0",
        "status": "synthetic_engineering_only" if data_kind == temporal_m55.SYNTHETIC_KIND else "private_real_blinded_packet_pending_formal_run",
        "data_kind": data_kind,
        "contract_hash": contract_report["contract_hash"],
        "dataset_hash": dataset_hash,
        "sample_count": len(model_inputs),
        "conditions": list(CONDITION_IDS),
        "model_inputs": model_inputs,
        "data_boundary": {
            "outcome_key_available_to_generation": False,
            "post_cutoff_evidence_available": False,
            "private_mental_fact_available": False,
            "raw_or_verbatim_content_available": False,
        },
    }
    outcome_key = {
        "schema": OUTCOME_KEY_SCHEMA,
        "version": "1.0.0",
        "status": "private_withheld_until_prediction_commitment",
        "data_kind": data_kind,
        "contract_hash": contract_report["contract_hash"],
        "dataset_hash": dataset_hash,
        "sample_count": len(outcomes),
        "outcomes": outcomes,
        "generation_process_access_allowed": False,
    }
    packet_validation = validate_prediction_packet(packet, contract)
    if not packet_validation["valid"]:
        raise ValueError("invalid prediction packet: " + "; ".join(packet_validation["errors"]))
    split_report = {
        "schema": "uruha_m56_blinded_split_report_v1",
        "data_kind": data_kind,
        "sample_count": len(model_inputs),
        "prediction_packet_hash": digest(packet),
        "outcome_key_hash": digest(outcome_key),
        "outcome_key_exposed_to_generation": False,
        "future_leakage_violations": 0,
        "model_call_count": 0,
        "m56_result_created": False,
        "formal_target_claim": False,
    }
    split_report["report_hash"] = digest(split_report)
    return {"prediction_packet": packet, "outcome_key": outcome_key, "split_report": split_report}


def build_fixture_run_manifest(
    packet: dict[str, Any], *, hardware_fingerprint: str = "synthetic-hardware"
) -> dict[str, Any]:
    contract = load_contract()
    controls = contract["model_and_resource_controls"]
    sample_ids = [row["sample_id"] for row in packet["model_inputs"]]
    runs = []
    for condition in CONDITION_IDS:
        model_used = condition != "B0_PRIOR"
        runs.append(
            {
                "condition_id": condition,
                "model_used": model_used,
                "model_name": controls["model_name"] if model_used else "deterministic_prior",
                "model_artifact_digest": "f" * 64 if model_used else "deterministic_prior",
                "hardware_fingerprint": hardware_fingerprint,
                "provider_options": deepcopy(controls["provider_options"]) if model_used else {},
                "input_token_budget": controls["per_sample_input_token_budget"] if model_used else 0,
                "output_token_budget": controls["per_sample_output_token_budget"] if model_used else 0,
                "model_call_cap_per_sample": 1 if model_used else 0,
                "source_sample_ids": sample_ids,
                "outcome_key_visible": False,
                "retry_count": 0,
                "fallback_count": 0,
            }
        )
    return {
        "schema": RUN_MANIFEST_SCHEMA,
        "version": "1.0.0",
        "status": "synthetic_preflight_manifest_only",
        "contract_hash": validate_contract()["contract_hash"],
        "data_kind": packet["data_kind"],
        "dataset_hash": packet["dataset_hash"],
        "prediction_packet_hash": digest(packet),
        "condition_runs": runs,
        "prediction_commitment_hash": None,
        "scoring_started": False,
        "model_call_count": 0,
    }


def validate_run_manifest(
    manifest: dict[str, Any],
    packet: dict[str, Any],
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    contract_report = validate_contract(contract)
    packet_report = validate_prediction_packet(packet, contract)
    errors = [f"contract:{error}" for error in contract_report["errors"]]
    errors.extend(f"packet:{error}" for error in packet_report["errors"])
    if not isinstance(manifest, dict):
        return {"valid": False, "errors": errors + ["manifest:object_required"]}
    if manifest.get("schema") != RUN_MANIFEST_SCHEMA:
        errors.append("manifest.schema")
    if manifest.get("version") != "1.0.0":
        errors.append("manifest.version")
    if manifest.get("contract_hash") != contract_report["contract_hash"]:
        errors.append("manifest.contract_hash")
    if manifest.get("data_kind") != packet.get("data_kind"):
        errors.append("manifest.data_kind")
    if manifest.get("dataset_hash") != packet.get("dataset_hash"):
        errors.append("manifest.dataset_hash")
    if manifest.get("prediction_packet_hash") != digest(packet):
        errors.append("manifest.prediction_packet_hash")
    runs = manifest.get("condition_runs")
    if not isinstance(runs, list):
        return {"valid": False, "errors": errors + ["manifest.condition_runs:array_required"]}
    if tuple(row.get("condition_id") for row in runs if isinstance(row, dict)) != CONDITION_IDS:
        errors.append("manifest.condition_order")
    controls = contract["model_and_resource_controls"]
    expected_samples = [row["sample_id"] for row in packet.get("model_inputs") or []]
    model_digests: set[str] = set()
    hardware: set[str] = set()
    for index, row in enumerate(runs):
        scope = f"manifest.condition_runs[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{scope}:object_required")
            continue
        condition = row.get("condition_id")
        model_used = condition != "B0_PRIOR"
        if row.get("model_used") is not model_used:
            errors.append(f"{scope}.model_used")
        if row.get("source_sample_ids") != expected_samples:
            errors.append(f"{scope}.source_sample_ids")
        if row.get("outcome_key_visible") is not False:
            errors.append(f"{scope}.outcome_key_visible")
        if row.get("retry_count") != 0 or row.get("fallback_count") != 0:
            errors.append(f"{scope}.retry_or_fallback")
        fingerprint = str(row.get("hardware_fingerprint") or "")
        if not fingerprint:
            errors.append(f"{scope}.hardware_fingerprint")
        hardware.add(fingerprint)
        if model_used:
            if row.get("model_name") != controls["model_name"]:
                errors.append(f"{scope}.model_name")
            model_digest = str(row.get("model_artifact_digest") or "")
            if len(model_digest) != 64:
                errors.append(f"{scope}.model_artifact_digest")
            model_digests.add(model_digest)
            if row.get("provider_options") != controls["provider_options"]:
                errors.append(f"{scope}.provider_options")
            if row.get("input_token_budget") != controls["per_sample_input_token_budget"]:
                errors.append(f"{scope}.input_token_budget")
            if row.get("output_token_budget") != controls["per_sample_output_token_budget"]:
                errors.append(f"{scope}.output_token_budget")
            if row.get("model_call_cap_per_sample") != 1:
                errors.append(f"{scope}.model_call_cap")
        else:
            if row.get("model_artifact_digest") != "deterministic_prior":
                errors.append(f"{scope}.deterministic_prior")
            if any(row.get(field) not in ({}, 0) for field in ("provider_options", "input_token_budget", "output_token_budget", "model_call_cap_per_sample")):
                errors.append(f"{scope}.deterministic_resources")
    if len(model_digests) != 1:
        errors.append("manifest.same_model_artifact")
    if len(hardware) != 1:
        errors.append("manifest.same_hardware")
    if manifest.get("status") == "synthetic_preflight_manifest_only":
        if manifest.get("prediction_commitment_hash") is not None:
            errors.append("manifest.synthetic_commitment_must_be_absent")
        if manifest.get("scoring_started") is not False or manifest.get("model_call_count") != 0:
            errors.append("manifest.synthetic_must_not_execute")
    return {
        "valid": not errors,
        "errors": errors,
        "condition_count": len(runs),
        "same_model_artifact": len(model_digests) == 1,
        "same_hardware": len(hardware) == 1,
        "manifest_hash": digest(manifest),
    }


def build_preflight_report(
    *, contract: dict[str, Any] | None = None, readiness: dict[str, Any] | None = None
) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    contract_report = validate_contract(contract)
    live = deepcopy(readiness or readiness_m55.build_readiness_m55())
    m55_complete = live.get("m55_pilot_complete") is True
    m56_from_m55 = live.get("m56_authorized") is True
    authorized = contract_report["valid"] and m55_complete and m56_from_m55
    report = {
        "schema": "uruha_m56_fair_comparison_preflight_report_v1",
        "status": "ready_for_private_dataset_binding" if authorized else "protocol_ready_execution_blocked",
        "contract_valid": contract_report["valid"],
        "contract_hash": contract_report["contract_hash"],
        "condition_count": contract_report["condition_count"],
        "primary_control": PRIMARY_CONTROL,
        "primary_system": PRIMARY_SYSTEM,
        "m55_pilot_complete": m55_complete,
        "m55_authorizes_m56": m56_from_m55,
        "current_execution_authorized": authorized,
        "blocking_gate": None if authorized else live.get("blocking_gate"),
        "counts": deepcopy(live.get("counts") or {}),
        "model_call_count": 0,
        "target_outcome_access_count": 0,
        "production_memory_write_count": 0,
        "formal_m56_result_created": False,
        "claim_boundary": "M56 protocol and blinded execution preflight only; no model result or Equation V1 validity claim",
    }
    report["report_hash"] = digest(report)
    return report


def render_preflight(report: dict[str, Any] | None = None) -> str:
    report = deepcopy(report or build_preflight_report())
    counts = report.get("counts") or {}
    v7_slots = list(counts.get("v7_completed_slots_by_ledger") or [0, 0])
    while len(v7_slots) < 2:
        v7_slots.append(0)
    visibility = [
        ("B0", "過去行為頻率", "無模型"),
        ("B1", "只看當前 X", "LLM"),
        ("B2", "X＋靜態人物摘要", "同模型"),
        ("B3", "X＋RAG 記憶", "同模型"),
        ("B4", "X＋完整歷史摘要", "同模型"),
        ("B5", "X＋結構化完整歷史", "主對照"),
        ("Ours", "同資料＋明確狀態轉移", "候選方程式"),
    ]
    cards = "".join(
        f'<div class="condition"><b>{html.escape(name)}</b><span>{html.escape(info)}</span><em>{html.escape(role)}</em></div>'
        for name, info, role in visibility
    )
    blocker = str(report.get("blocking_gate") or "private M55 dataset binding")
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M56 公平比較預檢</title><style>body{{margin:0;background:#08101e;color:#edf4ff;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}main{{max-width:1280px;margin:auto;padding:32px}}.hero,.panel{{background:#121d32;border:1px solid #2c4164;border-radius:20px;padding:24px;margin-bottom:18px}}.hero{{background:linear-gradient(135deg,#142c4a,#241831)}}h1{{font-size:34px;margin:.2em 0}}.warn{{color:#ff9aad;font-weight:800}}.ok{{color:#69dfc8}}.conditions{{display:grid;grid-template-columns:repeat(7,1fr);gap:8px}}.condition{{background:#0a1427;border:1px solid #344d73;border-radius:14px;padding:14px;text-align:center;min-height:100px}}.condition b,.condition span,.condition em{{display:block}}.condition span{{margin:9px 0}}.condition em{{color:#79d8c5;font-style:normal;font-size:13px}}.blind{{display:grid;grid-template-columns:1fr auto 1fr auto 1fr;gap:14px;align-items:center}}.node{{background:#0a1427;border:1px solid #38537b;border-radius:15px;padding:18px;text-align:center}}.arrow{{font-size:26px;color:#69dfc8}}.rules{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}.rule{{background:#0b1628;border-radius:14px;padding:16px;border:1px solid #344c70}}@media(max-width:900px){{.conditions,.blind,.rules{{grid-template-columns:1fr}}.arrow{{transform:rotate(90deg);text-align:center}}}}</style></head><body><main><section class="hero"><small>M56 · BEFORE MODEL GENERATION</small><h1>先把比較規則鎖死，再讓任何模型看到題目</h1><p>本頁是執行預檢，不是結果。主對照已固定為 <b>B5 vs Ours</b>，不能看完分數再換較弱 baseline。</p><p class="warn">目前 V7 {v7_slots[0]}/18 + {v7_slots[1]}/18 · V9 {counts.get('v9_independently_reviewed_event_count',0)}/30 · real rows {counts.get('temporally_valid_prediction_row_count',0)}/30 · M56 禁止</p></section><section class="panel"><h2>七組看到什麼</h2><div class="conditions">{cards}</div></section><section class="panel"><h2>答案隔離</h2><div class="blind"><div class="node"><b>M55 temporal dataset</b><br>由 coordinator 保管</div><div class="arrow">→</div><div class="node"><b>Prediction packet</b><br>只有 cutoff 前 model input<br><span class="ok">給 B0–B5/Ours</span></div><div class="arrow">→</div><div class="node"><b>SHA commitment</b><br>七組全部完成後<br>scorer 才能讀 outcome key</div></div></section><section class="panel"><h2>公平與成功規則</h2><div class="rules"><div class="rule"><b>同模型與硬體</b><p>B1–B5/Ours 使用同一 qwen3.5:9b artifact、相同 decoding、同機器。</p></div><div class="rule"><b>同 token 預算</b><p>每筆 input 8192、output 384；B5/Ours actual tokens 若差超過5%，必須補 exact-token sensitivity。</p></div><div class="rule"><b>兩個 proper score 都要贏</b><p>Brier 與 NLL 的 paired 95% CI 上界都低於0，Top-1不得落後超過5pp。</p></div></div></section><section class="panel"><h2>現在為何不能跑</h2><p class="warn">{html.escape(blocker)}</p><p>契約通過只表示未來比較可被反駁、可重現；真人資料、模型勝負、Equation V1有效性目前都仍是未知。</p></section></main></body></html>"""


def serve_demo(port: int) -> None:
    page = render_preflight().encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            return

        def do_GET(self) -> None:
            if self.path == "/health":
                body, content_type = b"ok", "text/plain; charset=utf-8"
            elif self.path in ("/", "/dashboard"):
                body, content_type = page, "text/html; charset=utf-8"
            else:
                body, content_type = b"not found", "text/plain; charset=utf-8"
                self.send_response(404)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_response(200)
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
    parser.add_argument("--port", type=int, default=7907)
    args = parser.parse_args()
    if args.serve:
        serve_demo(args.port)
        return
    if args.format == "contract":
        payload = validate_contract()
    elif args.format == "html":
        print(render_preflight())
        return
    else:
        payload = build_preflight_report()
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
