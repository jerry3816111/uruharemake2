#!/usr/bin/env python3
"""Frozen gate for P4-AB presentation-only P4-Z graph summaries."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_ab_source_proposition_graph_summary_acceptance_v1.json"


class P4ABGraphSummaryGateError(RuntimeError):
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
    if contract.get("schema") != "uruha_p4_ab_source_proposition_graph_summary_acceptance_v1":
        raise P4ABGraphSummaryGateError("contract_schema_invalid")
    dataset_info = contract.get("dataset") or {}
    dataset_path = ROOT / str(dataset_info.get("path") or "")
    if not dataset_path.is_file() or _sha256(dataset_path) != dataset_info.get("sha256"):
        raise P4ABGraphSummaryGateError("dataset_binding_invalid")
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    if len(dataset.get("cases") or []) != dataset_info.get("case_count"):
        raise P4ABGraphSummaryGateError("case_count_invalid")
    proposition = contract.get("predecessor") or {}
    proposition_path = ROOT / str(proposition.get("module") or "")
    if not proposition_path.is_file() or _sha256(proposition_path) != proposition.get("sha256"):
        raise P4ABGraphSummaryGateError("predecessor_changed")
    policy = contract.get("change_policy") or {}
    for field in (
        "visible_reply_change_allowed",
        "p4_z_logic_change_allowed",
        "trace_detail_change_allowed",
        "model_call_allowed",
        "memory_write_allowed",
        "raw_source_or_reply_in_summary_allowed",
    ):
        if policy.get(field) is not False:
            raise P4ABGraphSummaryGateError(f"policy_invalid:{field}")


def evaluate_evidence(contract, evidence):
    validate_contract(contract)
    failures = []
    if evidence.get("schema") != "uruha_p4_ab_source_proposition_graph_summary_evidence_v1":
        failures.append("evidence_schema_invalid")
    if evidence.get("dataset_sha256") != contract["dataset"]["sha256"]:
        failures.append("dataset_hash_mismatch")
    metrics = evidence.get("metrics") or {}
    for field, target in contract["gates"].items():
        if metrics.get(field) != target:
            failures.append(f"metric_mismatch:{field}")
    return {
        "schema": "uruha_p4_ab_source_proposition_graph_summary_gate_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "claim_boundary": contract["claim_boundary"],
    }
