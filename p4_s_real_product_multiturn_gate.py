#!/usr/bin/env python3
"""Fail-closed gate for the P4-S real Safari multi-turn lifecycle."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_s_real_product_multiturn_acceptance_v1.json"


class P4SGateError(RuntimeError):
    pass


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_contract(path=CONTRACT):
    contract = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_contract(contract)
    return contract


def validate_contract(contract):
    if contract.get("schema") != "uruha_p4_s_real_product_multiturn_acceptance_v1":
        raise P4SGateError("contract_schema_invalid")
    dataset = contract.get("dataset") or {}
    path = ROOT / str(dataset.get("path") or "")
    if not path.is_file() or _sha256(path) != dataset.get("sha256"):
        raise P4SGateError("dataset_binding_invalid")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("case_id") != dataset.get("case_id"):
        raise P4SGateError("dataset_case_invalid")
    if payload.get("turn_count") != 12 or len(payload.get("turns") or []) != 12:
        raise P4SGateError("dataset_turn_count_invalid")
    if payload.get("restart_after_turn") != 6:
        raise P4SGateError("restart_boundary_invalid")
    novelty = (payload.get("novelty") or {}).get("repository_occurrences_before_dataset_creation") or {}
    if not novelty or any(value != 0 for value in novelty.values()):
        raise P4SGateError("novelty_invalid")
    if (contract.get("failure_policy") or {}).get("same_case_rerun_allowed") is not False:
        raise P4SGateError("same_case_rerun_not_forbidden")


def evaluate_evidence(contract, evidence):
    validate_contract(contract)
    failures = []
    if evidence.get("schema") != "uruha_p4_s_real_product_multiturn_evidence_v1":
        failures.append("evidence_schema_invalid")
    if evidence.get("case_id") != contract["dataset"]["case_id"]:
        failures.append("case_id_mismatch")
    if evidence.get("dataset_sha256") != contract["dataset"]["sha256"]:
        failures.append("dataset_hash_mismatch")

    dataset = json.loads((ROOT / contract["dataset"]["path"]).read_text(encoding="utf-8"))
    observed_turns = evidence.get("turns") or []
    if [row.get("turn") for row in observed_turns] != list(range(1, 13)):
        failures.append("turn_order_or_count_invalid")
    else:
        for frozen, observed in zip(dataset["turns"], observed_turns):
            turn = frozen["turn"]
            if observed.get("input") != frozen["input"]:
                failures.append(f"turn_{turn}_input_mismatch")
            if observed.get("visible_output_language") != "Japanese":
                failures.append(f"turn_{turn}_not_japanese")
            if not observed.get("episode_id"):
                failures.append(f"turn_{turn}_episode_missing")
            if observed.get("graph_visible") is not True:
                failures.append(f"turn_{turn}_graph_missing")
            if float(observed.get("end_to_end_seconds", 10**9)) > contract["gates"][
                "maximum_turn_latency_seconds"
            ]:
                failures.append(f"turn_{turn}_latency_target_missed")
            expected_surface = frozen.get("expected_exact_surface")
            if expected_surface and observed.get("visible_output") != expected_surface:
                failures.append(f"turn_{turn}_exact_surface_mismatch")
            expected_act = frozen.get("expected_act")
            if expected_act:
                if observed.get("p4_i_selected") is not True or observed.get("p4_i_act") != expected_act:
                    failures.append(f"turn_{turn}_typed_act_mismatch")
            elif frozen["role"] not in {"pre_correction_recall", "post_correction_recall"}:
                if observed.get("p4_i_selected") is not False:
                    failures.append(f"turn_{turn}_distractor_typed_write")

    for field, expected in contract["gates"].items():
        if field.startswith("maximum_"):
            if float((evidence.get("metrics") or {}).get(field, 10**9)) > float(expected):
                failures.append(f"metric_ceiling_exceeded:{field}")
        elif (evidence.get("metrics") or {}).get(field) != expected:
            failures.append(f"metric_mismatch:{field}")

    restart = evidence.get("restart") or {}
    if restart.get("old_process_exit_observed") is not True or restart.get(
        "old_listener_closed_before_new_process"
    ) is not True:
        failures.append("restart_not_observed")
    if not restart.get("new_pid") or restart.get("new_pid") == restart.get("old_pid"):
        failures.append("pid_not_changed")
    if not restart.get("new_session_id") or restart.get("new_session_id") == restart.get(
        "old_session_id"
    ):
        failures.append("session_not_changed")
    if restart.get("runtime_root_before") != restart.get("runtime_root_after"):
        failures.append("runtime_root_changed")
    if restart.get("memory_db_before") != restart.get("memory_db_after"):
        failures.append("memory_db_changed")
    if restart.get("process_2_start_drink_active_values") != ["松葉茶"]:
        failures.append("restart_drink_state_invalid")
    if restart.get("process_2_start_game_active_values") != ["ストラテジーゲーム"]:
        failures.append("restart_cross_scope_state_invalid")

    final_state = evidence.get("final_state") or {}
    if final_state.get("drink_active_values") != ["なた豆茶"]:
        failures.append("final_active_value_invalid")
    if final_state.get("drink_historical_values") != ["松葉茶"]:
        failures.append("final_historical_value_invalid")
    if final_state.get("drink_explicit_negative_values") != ["松葉茶"]:
        failures.append("final_negative_value_invalid")
    if final_state.get("game_active_values") != ["ストラテジーゲーム"]:
        failures.append("final_cross_scope_state_invalid")
    if final_state.get("correction_previous_link_valid") is not True:
        failures.append("correction_previous_link_invalid")
    if final_state.get("negative_correction_link_valid") is not True:
        failures.append("negative_correction_link_invalid")

    accounting = evidence.get("accounting") or {}
    for field, expected in contract["accounting"].items():
        if field.endswith("_maximum"):
            if not isinstance(accounting.get(field), int) or accounting.get(field) > expected:
                failures.append(f"accounting_ceiling_exceeded:{field}")
        elif accounting.get(field) != expected:
            failures.append(f"accounting_mismatch:{field}")
    safari = evidence.get("safari") or {}
    if safari.get("actual_two_process_twelve_turn_acceptance") is not True:
        failures.append("safari_acceptance_not_observed")
    if safari.get("closed_tab_count") != 0:
        failures.append("user_tab_closed")
    return {
        "schema": "uruha_p4_s_real_product_multiturn_gate_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "claim_boundary": contract["claim_boundary"],
    }


if __name__ == "__main__":
    print(json.dumps(load_contract(), ensure_ascii=False, indent=2))
