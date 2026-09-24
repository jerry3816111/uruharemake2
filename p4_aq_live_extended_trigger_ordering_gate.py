#!/usr/bin/env python3
"""Fail-closed offline gate for P4-AQ same-turn ordering repair."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs/p4_aq_live_extended_trigger_ordering_v1.json"


class P4AQGateError(RuntimeError):
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
    if contract.get("schema") != "uruha_p4_aq_live_extended_trigger_ordering_contract_v1":
        raise P4AQGateError("contract_schema_invalid")
    dataset = contract["dataset"]
    path = ROOT / dataset["path"]
    if _sha(path) != dataset["sha256"]:
        raise P4AQGateError("dataset_hash_mismatch")
    payload = json.loads(path.read_text(encoding="utf-8"))
    for key in ("development_cases", "fresh_positive_cases", "fresh_control_cases"):
        expected = dataset[key.replace("cases", "case_count")]
        if len(payload[key]) != expected:
            raise P4AQGateError(f"{key}_count_mismatch")
    for name, binding in contract["predecessors"].items():
        path_text, digest = binding
        if _sha(ROOT / path_text) != digest:
            raise P4AQGateError(f"predecessor_changed:{name}")
    boundary = contract["implementation_boundary"]
    if any(value for key, value in boundary.items() if key != "allowed_new_files"):
        raise P4AQGateError("forbidden_implementation_change_allowed")
    if contract["failure_policy"]["real_product_or_safari_execution_authorized"] is not False:
        raise P4AQGateError("real_execution_must_remain_unauthorized")


def evaluate_offline_evidence(contract, evidence):
    validate_contract(contract)
    failures = []
    if evidence.get("schema") != "uruha_p4_aq_live_extended_trigger_ordering_evidence_v1":
        failures.append("evidence_schema_invalid")
    if evidence.get("dataset_sha256") != contract["dataset"]["sha256"]:
        failures.append("dataset_hash_mismatch")
    observed = evidence.get("metrics") or {}
    for key, target in contract["offline_gates"].items():
        if observed.get(key) != target:
            failures.append(f"metric_mismatch:{key}")
    return {
        "schema": "uruha_p4_aq_live_extended_trigger_ordering_gate_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "claim_boundary": contract["claim_boundary"],
    }
