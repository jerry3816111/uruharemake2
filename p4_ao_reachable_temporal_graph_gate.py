#!/usr/bin/env python3
"""Fail-closed formal runtime gate for P4-AO."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs/p4_ao_reachable_temporal_graph_v1.json"


class P4AOGateError(RuntimeError):
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
    if contract.get("schema") != "uruha_p4_ao_reachable_temporal_graph_contract_v1":
        raise P4AOGateError("contract_schema_invalid")
    dataset = contract["dataset"]
    path = ROOT / dataset["path"]
    if _sha(path) != dataset["sha256"]:
        raise P4AOGateError("dataset_hash_mismatch")
    if len(json.loads(path.read_text(encoding="utf-8"))["turns"]) != dataset["turn_count"]:
        raise P4AOGateError("turn_count_mismatch")
    for name, binding in contract["predecessors"].items():
        path_text, digest = binding
        if _sha(ROOT / path_text) != digest:
            raise P4AOGateError(f"predecessor_changed:{name}")
    if any(contract["implementation_boundary"].values()):
        raise P4AOGateError("implementation_change_not_allowed")


def evaluate_real_evidence(contract, evidence):
    validate_contract(contract)
    dataset = load_dataset(contract)
    failures = []
    if evidence.get("schema") != "uruha_p4_ao_real_reachable_temporal_graph_evidence_v1":
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
                ("past_record_count", "expected_past_record_count", "past_count"),
                ("present_candidate_count", "expected_present_candidate_count", "candidate_count"),
                ("current_future_status", "expected_current_future_status", "future_status"),
                ("previous_outcome", "expected_previous_outcome", "previous_outcome"),
                ("trigger_path", "expected_trigger_path", "trigger_path"),
            ):
                if row.get(observed_key) != frozen[expected_key]:
                    failures.append(f"turn_{turn}:{label}")
            for fragment in frozen["required_summary_fragments"]:
                if fragment not in str(row.get("graph_summary") or ""):
                    failures.append(f"turn_{turn}:summary_missing:{fragment}")
            for key in (
                "node_before_utterance",
                "logic_graph_payload_exact",
                "final_blackboard_contains_node",
                "safari_node_visually_observed",
            ):
                if row.get(key) is not True:
                    failures.append(f"turn_{turn}:{key}_false")
            if row.get("raw_or_private_payload_leak") is not False:
                failures.append(f"turn_{turn}:payload_leak")
    for key, target in contract["real_gates"].items():
        observed_value = (evidence.get("metrics") or {}).get(key)
        if key.startswith("maximum_"):
            if observed_value is None or observed_value > target:
                failures.append(f"metric_ceiling:{key}")
        elif observed_value != target:
            failures.append(f"metric_mismatch:{key}")
    safari = evidence.get("safari") or {}
    if safari.get("actual_three_turn_acceptance") is not True:
        failures.append("safari_three_turn_missing")
    if safari.get("temporal_node_visually_observed_each_turn") is not True:
        failures.append("safari_temporal_node_missing")
    return {
        "schema": "uruha_p4_ao_real_reachable_temporal_graph_gate_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "claim_boundary": contract["claim_boundary"],
    }
