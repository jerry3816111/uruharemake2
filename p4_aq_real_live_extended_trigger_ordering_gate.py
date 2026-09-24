#!/usr/bin/env python3
"""Fail-closed real runtime/Safari gate for P4-AQ."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs/p4_aq_real_live_extended_trigger_ordering_v1.json"


class P4AQRealGateError(RuntimeError):
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
    if contract.get("schema") != "uruha_p4_aq_real_live_extended_trigger_ordering_contract_v1":
        raise P4AQRealGateError("contract_schema_invalid")
    path = ROOT / contract["dataset"]["path"]
    if _sha(path) != contract["dataset"]["sha256"]:
        raise P4AQRealGateError("dataset_hash_mismatch")
    if len(json.loads(path.read_text(encoding="utf-8"))["turns"]) != contract["dataset"]["turn_count"]:
        raise P4AQRealGateError("turn_count_mismatch")
    for name, binding in contract["predecessors"].items():
        path_text, digest = binding
        if _sha(ROOT / path_text) != digest:
            raise P4AQRealGateError(f"predecessor_changed:{name}")
    runtime = contract["frozen_runtime"]
    if runtime != {
        "port": 7878,
        "browser": "Safari",
        "private_runtime_required": True,
        "same_case_execution_limit": 1,
    }:
        raise P4AQRealGateError("runtime_contract_changed")


def evaluate_real_evidence(contract, evidence):
    validate_contract(contract)
    dataset = load_dataset(contract)
    failures = []
    if evidence.get("schema") != "uruha_p4_aq_real_live_extended_trigger_ordering_evidence_v1":
        failures.append("evidence_schema_invalid")
    if evidence.get("dataset_sha256") != contract["dataset"]["sha256"]:
        failures.append("dataset_hash_mismatch")
    observed = evidence.get("turns") or []
    expected = dataset["turns"]
    if len(observed) != len(expected):
        failures.append("turn_count_mismatch")
    else:
        for frozen, row in zip(expected, observed):
            turn = frozen["turn"]
            for observed_key, expected_key, label in (
                ("trigger_path", "expected_trigger_path", "trigger_path"),
                ("ordering_status", "expected_ordering_status", "ordering_status"),
                ("prediction_sequence", "expected_prediction_sequence", "prediction_sequence"),
                ("shadow_identity_floor", "expected_shadow_identity_floor", "shadow_identity_floor"),
                ("past_record_count", "expected_past_record_count", "past_count"),
                ("present_candidate_count", "expected_present_candidate_count", "candidate_count"),
                ("current_future_status", "expected_current_future_status", "future_status"),
                ("previous_outcome", "expected_previous_outcome", "previous_outcome"),
            ):
                if row.get(observed_key) != frozen[expected_key]:
                    failures.append(f"turn_{turn}:{label}")
            for fragment in frozen["required_summary_fragments"]:
                if fragment not in str(row.get("graph_summary") or ""):
                    failures.append(f"turn_{turn}:summary_missing:{fragment}")
            for key in (
                "all_required_nodes_before_utterance",
                "logic_runtime_graph_payload_exact",
                "safari_ordering_node_visually_observed",
                "safari_temporal_node_visually_observed",
                "shadow_pending_identity_exact",
            ):
                if row.get(key) is not True:
                    failures.append(f"turn_{turn}:{key}_false")
            if row.get("raw_or_private_payload_leak") is not False:
                failures.append(f"turn_{turn}:payload_leak")
    for key, target in contract["real_gates"].items():
        value = (evidence.get("metrics") or {}).get(key)
        if key.startswith("maximum_"):
            if value is None or value > target:
                failures.append(f"metric_ceiling:{key}")
        elif value != target:
            failures.append(f"metric_mismatch:{key}")
    safari = evidence.get("safari") or {}
    if safari.get("actual_three_turn_acceptance") is not True:
        failures.append("safari_three_turn_missing")
    if safari.get("ordering_and_temporal_nodes_visually_observed_each_turn") is not True:
        failures.append("safari_required_nodes_missing")
    return {
        "schema": "uruha_p4_aq_real_live_extended_trigger_ordering_gate_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "claim_boundary": contract["claim_boundary"],
    }
