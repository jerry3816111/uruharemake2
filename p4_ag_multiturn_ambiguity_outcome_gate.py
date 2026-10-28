#!/usr/bin/env python3
"""Fail-closed gate for P4-AG multi-turn ambiguity outcome binding."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_ag_multiturn_ambiguity_outcome_v1.json"


class P4AGGateError(RuntimeError):
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
    if contract.get("schema") != "uruha_p4_ag_multiturn_ambiguity_outcome_contract_v1":
        raise P4AGGateError("contract_schema_invalid")
    info = contract.get("dataset") or {}
    path = ROOT / str(info.get("path") or "")
    if not path.is_file() or _sha256(path) != info.get("sha256"):
        raise P4AGGateError("dataset_binding_invalid")
    dataset = json.loads(path.read_text(encoding="utf-8"))
    if len(dataset.get("development_sequences") or []) != info.get("development_sequence_count"):
        raise P4AGGateError("development_sequence_count_invalid")
    if len(dataset.get("fresh_sequences") or []) != info.get("fresh_sequence_count"):
        raise P4AGGateError("fresh_sequence_count_invalid")
    predecessor = contract.get("predecessor") or {}
    for key, hash_key in (
        ("eligibility_module", "eligibility_module_sha256"),
        ("product_entry", "product_entry_sha256"),
    ):
        target = ROOT / str(predecessor.get(key) or "")
        if not target.is_file() or _sha256(target) != predecessor.get(hash_key):
            raise P4AGGateError(f"predecessor_changed:{key}")
    boundary = contract.get("implementation_boundary") or {}
    forbidden = (
        "predecessor_change_allowed",
        "existing_feedback_classifier_change_allowed",
        "candidate_score_or_order_change_allowed",
        "visible_reply_change_allowed",
        "prompt_or_model_change_allowed",
        "model_call_added_allowed",
        "factual_memory_write_allowed",
        "unknown_counted_as_success_allowed",
    )
    if any(boundary.get(key) is not False for key in forbidden):
        raise P4AGGateError("implementation_boundary_invalid")


def evaluate_evidence(contract, evidence):
    validate_contract(contract)
    dataset = load_dataset(contract)
    expected = [
        *(dict(row, partition="development_sequences") for row in dataset["development_sequences"]),
        *(dict(row, partition="fresh_sequences") for row in dataset["fresh_sequences"]),
    ]
    observed = evidence.get("sequences") or []
    failures = []
    if evidence.get("schema") != "uruha_p4_ag_multiturn_ambiguity_outcome_evidence_v1":
        failures.append("evidence_schema_invalid")
    if evidence.get("dataset_sha256") != contract["dataset"]["sha256"]:
        failures.append("dataset_hash_mismatch")
    if len(observed) != len(expected):
        failures.append("sequence_count_mismatch")
    else:
        for frozen, row in zip(expected, observed):
            case_id = frozen["case_id"]
            if row.get("case_id") != case_id or row.get("partition") != frozen["partition"]:
                failures.append(f"{case_id}:order_or_partition_mismatch")
                continue
            if row.get("first_turn_eligible") is not True:
                failures.append(f"{case_id}:first_turn_not_eligible")
            if row.get("first_policy") != frozen["expected_first_policy"]:
                failures.append(f"{case_id}:first_policy_mismatch")
            if row.get("identity_bound") is not True:
                failures.append(f"{case_id}:identity_not_bound")
            if row.get("outcome") != frozen["expected_outcome"]:
                failures.append(f"{case_id}:outcome_mismatch")
            if row.get("replacement_policy") != frozen.get("expected_replacement_policy"):
                failures.append(f"{case_id}:replacement_policy_mismatch")
            if row.get("unknown_counted_as_success") is not False:
                failures.append(f"{case_id}:unknown_counted_as_success")
            if row.get("visible_reply_changed") is not False or row.get("new_model_call_count") != 0:
                failures.append(f"{case_id}:visible_or_model_side_effect")
            if any(row.get(key) != 0 for key in ("fact_write_count", "profile_write_count", "episode_write_count")):
                failures.append(f"{case_id}:factual_memory_write_added")
            if row.get("raw_dialogue_persisted") is not False:
                failures.append(f"{case_id}:raw_dialogue_persisted")
    for key, target in (contract.get("gates") or {}).items():
        if (evidence.get("metrics") or {}).get(key) != target:
            failures.append(f"metric_mismatch:{key}")
    for key, target in (contract.get("integration_gates") or {}).items():
        if (evidence.get("integration") or {}).get(key) != target:
            failures.append(f"integration_mismatch:{key}")
    return {
        "schema": "uruha_p4_ag_multiturn_ambiguity_outcome_gate_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "claim_boundary": contract["claim_boundary"],
    }
