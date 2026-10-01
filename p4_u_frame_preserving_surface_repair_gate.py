#!/usr/bin/env python3
"""Fail-closed offline gate for P4-U frame-preserving Japanese repair."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_u_frame_preserving_surface_repair_acceptance_v1.json"


class P4UGateError(RuntimeError):
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
    if contract.get("schema") != "uruha_p4_u_frame_preserving_surface_repair_acceptance_v1":
        raise P4UGateError("contract_schema_invalid")
    dataset = contract.get("dataset") or {}
    path = ROOT / str(dataset.get("path") or "")
    if not path.is_file() or _sha256(path) != dataset.get("sha256"):
        raise P4UGateError("dataset_binding_invalid")
    payload = json.loads(path.read_text(encoding="utf-8"))
    for field, partition in (
        ("development_case_count", "development_failures"),
        ("holdout_case_count", "holdout_failures"),
        ("faithful_control_count", "faithful_controls"),
    ):
        if len(payload.get(partition) or []) != dataset.get(field):
            raise P4UGateError(f"dataset_{field}_invalid")
    ids = [
        row.get("case_id")
        for partition in ("development_failures", "holdout_failures", "faithful_controls")
        for row in payload.get(partition) or []
    ]
    if len(ids) != len(set(ids)) or any(not value for value in ids):
        raise P4UGateError("dataset_case_ids_invalid")
    boundary = contract.get("implementation_boundary") or {}
    if boundary.get("frame_classifier_change_allowed") is not False:
        raise P4UGateError("classifier_boundary_invalid")
    if boundary.get("case_id_or_source_exact_match_routing_allowed") is not False:
        raise P4UGateError("case_specific_routing_not_forbidden")
    if (contract.get("failure_policy") or {}).get("dataset_expected_reply_or_gate_change_after_implementation") is not False:
        raise P4UGateError("freeze_policy_invalid")
    released = ROOT / contract["predecessor"]["released_product_entry"]
    if _sha256(released) != contract["predecessor"]["released_product_entry_sha256"]:
        raise P4UGateError("released_product_entry_changed")


def _expected_rows(dataset):
    result = {}
    for partition in ("development_failures", "holdout_failures", "faithful_controls"):
        for row in dataset[partition]:
            result[row["case_id"]] = (partition, row)
    return result


def evaluate_evidence(contract, evidence):
    validate_contract(contract)
    expected = _expected_rows(load_dataset(contract))
    failures = []
    if evidence.get("schema") != "uruha_p4_u_frame_preserving_surface_repair_evidence_v1":
        failures.append("evidence_schema_invalid")
    if evidence.get("dataset_sha256") != contract["dataset"]["sha256"]:
        failures.append("dataset_hash_mismatch")
    rows = evidence.get("cases") or []
    if [row.get("case_id") for row in rows] != list(expected):
        failures.append("case_order_or_count_invalid")
    else:
        for observed in rows:
            case_id = observed["case_id"]
            partition, frozen = expected[case_id]
            if observed.get("partition") != partition:
                failures.append(f"{case_id}:partition_mismatch")
            if observed.get("before_violations") != frozen["expected_before_violations"]:
                failures.append(f"{case_id}:before_violation_mismatch")
            if observed.get("visible_reply") != frozen["expected_reply"]:
                failures.append(f"{case_id}:visible_reply_mismatch")
            if observed.get("after_violations") != []:
                failures.append(f"{case_id}:unresolved_violation")
            if observed.get("visible_output_language") != "Japanese":
                failures.append(f"{case_id}:not_japanese")
            if observed.get("trace_contains_raw_source_or_reply") is not False:
                failures.append(f"{case_id}:raw_trace_present")
            if observed.get("model_call_added") is not False:
                failures.append(f"{case_id}:model_call_added")
            if any(observed.get(field) != 0 for field in ("fact_write_count", "profile_write_count", "episode_write_count")):
                failures.append(f"{case_id}:memory_write_added")
            if partition == "faithful_controls" and observed.get("changed") is not False:
                failures.append(f"{case_id}:faithful_control_changed")
    for field, target in contract["gates"].items():
        if (evidence.get("metrics") or {}).get(field) != target:
            failures.append(f"metric_mismatch:{field}")
    integration = evidence.get("integration") or {}
    if integration.get("additive_product_entry_installs_repair") is not True:
        failures.append("product_install_missing")
    if integration.get("runtime_graph_node_test_passed") is not True:
        failures.append("runtime_graph_node_missing")
    if integration.get("released_product_entry_hash_preserved") is not True:
        failures.append("released_product_entry_hash_not_preserved")
    return {
        "schema": "uruha_p4_u_frame_preserving_surface_repair_gate_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "claim_boundary": contract["claim_boundary"],
    }


if __name__ == "__main__":
    print(json.dumps(load_contract(), ensure_ascii=False, indent=2))
