#!/usr/bin/env python3
"""Fail-closed acceptance gate for P4-Y post-turn runtime graph delivery."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_y_runtime_graph_trace_delivery_acceptance_v1.json"


class P4YGateError(RuntimeError):
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
    if contract.get("schema") != "uruha_p4_y_runtime_graph_trace_delivery_acceptance_v1":
        raise P4YGateError("contract_schema_invalid")
    dataset = contract.get("dataset") or {}
    path = ROOT / str(dataset.get("path") or "")
    if not path.is_file() or _sha256(path) != dataset.get("sha256"):
        raise P4YGateError("dataset_binding_invalid")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if len(payload.get("cases") or []) != dataset.get("case_count"):
        raise P4YGateError("case_count_invalid")
    predecessor = contract.get("predecessor") or {}
    for field, hash_field in (
        ("repair_module", "repair_module_sha256"),
        ("entry", "entry_sha256"),
        ("released_product_entry", "released_product_entry_sha256"),
    ):
        target = ROOT / str(predecessor.get(field) or "")
        if not target.is_file() or _sha256(target) != predecessor.get(hash_field):
            raise P4YGateError(f"predecessor_{field}_changed")
    policy = contract.get("failure_policy") or {}
    if policy.get("missing_trace_may_be_synthesized") is not False:
        raise P4YGateError("trace_synthesis_not_forbidden")
    if policy.get("p4_x_same_case_rerun_allowed") is not False:
        raise P4YGateError("p4_x_rerun_not_forbidden")


def evaluate_evidence(contract, evidence):
    validate_contract(contract)
    dataset = load_dataset(contract)
    failures = []
    if evidence.get("schema") != "uruha_p4_y_runtime_graph_trace_delivery_evidence_v1":
        failures.append("evidence_schema_invalid")
    if evidence.get("dataset_sha256") != contract["dataset"]["sha256"]:
        failures.append("dataset_hash_mismatch")
    cases = evidence.get("cases") or []
    expected_cases = dataset["cases"]
    if len(cases) != len(expected_cases):
        failures.append("case_count_mismatch")
    else:
        for expected, observed in zip(expected_cases, cases):
            case_id = expected["case_id"]
            if observed.get("case_id") != case_id:
                failures.append(f"case_{case_id}_order_mismatch")
                continue
            if observed.get("surface_chain") != expected["expected_surface_chain"]:
                failures.append(f"case_{case_id}_surface_chain_mismatch")
            if observed.get("delivery_complete") is not expected["expected_complete"]:
                failures.append(f"case_{case_id}_completion_mismatch")
            if observed.get("visible_reply_unchanged") is not True:
                failures.append(f"case_{case_id}_visible_changed")
            if observed.get("logic_unchanged") is not True:
                failures.append(f"case_{case_id}_logic_changed")
            if observed.get("missing_trace_synthesized") is not False:
                failures.append(f"case_{case_id}_trace_synthesized")
            if observed.get("duplicate_trace_label_count") != 0:
                failures.append(f"case_{case_id}_duplicate_trace")
            if observed.get("exact_trace_payload_count") != len(expected["logic_trace_ids"]):
                failures.append(f"case_{case_id}_trace_payload_mismatch")
    metrics = evidence.get("metrics") or {}
    for field, target in contract["gates"].items():
        if metrics.get(field) != target:
            failures.append(f"metric_mismatch:{field}")
    integration = evidence.get("integration") or {}
    for field, target in contract["integration"].items():
        if integration.get(field) is not target:
            failures.append(f"integration_mismatch:{field}")
    return {
        "schema": "uruha_p4_y_runtime_graph_trace_delivery_gate_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "claim_boundary": contract["claim_boundary"],
    }


if __name__ == "__main__":
    print(json.dumps(load_contract(), ensure_ascii=False, indent=2))
