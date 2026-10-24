#!/usr/bin/env python3
"""Fail-closed gate for P4-AA real-product source proposition acceptance."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_aa_real_product_source_proposition_acceptance_v1.json"


class P4AARealGateError(RuntimeError):
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
    if contract.get("schema") != "uruha_p4_aa_real_product_source_proposition_acceptance_v1":
        raise P4AARealGateError("contract_schema_invalid")
    dataset_info = contract.get("dataset") or {}
    dataset_path = ROOT / str(dataset_info.get("path") or "")
    if not dataset_path.is_file() or _sha256(dataset_path) != dataset_info.get("sha256"):
        raise P4AARealGateError("dataset_binding_invalid")
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    if len(dataset.get("turns") or []) != dataset_info.get("turn_count"):
        raise P4AARealGateError("turn_count_invalid")
    for field, hash_field in (
        ("proposition_module", "proposition_module_sha256"),
        ("entry", "entry_sha256"),
    ):
        target = ROOT / str((contract.get("predecessor") or {}).get(field) or "")
        if not target.is_file() or _sha256(target) != (contract.get("predecessor") or {}).get(hash_field):
            raise P4AARealGateError(f"predecessor_{field}_changed")
    policy = contract.get("failure_policy") or {}
    if policy.get("same_case_rerun_allowed") is not False:
        raise P4AARealGateError("rerun_policy_invalid")
    if policy.get("manual_candidate_injection_allowed") is not False:
        raise P4AARealGateError("candidate_injection_not_forbidden")
    if policy.get("manual_trace_injection_allowed") is not False:
        raise P4AARealGateError("trace_injection_not_forbidden")


def evaluate_evidence(contract, evidence):
    validate_contract(contract)
    dataset = load_dataset(contract)
    failures = []
    if evidence.get("schema") != "uruha_p4_aa_real_product_source_proposition_evidence_v1":
        failures.append("evidence_schema_invalid")
    if evidence.get("case_id") != contract["dataset"]["case_id"]:
        failures.append("case_id_mismatch")
    if evidence.get("dataset_sha256") != contract["dataset"]["sha256"]:
        failures.append("dataset_hash_mismatch")
    turns = evidence.get("turns") or []
    expected_turns = dataset["turns"]
    if len(turns) != len(expected_turns):
        failures.append("turn_count_mismatch")
    else:
        for expected, observed in zip(expected_turns, turns):
            turn = expected["turn"]
            if observed.get("turn") != turn or observed.get("input") != expected["input"]:
                failures.append(f"turn_{turn}_input_or_order_mismatch")
            if observed.get("visible_output_language") != "Japanese":
                failures.append(f"turn_{turn}_not_japanese")
            if not observed.get("episode_id"):
                failures.append(f"turn_{turn}_episode_missing")
            if observed.get("graph_visible") is not True:
                failures.append(f"turn_{turn}_graph_missing")
            if observed.get("surface_chain") != contract["surface_chain"]:
                failures.append(f"turn_{turn}_surface_chain_mismatch")
            if not all(observed.get(field) is True for field in (
                "logic_p4_t_present", "logic_p4_v_present", "logic_p4_w_present", "logic_p4_z_present",
                "graph_p4_t_present", "graph_p4_v_present", "graph_p4_w_present", "graph_p4_z_present",
            )):
                failures.append(f"turn_{turn}_trace_missing")
            if observed.get("exact_logic_to_graph_payload_count") != 4:
                failures.append(f"turn_{turn}_payload_mismatch")
            if observed.get("p4_z_status") not in expected["expected_p4_z_status"]:
                failures.append(f"turn_{turn}_p4_z_status_mismatch")
            if expected.get("expected_visible_output") is not None:
                if observed.get("visible_output") != expected["expected_visible_output"]:
                    failures.append(f"turn_{turn}_visible_output_mismatch")
                if observed.get("p4_z_violations_after") != []:
                    failures.append(f"turn_{turn}_source_proposition_unresolved")
            else:
                if observed.get("p4_z_changed") is not False:
                    failures.append(f"turn_{turn}_unsupported_source_changed")
            if observed.get("p4_i_selected") is not False:
                failures.append(f"turn_{turn}_typed_write_detected")
            if float(observed.get("end_to_end_seconds") or 0) > contract["gates"]["maximum_turn_latency_seconds"]:
                failures.append(f"turn_{turn}_latency_target_missed")
    metrics = evidence.get("metrics") or {}
    for field, target in contract["gates"].items():
        observed = metrics.get(field)
        if field.startswith("maximum_"):
            if observed is None or observed > target:
                failures.append(f"metric_ceiling_exceeded:{field}")
        elif observed != target:
            failures.append(f"metric_mismatch:{field}")
    accounting = evidence.get("accounting") or {}
    for field, target in contract["accounting"].items():
        observed = accounting.get(field)
        if field.endswith("_maximum"):
            if observed is None or observed > target:
                failures.append(f"accounting_ceiling_exceeded:{field}")
        elif observed != target:
            failures.append(f"accounting_mismatch:{field}")
    safari = evidence.get("safari") or {}
    if safari.get("actual_four_turn_acceptance") is not True:
        failures.append("safari_acceptance_missing")
    if safari.get("runtime_node_graph_observed_after_every_turn") is not True:
        failures.append("safari_graph_observation_missing")
    return {
        "schema": "uruha_p4_aa_real_product_source_proposition_gate_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "claim_boundary": contract["claim_boundary"],
    }


if __name__ == "__main__":
    print(json.dumps(load_contract(), ensure_ascii=False, indent=2))
