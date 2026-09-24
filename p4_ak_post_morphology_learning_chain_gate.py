#!/usr/bin/env python3
"""Fail-closed gate for the P4-AK fixed post-morphology learning chain."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_ak_post_morphology_learning_chain_v1.json"


class P4AKGateError(RuntimeError):
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
    if contract.get("schema") != "uruha_p4_ak_post_morphology_learning_chain_contract_v1":
        raise P4AKGateError("contract_schema_invalid")
    info = contract["dataset"]
    path = ROOT / info["path"]
    rows = json.loads(path.read_text(encoding="utf-8"))["fresh_sequences"]
    if _sha(path) != info["sha256"] or len(rows) != info["fresh_sequence_count"]:
        raise P4AKGateError("dataset_binding_invalid")
    for key, value in contract["predecessors"].items():
        path_text, digest = value
        if _sha(ROOT / path_text) != digest:
            raise P4AKGateError(f"predecessor_changed:{key}")
    if any(value is not False for key, value in contract["implementation_boundary"].items() if key.endswith("_allowed")):
        raise P4AKGateError("implementation_boundary_invalid")


def evaluate_evidence(contract, evidence):
    validate_contract(contract)
    frozen = load_dataset(contract)["fresh_sequences"]
    observed = evidence.get("sequences") or []
    failures = []
    if evidence.get("schema") != "uruha_p4_ak_post_morphology_learning_chain_evidence_v1":
        failures.append("evidence_schema_invalid")
    if evidence.get("dataset_sha256") != contract["dataset"]["sha256"]:
        failures.append("dataset_hash_mismatch")
    if len(observed) != len(frozen):
        failures.append("sequence_count_mismatch")
    else:
        for expected, row in zip(frozen, observed):
            case_id = expected["case_id"]
            if row.get("case_id") != case_id:
                failures.append(f"{case_id}:order_mismatch")
                continue
            for key in ("typed_trigger", "eligibility_authorized", "identity_bound"):
                if row.get(key) is not True:
                    failures.append(f"{case_id}:{key}_false")
            if row.get("candidate_count") != 6:
                failures.append(f"{case_id}:candidate_count")
            if row.get("first_policy") != expected["expected_policy"]:
                failures.append(f"{case_id}:policy_mismatch")
            if row.get("outcome") != expected["expected_outcome"]:
                failures.append(f"{case_id}:outcome_mismatch")
            if row.get("replacement_policy") != expected["expected_replacement_policy"]:
                failures.append(f"{case_id}:replacement_mismatch")
            if row.get("unknown_counted_as_success") is not False:
                failures.append(f"{case_id}:unknown_success_violation")
            if row.get("raw_dialogue_persisted") is not False:
                failures.append(f"{case_id}:raw_dialogue_violation")
    for key, target in contract["gates"].items():
        if (evidence.get("metrics") or {}).get(key) != target:
            failures.append(f"metric_mismatch:{key}")
    return {
        "schema": "uruha_p4_ak_post_morphology_learning_chain_gate_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "claim_boundary": contract["claim_boundary"],
    }
