#!/usr/bin/env python3
"""Prospective fail-closed gate for P4-AR executed-action authority."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs/p4_ar_executed_action_identity_gate_v1.json"


class P4ARGateError(RuntimeError):
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
    if contract.get("schema") != "uruha_p4_ar_executed_action_identity_gate_contract_v1":
        raise P4ARGateError("contract_schema_invalid")
    path = ROOT / contract["dataset"]["path"]
    if _sha(path) != contract["dataset"]["sha256"]:
        raise P4ARGateError("dataset_hash_mismatch")
    dataset = json.loads(path.read_text(encoding="utf-8"))
    count = sum(
        len(dataset.get(key) or [])
        for key in (
            "development_cases",
            "fresh_authorized_cases",
            "fresh_blocked_cases",
            "control_cases",
        )
    )
    if count != contract["dataset"]["case_count"]:
        raise P4ARGateError("case_count_mismatch")
    for name, binding in contract["predecessors"].items():
        path_text, digest = binding
        if _sha(ROOT / path_text) != digest:
            raise P4ARGateError(f"predecessor_changed:{name}")
    policy = contract["failure_policy"]
    if any(
        policy.get(key) is not False
        for key in (
            "dataset_change_after_implementation_allowed",
            "gate_change_after_implementation_allowed",
            "weaken_p1_identity_allowed",
            "fallback_id_may_be_promoted_to_p1",
            "unexecuted_action_may_enter_outcome_verification",
            "visible_reply_change_allowed",
            "model_call_allowed",
            "factual_memory_write_allowed",
        )
    ):
        raise P4ARGateError("failure_policy_invalid")


def evaluate_offline_evidence(contract, evidence):
    validate_contract(contract)
    failures = []
    if evidence.get("schema") != "uruha_p4_ar_executed_action_identity_gate_evidence_v1":
        failures.append("evidence_schema_invalid")
    if evidence.get("dataset_sha256") != contract["dataset"]["sha256"]:
        failures.append("dataset_hash_mismatch")
    if (evidence.get("metrics") or {}) != contract["offline_gates"]:
        for key, expected in contract["offline_gates"].items():
            if (evidence.get("metrics") or {}).get(key) != expected:
                failures.append(f"metric_mismatch:{key}")
    return {
        "schema": "uruha_p4_ar_executed_action_identity_gate_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "claim_boundary": contract["claim_boundary"],
    }
