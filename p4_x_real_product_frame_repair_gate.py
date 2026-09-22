#!/usr/bin/env python3
"""Fail-closed gate for the P4-X real-product frame-repair acceptance."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_x_real_product_frame_repair_acceptance_v1.json"


class P4XGateError(RuntimeError):
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
    if contract.get("schema") != "uruha_p4_x_real_product_frame_repair_acceptance_v1":
        raise P4XGateError("contract_schema_invalid")
    dataset = contract.get("dataset") or {}
    path = ROOT / str(dataset.get("path") or "")
    if not path.is_file() or _sha256(path) != dataset.get("sha256"):
        raise P4XGateError("dataset_binding_invalid")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if len(payload.get("turns") or []) != dataset.get("turn_count"):
        raise P4XGateError("turn_count_invalid")
    predecessor = contract.get("predecessor") or {}
    for field, hash_field in (
        ("repair_module", "repair_module_sha256"),
        ("entry", "entry_sha256"),
        ("released_product_entry", "released_product_entry_sha256"),
    ):
        target = ROOT / str(predecessor.get(field) or "")
        if not target.is_file() or _sha256(target) != predecessor.get(hash_field):
            raise P4XGateError(f"predecessor_{field}_changed")
    if (contract.get("runtime") or {}).get("fresh_isolated_root") is not True:
        raise P4XGateError("runtime_isolation_invalid")
    policy = contract.get("failure_policy") or {}
    if policy.get("same_case_rerun_allowed") is not False:
        raise P4XGateError("rerun_policy_invalid")
    if policy.get("manual_candidate_injection_allowed") is not False:
        raise P4XGateError("candidate_injection_not_forbidden")


def evaluate_evidence(contract, evidence):
    validate_contract(contract)
    dataset = load_dataset(contract)
    failures = []
    if evidence.get("schema") != "uruha_p4_x_real_product_frame_repair_evidence_v1":
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
            if not all(observed.get(field) is True for field in ("p4_t_present", "p4_v_present", "p4_w_present")):
                failures.append(f"turn_{turn}_surface_trace_missing")
            violations = observed.get("p4_v_violations") or []
            changed = observed.get("p4_w_changed")
            after = observed.get("p4_w_after_violations")
            branch_ok = (bool(violations) and changed is True and after == []) or (
                not violations and changed is False and after == []
            )
            if observed.get("branch_consistent") is not True or not branch_ok:
                failures.append(f"turn_{turn}_branch_inconsistent")
            if observed.get("visible_matches_after_digest") is not True:
                failures.append(f"turn_{turn}_visible_digest_mismatch")
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
        elif field == "minimum_natural_repair_trigger_count":
            if observed is None or observed < target:
                failures.append(f"metric_floor_missed:{field}")
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
        "schema": "uruha_p4_x_real_product_frame_repair_gate_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "claim_boundary": contract["claim_boundary"],
    }


if __name__ == "__main__":
    print(json.dumps(load_contract(), ensure_ascii=False, indent=2))
