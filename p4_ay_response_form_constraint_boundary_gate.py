#!/usr/bin/env python3
"""Prospective fail-closed gate for P4-AY response-form constraints."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_ay_response_form_constraint_boundary_v1.json"


class P4AYGateError(RuntimeError):
    pass


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_contract(contract):
    if contract.get("schema") != "uruha_p4_ay_response_form_constraint_boundary_contract_v1":
        raise P4AYGateError("contract_schema_invalid")
    binding = contract.get("dataset") or {}
    path = ROOT / str(binding.get("path") or "")
    if not path.is_file() or _sha(path) != binding.get("sha256"):
        raise P4AYGateError("dataset_hash_mismatch")
    dataset = json.loads(path.read_text(encoding="utf-8"))
    partitions = {
        "development_sequences": "development_count",
        "fresh_positive_sequences": "fresh_positive_count",
        "fresh_control_sequences": "fresh_control_count",
    }
    case_count = 0
    for partition, count_key in partitions.items():
        count = len(dataset.get(partition) or [])
        case_count += count
        if count != binding.get(count_key):
            raise P4AYGateError(f"partition_count_mismatch:{partition}")
    if case_count != binding.get("case_count"):
        raise P4AYGateError("case_count_mismatch")
    predecessor = dataset.get("predecessor_dataset") or {}
    if predecessor.get("expected_preserved_link_count") != binding.get("predecessor_positive_count"):
        raise P4AYGateError("predecessor_count_mismatch")
    for name, predecessor_binding in (contract.get("predecessors") or {}).items():
        source_path, expected_sha = predecessor_binding
        if _sha(ROOT / source_path) != expected_sha:
            raise P4AYGateError(f"predecessor_changed:{name}")
    failure = contract.get("failure_policy") or {}
    forbidden_true = (
        "same_fresh_case_retry_allowed",
        "post_result_gate_or_dataset_change_allowed",
        "missing_p4_ax_authority_may_count_as_authorized",
        "genuine_task_replacement_may_inherit_prior_problem",
        "third_party_quote_meta_mismatch_or_wrong_policy_may_inherit_prior_problem",
        "p4_au_non_task_guards_may_be_bypassed",
        "offline_pass_may_rewrite_p4_ax_real_failure",
        "offline_pass_may_fix_or_hide_m45_json_failure",
    )
    if any(failure.get(key) is not False for key in forbidden_true):
        raise P4AYGateError("failure_policy_invalid")
    if failure.get("fresh_safari_case_required_after_offline_pass") is not True:
        raise P4AYGateError("fresh_safari_requirement_missing")


def load_contract(path=CONTRACT):
    contract = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_contract(contract)
    return contract


def load_dataset(contract):
    return json.loads((ROOT / contract["dataset"]["path"]).read_text(encoding="utf-8"))


def evaluate_offline_evidence(contract, evidence):
    validate_contract(contract)
    failures = []
    if evidence.get("schema") != "uruha_p4_ay_response_form_constraint_boundary_evidence_v1":
        failures.append("evidence_schema_invalid")
    if evidence.get("dataset_sha256") != contract["dataset"]["sha256"]:
        failures.append("dataset_hash_mismatch")
    for key, expected in (contract.get("offline_gates") or {}).items():
        if (evidence.get("metrics") or {}).get(key) != expected:
            failures.append(f"metric_mismatch:{key}")
    return {
        "schema": "uruha_p4_ay_response_form_constraint_boundary_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "claim_boundary": contract.get("claim_boundary"),
    }


__all__ = [
    "P4AYGateError",
    "evaluate_offline_evidence",
    "load_contract",
    "load_dataset",
    "validate_contract",
]
