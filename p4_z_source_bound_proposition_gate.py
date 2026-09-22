#!/usr/bin/env python3
"""Fail-closed frozen-contract gate for P4-Z source-bound propositions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_z_source_bound_proposition_acceptance_v1.json"


class P4ZGateError(RuntimeError):
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
    if contract.get("schema") != "uruha_p4_z_source_bound_proposition_acceptance_v1":
        raise P4ZGateError("contract_schema_invalid")
    dataset_info = contract.get("dataset") or {}
    dataset_path = ROOT / str(dataset_info.get("path") or "")
    if not dataset_path.is_file() or _sha256(dataset_path) != dataset_info.get("sha256"):
        raise P4ZGateError("dataset_binding_invalid")
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    for partition, count_field in (
        ("development_failures", "development_case_count"),
        ("holdout_failures", "holdout_case_count"),
        ("faithful_controls", "faithful_control_count"),
        ("unsupported_controls", "unsupported_control_count"),
    ):
        if len(dataset.get(partition) or []) != dataset_info.get(count_field):
            raise P4ZGateError(f"{partition}_count_invalid")
    holdout_sources = {row["source"] for row in dataset["holdout_failures"]}
    development_sources = {row["source"] for row in dataset["development_failures"]}
    if holdout_sources & development_sources:
        raise P4ZGateError("holdout_reuses_development_source")
    if dataset.get("novelty", {}).get("p4_x_inputs_reused_as_holdout") is not False:
        raise P4ZGateError("p4_x_reuse_policy_invalid")
    if dataset.get("novelty", {}).get("p4_y_inputs_reused_as_holdout") is not False:
        raise P4ZGateError("p4_y_reuse_policy_invalid")
    for field, hash_field in (
        ("source_atom_module", "source_atom_module_sha256"),
        ("visible_repair_module", "visible_repair_module_sha256"),
        ("graph_delivery_module", "graph_delivery_module_sha256"),
        ("product_entry", "product_entry_sha256"),
    ):
        target = ROOT / str((contract.get("predecessor") or {}).get(field) or "")
        expected = (contract.get("predecessor") or {}).get(hash_field)
        if not target.is_file() or _sha256(target) != expected:
            raise P4ZGateError(f"predecessor_{field}_changed")
    policy = contract.get("failure_policy") or {}
    if policy.get("candidate_keyword_invention_allowed") is not False:
        raise P4ZGateError("candidate_invention_not_forbidden")
    if policy.get("unsupported_source_repair_allowed") is not False:
        raise P4ZGateError("unsupported_repair_not_forbidden")


def evaluate_evidence(contract, evidence):
    validate_contract(contract)
    failures = []
    if evidence.get("schema") != "uruha_p4_z_source_bound_proposition_evidence_v1":
        failures.append("evidence_schema_invalid")
    if evidence.get("dataset_sha256") != contract["dataset"]["sha256"]:
        failures.append("dataset_hash_mismatch")
    metrics = evidence.get("metrics") or {}
    for field, target in contract["implementation_gates"].items():
        if metrics.get(field) != target:
            failures.append(f"implementation_metric_mismatch:{field}")
    integration = evidence.get("integration_metrics") or {}
    for field, target in contract["integration_gates"].items():
        if integration.get(field) != target:
            failures.append(f"integration_metric_mismatch:{field}")
    return {
        "schema": "uruha_p4_z_source_bound_proposition_gate_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "claim_boundary": contract["claim_boundary"],
    }


if __name__ == "__main__":
    print(json.dumps(load_contract(), ensure_ascii=False, indent=2))
