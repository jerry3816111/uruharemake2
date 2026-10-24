#!/usr/bin/env python3
"""Fail-closed gate for P4-AH multilingual trigger coverage."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_ah_multilingual_trigger_coverage_v1.json"


class P4AHGateError(RuntimeError):
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
    if contract.get("schema") != "uruha_p4_ah_multilingual_trigger_coverage_contract_v1":
        raise P4AHGateError("contract_schema_invalid")
    info = contract.get("dataset") or {}
    path = ROOT / str(info.get("path") or "")
    if not path.is_file() or _sha256(path) != info.get("sha256"):
        raise P4AHGateError("dataset_binding_invalid")
    dataset = json.loads(path.read_text(encoding="utf-8"))
    for key, count_key in (
        ("development_cases", "development_case_count"),
        ("fresh_positive_cases", "fresh_positive_case_count"),
        ("fresh_control_cases", "fresh_control_case_count"),
    ):
        if len(dataset.get(key) or []) != info.get(count_key):
            raise P4AHGateError(f"{key}_count_invalid")
    predecessor = contract.get("predecessor") or {}
    for key, hash_key in (
        ("adaptive_module", "adaptive_module_sha256"),
        ("outcome_binding_module", "outcome_binding_module_sha256"),
        ("product_entry", "product_entry_sha256"),
    ):
        target = ROOT / str(predecessor.get(key) or "")
        if not target.is_file() or _sha256(target) != predecessor.get(hash_key):
            raise P4AHGateError(f"predecessor_changed:{key}")
    boundary = contract.get("implementation_boundary") or {}
    forbidden = (
        "predecessor_change_allowed",
        "feedback_classifier_change_allowed",
        "outcome_binding_change_allowed",
        "p4_af_authority_change_allowed",
        "candidate_score_or_order_change_allowed",
        "visible_reply_change_allowed",
        "prompt_or_model_change_allowed",
        "model_call_added_allowed",
        "memory_write_added_allowed",
        "full_case_string_patch_allowed",
    )
    if any(boundary.get(key) is not False for key in forbidden):
        raise P4AHGateError("implementation_boundary_invalid")


def evaluate_evidence(contract, evidence):
    validate_contract(contract)
    dataset = load_dataset(contract)
    expected = [
        *(dict(row, partition="development_cases") for row in dataset["development_cases"]),
        *(dict(row, partition="fresh_positive_cases") for row in dataset["fresh_positive_cases"]),
        *(dict(row, partition="fresh_control_cases") for row in dataset["fresh_control_cases"]),
    ]
    observed = evidence.get("cases") or []
    failures = []
    if evidence.get("schema") != "uruha_p4_ah_multilingual_trigger_coverage_evidence_v1":
        failures.append("evidence_schema_invalid")
    if evidence.get("dataset_sha256") != contract["dataset"]["sha256"]:
        failures.append("dataset_hash_mismatch")
    if len(observed) != len(expected):
        failures.append("case_count_mismatch")
    else:
        for frozen, row in zip(expected, observed):
            case_id = frozen["case_id"]
            if row.get("case_id") != case_id or row.get("partition") != frozen["partition"]:
                failures.append(f"{case_id}:order_or_partition_mismatch")
                continue
            expected_predicate = frozen.get("expected_predicate")
            predicates = row.get("predicates") or []
            if expected_predicate and expected_predicate not in predicates:
                failures.append(f"{case_id}:predicate_missing")
            if expected_predicate is None and predicates:
                failures.append(f"{case_id}:unexpected_trigger")
            if row.get("private_state_truth_claimed") is not False:
                failures.append(f"{case_id}:private_truth_claimed")
            if row.get("base_trace_mutated") is not False:
                failures.append(f"{case_id}:base_trace_mutated")
            if row.get("visible_reply_changed") is not False or row.get("new_model_call_count") != 0:
                failures.append(f"{case_id}:visible_or_model_side_effect")
            if any(row.get(key) != 0 for key in ("fact_write_count", "profile_write_count", "episode_write_count")):
                failures.append(f"{case_id}:memory_write_added")
            if row.get("raw_dialogue_persisted") is not False:
                failures.append(f"{case_id}:raw_dialogue_persisted")
    for key, target in (contract.get("gates") or {}).items():
        if (evidence.get("metrics") or {}).get(key) != target:
            failures.append(f"metric_mismatch:{key}")
    for key, target in (contract.get("integration_gates") or {}).items():
        if (evidence.get("integration") or {}).get(key) != target:
            failures.append(f"integration_mismatch:{key}")
    return {
        "schema": "uruha_p4_ah_multilingual_trigger_coverage_gate_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "claim_boundary": contract["claim_boundary"],
    }
