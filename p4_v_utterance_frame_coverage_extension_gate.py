#!/usr/bin/env python3
"""Fail-closed offline gate for P4-V utterance-frame coverage extension."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_v_utterance_frame_coverage_extension_acceptance_v1.json"


class P4VGateError(RuntimeError):
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
    if contract.get("schema") != "uruha_p4_v_utterance_frame_coverage_extension_acceptance_v1":
        raise P4VGateError("contract_schema_invalid")
    dataset = contract.get("dataset") or {}
    path = ROOT / str(dataset.get("path") or "")
    if not path.is_file() or _sha256(path) != dataset.get("sha256"):
        raise P4VGateError("dataset_binding_invalid")
    payload = json.loads(path.read_text(encoding="utf-8"))
    for field, partition in (
        ("development_case_count", "development_failures"),
        ("holdout_case_count", "holdout_failures"),
        ("faithful_control_count", "faithful_controls"),
    ):
        if len(payload.get(partition) or []) != dataset.get(field):
            raise P4VGateError(f"dataset_{field}_invalid")
    ids = [
        row.get("case_id")
        for partition in ("development_failures", "holdout_failures", "faithful_controls")
        for row in payload.get(partition) or []
    ]
    if len(ids) != len(set(ids)) or any(not value for value in ids):
        raise P4VGateError("dataset_case_ids_invalid")
    predecessor = contract.get("predecessor") or {}
    for field, hash_field in (
        ("module", "module_sha256"),
        ("entry", "entry_sha256"),
        ("released_product_entry", "released_product_entry_sha256"),
    ):
        target = ROOT / str(predecessor.get(field) or "")
        if not target.is_file() or _sha256(target) != predecessor.get(hash_field):
            raise P4VGateError(f"predecessor_{field}_changed")
    boundary = contract.get("implementation_boundary") or {}
    if boundary.get("visible_reply_change_allowed") is not False:
        raise P4VGateError("visible_reply_boundary_invalid")
    if boundary.get("p4_t_module_or_entry_change_allowed") is not False:
        raise P4VGateError("p4_t_immutability_invalid")
    if boundary.get("case_id_or_source_exact_match_routing_allowed") is not False:
        raise P4VGateError("case_specific_routing_not_forbidden")
    policy = contract.get("failure_policy") or {}
    if policy.get("dataset_expected_label_or_gate_change_after_implementation") is not False:
        raise P4VGateError("freeze_policy_invalid")
    if policy.get("later_surface_repair_requires_another_fresh_holdout") is not True:
        raise P4VGateError("future_holdout_policy_invalid")


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
    if evidence.get("schema") != "uruha_p4_v_utterance_frame_coverage_extension_evidence_v1":
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
            if observed.get("base_violations") != frozen["expected_base_violations"]:
                failures.append(f"{case_id}:base_violation_mismatch")
            if observed.get("extension_evidence") != frozen["expected_extension_evidence"]:
                failures.append(f"{case_id}:extension_evidence_mismatch")
            if observed.get("violations") != frozen["expected_violations"]:
                failures.append(f"{case_id}:violation_mismatch")
            if observed.get("candidate_unchanged") is not True:
                failures.append(f"{case_id}:candidate_changed")
            if observed.get("trace_contains_raw_source_or_reply") is not False:
                failures.append(f"{case_id}:raw_trace_present")
            if observed.get("model_call_added") is not False:
                failures.append(f"{case_id}:model_call_added")
            if any(observed.get(field) != 0 for field in ("fact_write_count", "profile_write_count", "episode_write_count")):
                failures.append(f"{case_id}:memory_write_added")
    for field, target in contract["gates"].items():
        if (evidence.get("metrics") or {}).get(field) != target:
            failures.append(f"metric_mismatch:{field}")
    integration = evidence.get("integration") or {}
    if integration.get("additive_product_entry_installs_extension") is not True:
        failures.append("product_install_missing")
    if integration.get("runtime_graph_node_test_passed") is not True:
        failures.append("runtime_graph_node_missing")
    if integration.get("predecessor_hashes_preserved") is not True:
        failures.append("predecessor_hash_not_preserved")
    return {
        "schema": "uruha_p4_v_utterance_frame_coverage_extension_gate_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "claim_boundary": contract["claim_boundary"],
    }


if __name__ == "__main__":
    print(json.dumps(load_contract(), ensure_ascii=False, indent=2))
