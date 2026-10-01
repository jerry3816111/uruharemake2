#!/usr/bin/env python3
"""Fail-closed offline and real-runtime gates for P4-AM."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs/p4_am_real_runtime_temporal_graph_v1.json"


class P4AMGateError(RuntimeError):
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
    if contract.get("schema") != "uruha_p4_am_real_runtime_temporal_graph_contract_v1":
        raise P4AMGateError("contract_schema_invalid")
    dataset = contract["dataset"]
    path = ROOT / dataset["path"]
    if _sha(path) != dataset["sha256"]:
        raise P4AMGateError("dataset_hash_mismatch")
    if len(json.loads(path.read_text(encoding="utf-8"))["turns"]) != dataset["turn_count"]:
        raise P4AMGateError("turn_count_mismatch")
    for name, binding in contract["predecessors"].items():
        path_text, digest = binding
        if _sha(ROOT / path_text) != digest:
            raise P4AMGateError(f"predecessor_changed:{name}")
    boundary = contract["implementation_boundary"]
    if boundary.get("allowed_new_files") != [
        "uruha_runtime_temporal_graph_delivery_p4.py",
        "uruha_web_ui_product_p4_am.py",
        "p4_am_safe_isolated_product_launcher.py",
        "tests_and_evidence_only"
    ]:
        raise P4AMGateError("allowed_files_invalid")
    if any(value is not False for key, value in boundary.items() if key.endswith("_allowed")):
        raise P4AMGateError("implementation_boundary_invalid")


def _evaluate_rows(contract, evidence, schema, gate_key):
    validate_contract(contract)
    dataset = load_dataset(contract)
    failures = []
    if evidence.get("schema") != schema:
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
            if row.get("turn") != turn:
                failures.append(f"turn_{turn}:order_mismatch")
                continue
            if row.get("past_record_count") != frozen["expected_past_record_count"]:
                failures.append(f"turn_{turn}:past_count")
            if row.get("present_candidate_count") != frozen["expected_present_candidate_count"]:
                failures.append(f"turn_{turn}:candidate_count")
            if row.get("current_future_status") != frozen["expected_current_future_status"]:
                failures.append(f"turn_{turn}:future_status")
            if row.get("previous_outcome") != frozen["expected_previous_outcome"]:
                failures.append(f"turn_{turn}:previous_outcome")
            for fragment in frozen["required_summary_fragments"]:
                if fragment not in str(row.get("graph_summary") or ""):
                    failures.append(f"turn_{turn}:summary_missing:{fragment}")
            for key in ("node_before_utterance", "logic_graph_payload_exact"):
                if row.get(key) is not True:
                    failures.append(f"turn_{turn}:{key}_false")
            if row.get("raw_or_private_payload_leak") is not False:
                failures.append(f"turn_{turn}:payload_leak")
    for key, target in contract[gate_key].items():
        observed_value = (evidence.get("metrics") or {}).get(key)
        if key.startswith("maximum_"):
            if observed_value is None or observed_value > target:
                failures.append(f"metric_ceiling:{key}")
        elif observed_value != target:
            failures.append(f"metric_mismatch:{key}")
    return failures


def evaluate_offline_evidence(contract, evidence):
    failures = _evaluate_rows(
        contract,
        evidence,
        "uruha_p4_am_offline_temporal_graph_evidence_v1",
        "offline_gates",
    )
    return {
        "schema": "uruha_p4_am_offline_temporal_graph_gate_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "real_runtime_authorized": not failures,
        "claim_boundary": contract["claim_boundary"],
    }


def evaluate_real_evidence(contract, evidence):
    failures = _evaluate_rows(
        contract,
        evidence,
        "uruha_p4_am_real_runtime_temporal_graph_evidence_v1",
        "real_gates",
    )
    safari = evidence.get("safari") or {}
    if safari.get("actual_three_turn_acceptance") is not True:
        failures.append("safari_three_turn_missing")
    if safari.get("temporal_node_visually_observed_each_turn") is not True:
        failures.append("safari_temporal_node_missing")
    return {
        "schema": "uruha_p4_am_real_runtime_temporal_graph_gate_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "claim_boundary": contract["claim_boundary"],
    }
