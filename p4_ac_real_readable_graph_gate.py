#!/usr/bin/env python3
"""Fail-closed gate for P4-AC real Safari readable-graph delivery."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_ac_real_readable_graph_acceptance_v1.json"


class P4ACRealGraphGateError(RuntimeError):
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
    if contract.get("schema") != "uruha_p4_ac_real_readable_graph_acceptance_v1":
        raise P4ACRealGraphGateError("contract_schema_invalid")
    dataset_info = contract.get("dataset") or {}
    dataset_path = ROOT / str(dataset_info.get("path") or "")
    if not dataset_path.is_file() or _sha256(dataset_path) != dataset_info.get("sha256"):
        raise P4ACRealGraphGateError("dataset_binding_invalid")
    if len(json.loads(dataset_path.read_text(encoding="utf-8")).get("turns") or []) != dataset_info.get("turn_count"):
        raise P4ACRealGraphGateError("turn_count_invalid")
    for field, hash_field in (
        ("product_entry", "product_entry_sha256"),
        ("summary_module", "summary_module_sha256"),
        ("proposition_module", "proposition_module_sha256"),
    ):
        target = ROOT / str((contract.get("predecessor") or {}).get(field) or "")
        if not target.is_file() or _sha256(target) != (contract.get("predecessor") or {}).get(hash_field):
            raise P4ACRealGraphGateError(f"predecessor_{field}_changed")
    policy = contract.get("failure_policy") or {}
    if policy.get("same_case_rerun_allowed") is not False or policy.get("gate_change_after_result_allowed") is not False:
        raise P4ACRealGraphGateError("failure_policy_invalid")


def evaluate_evidence(contract, evidence):
    validate_contract(contract)
    dataset = load_dataset(contract)
    failures = []
    if evidence.get("schema") != "uruha_p4_ac_real_readable_graph_evidence_v1":
        failures.append("evidence_schema_invalid")
    if evidence.get("case_id") != dataset["case_id"]:
        failures.append("case_id_mismatch")
    if evidence.get("dataset_sha256") != contract["dataset"]["sha256"]:
        failures.append("dataset_hash_mismatch")
    turns = evidence.get("turns") or []
    if len(turns) != len(dataset["turns"]):
        failures.append("turn_count_mismatch")
    else:
        for expected, observed in zip(dataset["turns"], turns):
            turn = expected["turn"]
            if observed.get("turn") != turn or observed.get("input") != expected["input"]:
                failures.append(f"turn_{turn}_input_or_order_mismatch")
            if observed.get("visible_output_language") != "Japanese":
                failures.append(f"turn_{turn}_not_japanese")
            if not observed.get("episode_id"):
                failures.append(f"turn_{turn}_episode_missing")
            if observed.get("surface_chain") != contract["surface_chain"]:
                failures.append(f"turn_{turn}_surface_chain_mismatch")
            if observed.get("graph_visible") is not True or observed.get("p4_z_node_visible") is not True:
                failures.append(f"turn_{turn}_graph_node_missing")
            if observed.get("graph_summary") != observed.get("logic_derived_summary"):
                failures.append(f"turn_{turn}_summary_logic_mismatch")
            if observed.get("graph_summary") in ("18 fields", "22 fields"):
                failures.append(f"turn_{turn}_generic_summary_not_replaced")
            for fragment in expected["required_summary_fragments"]:
                if fragment not in str(observed.get("graph_summary") or ""):
                    failures.append(f"turn_{turn}_summary_fragment_missing:{fragment}")
            if expected["expected_visible_output"] is not None:
                if observed.get("visible_output") != expected["expected_visible_output"]:
                    failures.append(f"turn_{turn}_visible_output_mismatch")
                if observed.get("p4_z_violations_after") != []:
                    failures.append(f"turn_{turn}_proposition_unresolved")
            elif observed.get("p4_z_changed") is not False:
                failures.append(f"turn_{turn}_unsupported_changed")
            if float(observed.get("end_to_end_seconds") or 0) > contract["gates"]["maximum_turn_latency_seconds"]:
                failures.append(f"turn_{turn}_latency_target_missed")
    for field, target in contract["gates"].items():
        observed = (evidence.get("metrics") or {}).get(field)
        if field.startswith("maximum_"):
            if observed is None or observed > target:
                failures.append(f"metric_ceiling_exceeded:{field}")
        elif observed != target:
            failures.append(f"metric_mismatch:{field}")
    for field, target in contract["accounting"].items():
        observed = (evidence.get("accounting") or {}).get(field)
        if field.endswith("_maximum"):
            if observed is None or observed > target:
                failures.append(f"accounting_ceiling_exceeded:{field}")
        elif observed != target:
            failures.append(f"accounting_mismatch:{field}")
    safari = evidence.get("safari") or {}
    if safari.get("actual_two_turn_acceptance") is not True or safari.get("graph_summary_visually_observed_each_turn") is not True:
        failures.append("safari_visual_acceptance_missing")
    return {
        "schema": "uruha_p4_ac_real_readable_graph_gate_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "claim_boundary": contract["claim_boundary"],
    }
