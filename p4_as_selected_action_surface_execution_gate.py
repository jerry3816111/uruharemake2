#!/usr/bin/env python3
"""Prospective fail-closed gate for P4-AS selected-action execution."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs/p4_as_selected_action_surface_execution_v1.json"


class P4ASGateError(RuntimeError):
    pass


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_contract(path=CONTRACT):
    contract = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_contract(contract)
    return contract


def load_dataset(contract):
    return json.loads((ROOT / contract["dataset"]["path"]).read_text(encoding="utf-8"))


def validate_contract(contract):
    if contract.get("schema") != "uruha_p4_as_selected_action_surface_execution_contract_v1":
        raise P4ASGateError("contract_schema_invalid")
    path = ROOT / contract["dataset"]["path"]
    if _sha(path) != contract["dataset"]["sha256"]:
        raise P4ASGateError("dataset_hash_mismatch")
    dataset = json.loads(path.read_text(encoding="utf-8"))
    count = sum(
        len(dataset.get(key) or [])
        for key in ("development_cases", "fresh_positive_cases", "fresh_control_cases")
    )
    if count != contract["dataset"]["case_count"]:
        raise P4ASGateError("case_count_mismatch")
    for name, binding in contract["predecessors"].items():
        path_text, digest = binding
        if _sha(ROOT / path_text) != digest:
            raise P4ASGateError(f"predecessor_changed:{name}")
    policy = contract["failure_policy"]
    forbidden_true = (
        "dataset_change_after_implementation_allowed",
        "gate_change_after_implementation_allowed",
        "p4_ah_detector_change_allowed",
        "candidate_score_or_order_change_allowed",
        "feedback_classifier_change_allowed",
        "p1_guard_weakening_allowed",
        "m39_or_m44_source_change_allowed",
        "surface_change_outside_exact_authority_allowed",
        "model_call_allowed",
        "factual_memory_write_allowed",
        "private_state_truth_claim_allowed",
    )
    if any(policy.get(key) is not False for key in forbidden_true):
        raise P4ASGateError("failure_policy_invalid")
    required_true = (
        "user_first_person_without_third_party_required",
        "verified_surface_before_receipt_required",
        "exact_p1_receipt_and_pending_required",
    )
    if any(policy.get(key) is not True for key in required_true):
        raise P4ASGateError("required_authority_policy_invalid")


def evaluate_offline_evidence(contract, evidence):
    validate_contract(contract)
    failures = []
    if evidence.get("schema") != "uruha_p4_as_selected_action_surface_execution_evidence_v1":
        failures.append("evidence_schema_invalid")
    if evidence.get("dataset_sha256") != contract["dataset"]["sha256"]:
        failures.append("dataset_hash_mismatch")
    for key, expected in contract["offline_gates"].items():
        if (evidence.get("metrics") or {}).get(key) != expected:
            failures.append(f"metric_mismatch:{key}")
    return {
        "schema": "uruha_p4_as_selected_action_surface_execution_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "claim_boundary": contract["claim_boundary"],
    }
