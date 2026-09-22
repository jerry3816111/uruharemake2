#!/usr/bin/env python3
"""Fail-closed gate for P4-AE fresh post-correction generalization."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_ae_fresh_ambiguity_generalization_v1.json"


class P4AEGateError(RuntimeError):
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
    if contract.get("schema") != "uruha_p4_ae_fresh_ambiguity_generalization_contract_v1":
        raise P4AEGateError("contract_schema_invalid")
    info = contract.get("dataset") or {}
    path = ROOT / str(info.get("path") or "")
    if not path.is_file() or _sha256(path) != info.get("sha256"):
        raise P4AEGateError("dataset_binding_invalid")
    dataset = json.loads(path.read_text(encoding="utf-8"))
    if len(dataset.get("ambiguity_cases") or []) != info.get("ambiguity_case_count"):
        raise P4AEGateError("ambiguity_count_invalid")
    if len(dataset.get("near_miss_controls") or []) != info.get("near_miss_control_count"):
        raise P4AEGateError("control_count_invalid")
    for path_key, hash_key in (
        ("ledger_module", "ledger_module_sha256"),
        ("product_entry", "product_entry_sha256"),
        ("predecessor_contract", "predecessor_contract_sha256"),
    ):
        target = ROOT / str((contract.get("frozen_implementation") or {}).get(path_key) or "")
        if not target.is_file() or _sha256(target) != (contract.get("frozen_implementation") or {}).get(hash_key):
            raise P4AEGateError(f"frozen_implementation_changed:{path_key}")
    execution = contract.get("execution") or {}
    if execution.get("maximum_executions") != 1 or execution.get("retry_count") != 0:
        raise P4AEGateError("execution_budget_invalid")
    if any(execution.get(key) is not False for key in (
        "case_or_gate_change_after_result_allowed",
        "implementation_change_after_result_allowed",
        "real_product_or_safari_execution_authorized",
    )):
        raise P4AEGateError("execution_boundary_invalid")


def evaluate_evidence(contract, evidence):
    validate_contract(contract)
    dataset = load_dataset(contract)
    failures = []
    if evidence.get("schema") != "uruha_p4_ae_fresh_ambiguity_generalization_evidence_v1":
        failures.append("evidence_schema_invalid")
    if evidence.get("dataset_sha256") != contract["dataset"]["sha256"]:
        failures.append("dataset_hash_mismatch")
    if evidence.get("execution_count") != 1:
        failures.append("execution_count_mismatch")
    expected = [
        *(dict(row, partition="ambiguity_cases") for row in dataset["ambiguity_cases"]),
        *(dict(row, partition="near_miss_controls") for row in dataset["near_miss_controls"]),
    ]
    observed = evidence.get("cases") or []
    if len(observed) != len(expected):
        failures.append("case_count_mismatch")
    else:
        for frozen, row in zip(expected, observed):
            case_id = frozen["case_id"]
            if row.get("case_id") != case_id or row.get("partition") != frozen["partition"]:
                failures.append(f"{case_id}:order_or_partition_mismatch")
                continue
            if row.get("status") != frozen["expected_status"]:
                failures.append(f"{case_id}:status_mismatch")
            if frozen.get("expected_selected_action_mode") is not None and row.get("selected_action_mode") != frozen["expected_selected_action_mode"]:
                failures.append(f"{case_id}:selected_action_mismatch")
            if not set(frozen.get("required_candidate_modes") or []).issubset(set(row.get("candidate_modes") or [])):
                failures.append(f"{case_id}:candidate_modes_missing")
            if frozen["partition"] == "ambiguity_cases":
                if row.get("candidate_contract_passed") is not True:
                    failures.append(f"{case_id}:candidate_contract_failed")
                if row.get("private_reason_status") != "unknown_not_observed":
                    failures.append(f"{case_id}:unknown_boundary_missing")
            elif row.get("candidate_count") != 0:
                failures.append(f"{case_id}:near_miss_false_positive")
            if row.get("selected_action_is_private_truth_commitment") is not False:
                failures.append(f"{case_id}:private_truth_committed")
            if row.get("trace_contains_raw_input") is not False or row.get("visible_reply_changed") is not False:
                failures.append(f"{case_id}:raw_or_visible_side_effect")
            if row.get("new_model_call_count") != 0:
                failures.append(f"{case_id}:model_call_added")
            if any(row.get(key) != 0 for key in ("fact_write_count", "profile_write_count", "episode_write_count")):
                failures.append(f"{case_id}:memory_write_added")
    for key, target in contract["gates"].items():
        if (evidence.get("metrics") or {}).get(key) != target:
            failures.append(f"metric_mismatch:{key}")
    accounting = evidence.get("accounting") or {}
    if accounting.get("retry_count") != 0 or accounting.get("fallback_count") != 0:
        failures.append("retry_or_fallback_used")
    return {
        "schema": "uruha_p4_ae_fresh_ambiguity_generalization_gate_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "claim_boundary": contract["claim_boundary"],
    }
