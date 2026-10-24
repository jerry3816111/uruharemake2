#!/usr/bin/env python3
"""Fail-closed gate for the frozen P4-G real product acceptance."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_g_multilingual_preference_acknowledgement_acceptance_v1.json"


class P4GPreferenceAcknowledgementGateError(RuntimeError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    contract = json.loads(path.read_text(encoding="utf-8"))
    validate_contract(contract)
    return contract


def validate_contract(contract: dict) -> None:
    if contract.get("schema") != "uruha_p4_g_multilingual_preference_acknowledgement_acceptance_v1":
        raise P4GPreferenceAcknowledgementGateError("contract_schema_invalid")
    turns = contract.get("turns") or []
    if len(turns) != 2 or [row.get("turn_index") for row in turns] != [1, 2]:
        raise P4GPreferenceAcknowledgementGateError("turn_shape_invalid")
    if [(row.get("expected_language"), row.get("expected_act")) for row in turns] != [
        ("zh", "write"),
        ("ja", "correction"),
    ]:
        raise P4GPreferenceAcknowledgementGateError("multilingual_act_order_invalid")
    if any("herbal tea" in row.get("input", "").casefold() for row in turns):
        raise P4GPreferenceAcknowledgementGateError("p4_f_case_reused")
    requirements = contract.get("per_turn_requirements") or {}
    if requirements.get("product_planner_model_call_count_maximum") != 1:
        raise P4GPreferenceAcknowledgementGateError("per_turn_model_ceiling_invalid")
    ceiling = contract.get("execution_ceiling") or {}
    if ceiling.get("real_product_turns") != 2 or ceiling.get("retry_count") != 0:
        raise P4GPreferenceAcknowledgementGateError("execution_ceiling_invalid")
    failure = contract.get("failure_policy") or {}
    if not failure or not all(value is False for value in failure.values()):
        raise P4GPreferenceAcknowledgementGateError("failure_policy_invalid")


def evaluate_evidence(contract: dict, evidence: dict) -> dict:
    validate_contract(contract)
    failed = []
    runtime = evidence.get("runtime") or {}
    if runtime.get("fresh_isolated_root") is not True:
        failed.append("runtime_not_fresh")
    if runtime.get("listener") != "127.0.0.1:7860":
        failed.append("listener_not_localhost")
    if runtime.get("production_memory_access_count") != 0:
        failed.append("production_memory_access_nonzero")

    requirements = contract["per_turn_requirements"]
    evidence_turns = evidence.get("turns") or []
    if len(evidence_turns) != 2:
        failed.append("evidence_turn_count_mismatch")
    for expected, observed in zip(contract["turns"], evidence_turns):
        prefix = f"turn{expected['turn_index']}"
        exact = {
            "turn_index": expected["turn_index"],
            "input": expected["input"],
            "visible_output": expected["expected_visible_output"],
            "visible_output_language": requirements["visible_output_language"],
            "p4_g_status": requirements["p4_g_status"],
            "act": expected["expected_act"],
            "input_language": expected["expected_language"],
            "surface_authority": requirements["surface_authority"],
            "surface_changed": requirements["surface_changed"],
            "language_guard_repair_action": requirements["language_guard_repair_action"],
            "graph_node_visible": requirements["graph_node"],
            "durable_episode_write_count": requirements["durable_episode_write_count"],
            "fallback_count": requirements["fallback_count"],
            "raw_dialogue_persisted_in_p4_g_trace": requirements["raw_dialogue_persisted_in_p4_g_trace"],
        }
        for key, value in exact.items():
            if observed.get(key) != value:
                failed.append(f"{prefix}_mismatch:{key}")
        calls = observed.get("product_planner_model_call_count")
        if not isinstance(calls, int) or calls < 0 or calls > requirements["product_planner_model_call_count_maximum"]:
            failed.append(f"{prefix}_model_call_ceiling_exceeded")
        if not observed.get("episode_id"):
            failed.append(f"{prefix}_episode_id_missing")
    if len(evidence_turns) == 2 and evidence_turns[0].get("episode_id") == evidence_turns[1].get("episode_id"):
        failed.append("episode_ids_not_distinct")

    accounting = evidence.get("accounting") or {}
    ceilings = contract["execution_ceiling"]
    for key in (
        "real_product_turns",
        "process_starts",
        "retry_count",
        "paid_api_call_count",
        "external_deployment_count",
        "production_memory_access_count",
        "function_tool_execution_count",
        "vrm_action_execution_count",
    ):
        if accounting.get(key) != ceilings.get(key):
            failed.append(f"accounting_mismatch:{key}")
    calls = accounting.get("local_product_planner_model_calls")
    if not isinstance(calls, int) or calls < 0 or calls > ceilings["local_product_planner_model_calls_maximum"]:
        failed.append("accounting_model_call_ceiling_exceeded")
    if accounting.get("fallback_count") != 0:
        failed.append("accounting_fallback_nonzero")
    safari = evidence.get("safari") or {}
    if safari.get("actual_two_turn_acceptance") is not True:
        failed.append("safari_acceptance_not_observed")
    if safari.get("closed_tab_count") != 0:
        failed.append("safari_tab_closed")
    return {
        "schema": "uruha_p4_g_preference_acknowledgement_gate_result_v1",
        "status": "pass" if not failed else "fail",
        "failed_gates": failed,
        "claim_boundary": contract["claim_boundary"],
    }


if __name__ == "__main__":
    print(json.dumps(load_contract(), ensure_ascii=False, indent=2))
