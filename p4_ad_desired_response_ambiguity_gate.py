#!/usr/bin/env python3
"""Fail-closed gate for the P4-AD desired-response ambiguity ledger."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_ad_desired_response_ambiguity_v1.json"


class P4ADGateError(RuntimeError):
    pass


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_contract(path=CONTRACT):
    contract = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_contract(contract)
    return contract


def load_dataset(contract):
    return json.loads((ROOT / contract["dataset"]["path"]).read_text(encoding="utf-8"))


def validate_contract(contract):
    if contract.get("schema") != "uruha_p4_ad_desired_response_ambiguity_contract_v1":
        raise P4ADGateError("contract_schema_invalid")
    dataset_info = contract.get("dataset") or {}
    dataset_path = ROOT / str(dataset_info.get("path") or "")
    if not dataset_path.is_file() or _sha256(dataset_path) != dataset_info.get("sha256"):
        raise P4ADGateError("dataset_binding_invalid")
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    for key, count_key in (
        ("development_cases", "development_case_count"),
        ("holdout_ambiguity_cases", "holdout_ambiguity_case_count"),
        ("literal_controls", "literal_control_count"),
    ):
        if len(dataset.get(key) or []) != dataset_info.get(count_key):
            raise P4ADGateError(f"{key}_count_invalid")
    for binding, row in (contract.get("predecessor_bindings") or {}).items():
        target = ROOT / str((row or {}).get("path") or "")
        if not target.is_file() or _sha256(target) != (row or {}).get("sha256"):
            raise P4ADGateError(f"predecessor_changed:{binding}")
    boundary = contract.get("implementation_boundary") or {}
    forbidden_true = (
        "existing_adaptive_model_change_allowed",
        "existing_human_equation_change_allowed",
        "released_product_entry_change_allowed",
        "core_graph_renderer_change_allowed",
        "visible_reply_change_allowed",
        "prompt_change_allowed",
        "model_or_generation_parameter_change_allowed",
        "new_model_call_allowed",
        "factual_profile_or_episode_write_allowed",
        "candidate_action_score_may_be_called_private_truth_probability",
        "selected_action_may_be_called_private_truth",
    )
    if any(boundary.get(key) is not False for key in forbidden_true):
        raise P4ADGateError("implementation_boundary_invalid")
    failure = contract.get("failure_policy") or {}
    if failure.get("maximum_informed_correction_batches") != 2:
        raise P4ADGateError("correction_budget_invalid")
    if failure.get("real_product_or_safari_execution_authorized_by_this_contract") is not False:
        raise P4ADGateError("real_execution_boundary_invalid")


def _expected_rows(dataset):
    return [
        *(dict(row, partition="development_cases") for row in dataset["development_cases"]),
        *(dict(row, partition="holdout_ambiguity_cases") for row in dataset["holdout_ambiguity_cases"]),
        *(dict(row, partition="literal_controls") for row in dataset["literal_controls"]),
    ]


def evaluate_evidence(contract, evidence):
    validate_contract(contract)
    dataset = load_dataset(contract)
    failures = []
    if evidence.get("schema") != "uruha_p4_ad_desired_response_ambiguity_evidence_v1":
        failures.append("evidence_schema_invalid")
    if evidence.get("dataset_sha256") != contract["dataset"]["sha256"]:
        failures.append("dataset_hash_mismatch")
    expected_rows = _expected_rows(dataset)
    observed_rows = evidence.get("cases") or []
    if len(observed_rows) != len(expected_rows):
        failures.append("case_count_mismatch")
    else:
        for expected, observed in zip(expected_rows, observed_rows):
            case_id = expected["case_id"]
            if observed.get("case_id") != case_id or observed.get("partition") != expected["partition"]:
                failures.append(f"{case_id}:order_or_partition_mismatch")
                continue
            if observed.get("status") != expected["expected_status"]:
                failures.append(f"{case_id}:status_mismatch")
            if expected.get("expected_selected_action_mode") is not None:
                if observed.get("selected_action_mode") != expected["expected_selected_action_mode"]:
                    failures.append(f"{case_id}:selected_action_mismatch")
            required = set(expected.get("required_candidate_modes") or [])
            if not required.issubset(set(observed.get("candidate_modes") or [])):
                failures.append(f"{case_id}:required_candidate_modes_missing")
            if expected["partition"] == "literal_controls" and observed.get("candidate_count") != 0:
                failures.append(f"{case_id}:literal_control_false_positive")
            if expected["partition"] != "literal_controls":
                if observed.get("candidate_contract_passed") is not True:
                    failures.append(f"{case_id}:candidate_contract_failed")
                if observed.get("private_reason_status") not in {
                    "unknown_not_observed",
                    "unknown_beyond_explicit_response_form",
                }:
                    failures.append(f"{case_id}:private_unknown_boundary_missing")
            if observed.get("selected_action_is_private_truth_commitment") is not False:
                failures.append(f"{case_id}:private_truth_committed")
            if observed.get("trace_contains_raw_input") is not False:
                failures.append(f"{case_id}:raw_input_persisted")
            if observed.get("visible_reply_changed") is not False:
                failures.append(f"{case_id}:visible_reply_changed")
            if observed.get("new_model_call_count") != 0:
                failures.append(f"{case_id}:model_call_added")
            if any(observed.get(key) != 0 for key in ("fact_write_count", "profile_write_count", "episode_write_count")):
                failures.append(f"{case_id}:memory_write_added")
    for field, target in (contract.get("gates") or {}).items():
        if (evidence.get("metrics") or {}).get(field) != target:
            failures.append(f"metric_mismatch:{field}")
    for field, target in (contract.get("integration_gates") or {}).items():
        if (evidence.get("integration") or {}).get(field) != target:
            failures.append(f"integration_mismatch:{field}")
    return {
        "schema": "uruha_p4_ad_desired_response_ambiguity_gate_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "claim_boundary": contract["claim_boundary"],
    }
