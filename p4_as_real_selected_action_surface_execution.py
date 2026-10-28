#!/usr/bin/env python3
"""One-shot real runtime/Safari gate for P4-AS."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs/p4_as_real_selected_action_surface_execution_v1.json"


class P4ASRealGateError(RuntimeError):
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
    if contract.get("schema") != "uruha_p4_as_real_selected_action_surface_execution_contract_v1":
        raise P4ASRealGateError("contract_schema_invalid")
    path = ROOT / contract["dataset"]["path"]
    if _sha(path) != contract["dataset"]["sha256"]:
        raise P4ASRealGateError("dataset_hash_mismatch")
    for name, binding in contract["predecessors"].items():
        path_text, digest = binding
        if _sha(ROOT / path_text) != digest:
            raise P4ASRealGateError(f"predecessor_changed:{name}")
    if contract["frozen_runtime"] != {
        "port": 7882,
        "browser": "Safari",
        "private_runtime_required": True,
        "same_case_execution_limit": 1,
    }:
        raise P4ASRealGateError("runtime_contract_changed")


def evaluate_real_evidence(contract, evidence):
    validate_contract(contract)
    dataset = load_dataset(contract)
    failures = []
    if evidence.get("schema") != "uruha_p4_as_real_selected_action_surface_execution_evidence_v1":
        failures.append("evidence_schema_invalid")
    if evidence.get("dataset_sha256") != contract["dataset"]["sha256"]:
        failures.append("dataset_hash_mismatch")
    row = evidence.get("turn") or {}
    expectations = {
        "p4_as_status": dataset["expected_p4_as_status"],
        "selected_policy": dataset["expected_selected_policy"],
        "visible_reply": dataset["expected_visible_reply"],
        "m44_status": dataset["expected_m44_status"],
        "p4_ar_status": dataset["expected_p4_ar_status"],
        "ambiguity_candidate_count": dataset["expected_ambiguity_candidate_count"],
        "verification_binding_status": dataset["expected_verification_binding_status"],
        "verification_binding_candidate_count": dataset["expected_verification_binding_candidate_count"],
        "temporal_present_candidate_count": dataset["expected_temporal_present_candidate_count"],
        "temporal_future_status": dataset["expected_temporal_future_status"],
    }
    for key, expected in expectations.items():
        if row.get(key) != expected:
            failures.append(f"turn:{key}")
    if row.get("m39_status") not in dataset["expected_m39_statuses"]:
        failures.append("turn:m39_status")
    for fragment in dataset["required_summary_fragments"]:
        if fragment not in str(row.get("graph_summary") or ""):
            failures.append(f"turn:summary_missing:{fragment}")
    for key in (
        "visible_reply_is_japanese",
        "durable_episode_written",
        "graph_visible",
        "surface_verified",
        "receipt_identity_exact",
        "p4_ar_authorized",
        "p1_identity_exact",
        "required_nodes_before_utterance",
        "logic_runtime_graph_payload_exact",
        "safari_p4_as_node_visually_observed",
        "safari_p4_ar_node_visually_observed",
        "safari_temporal_node_visually_observed",
    ):
        if row.get(key) is not True:
            failures.append(f"turn:{key}_false")
    if row.get("raw_or_private_payload_leak") is not False:
        failures.append("turn:payload_leak")
    for key, target in contract["real_gates"].items():
        value = (evidence.get("metrics") or {}).get(key)
        if key.startswith("maximum_"):
            if value is None or value > target:
                failures.append(f"metric_ceiling:{key}")
        elif value != target:
            failures.append(f"metric_mismatch:{key}")
    safari = evidence.get("safari") or {}
    if safari.get("actual_one_turn_acceptance") is not True:
        failures.append("safari_turn_missing")
    if safari.get("required_nodes_visually_observed") is not True:
        failures.append("safari_required_nodes_missing")
    return {
        "schema": "uruha_p4_as_real_selected_action_surface_execution_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "claim_boundary": contract["claim_boundary"],
    }


__all__ = ["evaluate_real_evidence", "load_contract", "load_dataset", "validate_contract"]
