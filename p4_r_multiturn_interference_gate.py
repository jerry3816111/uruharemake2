#!/usr/bin/env python3
"""Fail-closed gate for the P4-R multi-turn interference comparison."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_r_multiturn_interference_acceptance_v1.json"


class P4RGateError(RuntimeError):
    pass


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_contract(path=CONTRACT):
    contract = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_contract(contract)
    return contract


def validate_contract(contract):
    if contract.get("schema") != "uruha_p4_r_multiturn_interference_acceptance_v1":
        raise P4RGateError("contract_schema_invalid")
    dataset = contract.get("dataset") or {}
    dataset_path = ROOT / str(dataset.get("path") or "")
    if not dataset_path.is_file() or _sha256(dataset_path) != dataset.get("sha256"):
        raise P4RGateError("dataset_binding_invalid")
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    if payload.get("case_id") != dataset.get("case_id"):
        raise P4RGateError("dataset_case_id_invalid")
    if payload.get("turn_count") != dataset.get("turn_count") or len(payload.get("turns") or []) != 12:
        raise P4RGateError("dataset_turn_count_invalid")
    if [row.get("turn") for row in payload.get("turns") or []] != list(range(1, 13)):
        raise P4RGateError("dataset_turn_order_invalid")
    novelty = (payload.get("novelty") or {}).get("repository_occurrences_before_dataset_creation") or {}
    if not novelty or any(value != 0 for value in novelty.values()):
        raise P4RGateError("dataset_novelty_invalid")
    if (contract.get("conditions") or {}).get("baseline") != "recent_five_turn_lexical_drink_mention":
        raise P4RGateError("baseline_definition_invalid")
    if (contract.get("conditions") or {}).get("system") != "p4_typed_current_preference_lineage":
        raise P4RGateError("system_definition_invalid")
    failure = contract.get("failure_policy") or {}
    if failure.get("same_case_rerun_allowed") is not False:
        raise P4RGateError("same_case_rerun_not_forbidden")


def evaluate_evidence(contract, evidence):
    validate_contract(contract)
    failures = []
    if evidence.get("schema") != "uruha_p4_r_multiturn_interference_evidence_v1":
        failures.append("evidence_schema_invalid")
    if evidence.get("case_id") != contract["dataset"]["case_id"]:
        failures.append("case_id_mismatch")
    if evidence.get("dataset_sha256") != contract["dataset"]["sha256"]:
        failures.append("dataset_hash_mismatch")
    if evidence.get("turn_count") != contract["dataset"]["turn_count"]:
        failures.append("turn_count_mismatch")

    conditions = evidence.get("conditions") or {}
    baseline = conditions.get("baseline") or {}
    system = conditions.get("system") or {}
    expected = {row["turn"]: row for row in contract["expected_recall"]}
    for name, condition in (("baseline", baseline), ("system", system)):
        rows = condition.get("recalls") or []
        if [row.get("turn") for row in rows] != contract["dataset"]["recall_turns"]:
            failures.append(f"{name}_recall_turns_mismatch")
            continue
        for row in rows:
            frozen = expected[row["turn"]]
            field = "baseline_value" if name == "baseline" else "system_value"
            if row.get("selected_value") != frozen[field]:
                failures.append(f"{name}_turn_{row['turn']}_value_mismatch")
            if name == "system":
                if row.get("visible_surface") != frozen["system_surface"]:
                    failures.append(f"system_turn_{row['turn']}_surface_mismatch")
                if row.get("status") != "resolved_unique_active_typed_current_preference":
                    failures.append(f"system_turn_{row['turn']}_status_mismatch")
                if row.get("answer_use_authorized") is not True:
                    failures.append(f"system_turn_{row['turn']}_not_authorized")

    gates = contract["gates"]
    observed_metrics = evidence.get("metrics") or {}
    for field, expected_value in gates.items():
        if observed_metrics.get(field) != expected_value:
            failures.append(f"metric_mismatch:{field}")

    state = evidence.get("final_state") or {}
    if state.get("drink_active_values") != ["よもぎ茶"]:
        failures.append("final_drink_active_value_invalid")
    if state.get("drink_historical_values") != ["月桃茶"]:
        failures.append("final_drink_historical_value_invalid")
    if state.get("drink_explicit_negative_values") != ["月桃茶"]:
        failures.append("final_drink_negative_value_invalid")
    if state.get("game_active_values") != ["cooperative games"]:
        failures.append("cross_scope_state_invalid")
    if state.get("correction_previous_link_valid") is not True:
        failures.append("correction_previous_link_invalid")
    if state.get("negative_correction_link_valid") is not True:
        failures.append("negative_correction_link_invalid")

    accounting = evidence.get("accounting") or {}
    for field, expected_value in contract["execution"].items():
        if accounting.get(field) != expected_value:
            failures.append(f"accounting_mismatch:{field}")
    return {
        "schema": "uruha_p4_r_multiturn_interference_gate_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "claim_boundary": contract["claim_boundary"],
    }


if __name__ == "__main__":
    print(json.dumps(load_contract(), ensure_ascii=False, indent=2))
