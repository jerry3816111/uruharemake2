#!/usr/bin/env python3
"""Prospective fail-closed gate for P4-AZ previous-turn CJK ellipsis."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_az_previous_turn_cjk_ellipsis_authority_v1.json"


class P4AZGateError(RuntimeError):
    pass


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_contract(contract):
    if contract.get("schema") != "uruha_p4_az_previous_turn_cjk_ellipsis_authority_contract_v1":
        raise P4AZGateError("contract_schema_invalid")
    binding = contract.get("dataset") or {}
    path = ROOT / str(binding.get("path") or "")
    if not path.is_file() or _sha(path) != binding.get("sha256"):
        raise P4AZGateError("dataset_hash_mismatch")
    dataset = json.loads(path.read_text(encoding="utf-8"))
    partitions = {
        "development_sequences": "development_count",
        "fresh_positive_sequences": "fresh_positive_count",
        "fresh_control_sequences": "fresh_control_count",
    }
    total = 0
    for partition, count_key in partitions.items():
        count = len(dataset.get(partition) or [])
        total += count
        if count != binding.get(count_key):
            raise P4AZGateError(f"partition_count_mismatch:{partition}")
    if total != binding.get("case_count"):
        raise P4AZGateError("case_count_mismatch")
    predecessor = dataset.get("predecessor_dataset") or {}
    if predecessor.get("expected_preserved_link_count") != binding.get("predecessor_positive_count"):
        raise P4AZGateError("predecessor_count_mismatch")
    for name, predecessor_binding in (contract.get("predecessors") or {}).items():
        source_path, expected_sha = predecessor_binding
        if _sha(ROOT / source_path) != expected_sha:
            raise P4AZGateError(f"predecessor_changed:{name}")
    failure = contract.get("failure_policy") or {}
    forbidden_true = (
        "same_fresh_case_retry_allowed",
        "post_result_gate_or_dataset_change_allowed",
        "speaker_role_may_be_rewritten_to_first_person",
        "missing_exact_feedback_chain_may_count_as_authorized",
        "third_party_meta_report_hypothetical_physical_or_resolved_may_count_as_authorized",
        "p4_au_non_role_guards_may_be_bypassed",
        "offline_pass_may_rewrite_p4_ay_failure",
        "offline_pass_may_fix_or_hide_m45_json_failure",
    )
    if any(failure.get(key) is not False for key in forbidden_true):
        raise P4AZGateError("failure_policy_invalid")
    if failure.get("fresh_safari_case_required_after_offline_pass") is not True:
        raise P4AZGateError("fresh_safari_requirement_missing")


def load_contract(path=CONTRACT):
    contract = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_contract(contract)
    return contract


def load_dataset(contract):
    return json.loads((ROOT / contract["dataset"]["path"]).read_text(encoding="utf-8"))


def evaluate_offline_evidence(contract, evidence):
    validate_contract(contract)
    failures = []
    if evidence.get("schema") != "uruha_p4_az_previous_turn_cjk_ellipsis_authority_evidence_v1":
        failures.append("evidence_schema_invalid")
    if evidence.get("dataset_sha256") != contract["dataset"]["sha256"]:
        failures.append("dataset_hash_mismatch")
    for key, expected in (contract.get("offline_gates") or {}).items():
        if (evidence.get("metrics") or {}).get(key) != expected:
            failures.append(f"metric_mismatch:{key}")
    return {
        "schema": "uruha_p4_az_previous_turn_cjk_ellipsis_authority_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "claim_boundary": contract.get("claim_boundary"),
    }


__all__ = [
    "P4AZGateError",
    "evaluate_offline_evidence",
    "load_contract",
    "load_dataset",
    "validate_contract",
]
