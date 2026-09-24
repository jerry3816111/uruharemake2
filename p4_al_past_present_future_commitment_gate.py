#!/usr/bin/env python3
"""Fail-closed gate for P4-AL temporal commitment evidence."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs/p4_al_past_present_future_commitment_v1.json"


class P4ALGateError(RuntimeError):
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
    if contract.get("schema") != "uruha_p4_al_past_present_future_commitment_contract_v1":
        raise P4ALGateError("contract_schema_invalid")
    dataset = contract["dataset"]
    path = ROOT / dataset["path"]
    if _sha(path) != dataset["sha256"]:
        raise P4ALGateError("dataset_hash_mismatch")
    if len(json.loads(path.read_text(encoding="utf-8"))["cases"]) != dataset["case_count"]:
        raise P4ALGateError("dataset_count_mismatch")
    for name, binding in contract["bindings"].items():
        path_text, digest = binding
        if _sha(ROOT / path_text) != digest:
            raise P4ALGateError(f"binding_changed:{name}")
    if any(value is not False for key, value in contract["implementation_boundary"].items() if key.endswith("_allowed")):
        raise P4ALGateError("implementation_boundary_invalid")


def evaluate_evidence(contract, evidence):
    validate_contract(contract)
    failures = []
    if evidence.get("schema") != "uruha_p4_al_past_present_future_commitment_evidence_v1":
        failures.append("evidence_schema_invalid")
    if evidence.get("dataset_sha256") != contract["dataset"]["sha256"]:
        failures.append("dataset_hash_mismatch")
    expected = load_dataset(contract)["cases"]
    observed = evidence.get("cases") or []
    if len(observed) != len(expected):
        failures.append("case_count_mismatch")
    else:
        for frozen, row in zip(expected, observed):
            case_id = frozen["case_id"]
            if row.get("case_id") != case_id:
                failures.append(f"{case_id}:order_mismatch")
                continue
            if row.get("outcome") != frozen["expected_outcome"]:
                failures.append(f"{case_id}:outcome_mismatch")
            if row.get("replacement_policy") != frozen["expected_replacement_policy"]:
                failures.append(f"{case_id}:replacement_mismatch")
            for key in (
                "past_strictly_before_present",
                "outcome_absent_before_unlock",
                "commitment_hash_valid",
                "exact_identity_bound",
                "next_past_record_created",
            ):
                if row.get(key) is not True:
                    failures.append(f"{case_id}:{key}_false")
            if row.get("raw_or_private_content_persisted") is not False:
                failures.append(f"{case_id}:raw_or_private_content_violation")
    for key, target in contract["gates"].items():
        if (evidence.get("metrics") or {}).get(key) != target:
            failures.append(f"metric_mismatch:{key}")
    return {
        "schema": "uruha_p4_al_past_present_future_commitment_gate_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "claim_boundary": contract["claim_boundary"],
    }
