#!/usr/bin/env python3
"""Fail-closed P4-F product preference-supersession evidence gate."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_f_cross_restart_preference_supersession_acceptance_v1.json"


class P4FPreferenceSupersessionError(RuntimeError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_contract(payload)
    return payload


def validate_contract(contract: dict) -> None:
    if contract.get("schema") != "uruha_p4_f_cross_restart_preference_supersession_acceptance_v1":
        raise P4FPreferenceSupersessionError("contract_schema_invalid")
    first = contract.get("session_1") or {}
    old_input = str(first.get("old_preference_input") or "")
    correction_input = str(first.get("correction_input") or "")
    if "herbal tea" not in old_input.casefold() or "current tea preference" not in old_input.casefold():
        raise P4FPreferenceSupersessionError("old_preference_fixture_invalid")
    required_correction_parts = ("i do not prefer herbal tea anymore", "i prefer black tea now")
    if not all(part in correction_input.casefold() for part in required_correction_parts):
        raise P4FPreferenceSupersessionError("explicit_correction_fixture_invalid")
    if first.get("durable_episode_writes_required") != 2:
        raise P4FPreferenceSupersessionError("session_1_episode_count_invalid")
    second = contract.get("session_2") or {}
    recall_input = str(second.get("recall_input") or "")
    for value in second.get("answer_values_absent_from_input") or []:
        if str(value).casefold() in recall_input.casefold():
            raise P4FPreferenceSupersessionError("recall_prompt_contains_answer_value")
    if second.get("expected_contract_status") != "resolved_explicit_preference_supersession":
        raise P4FPreferenceSupersessionError("expected_contract_status_invalid")
    if second.get("maximum_product_planner_model_calls") != 0:
        raise P4FPreferenceSupersessionError("recall_model_call_ceiling_invalid")
    restart = contract.get("restart") or {}
    required_true = (
        "old_process_must_exit",
        "new_pid_required",
        "new_product_session_id_required",
        "same_runtime_root_required",
        "same_memory_db_required",
        "reuse_runtime_manifest_required",
    )
    if not all(restart.get(key) is True for key in required_true):
        raise P4FPreferenceSupersessionError("restart_proof_requirement_missing")
    if restart.get("server_side_injection_or_seed_after_session_1_allowed") is not False:
        raise P4FPreferenceSupersessionError("post_turn_seed_not_forbidden")
    history = contract.get("history_integrity") or {}
    if not all(value is True for value in history.values()):
        raise P4FPreferenceSupersessionError("history_integrity_requirement_missing")
    ceiling = contract.get("execution_ceiling") or {}
    if ceiling.get("real_product_turns") != 3 or ceiling.get("retry_count") != 0:
        raise P4FPreferenceSupersessionError("execution_ceiling_invalid")


def evaluate_evidence(contract: dict, evidence: dict) -> dict:
    """Return exact failures; never repair, infer, or fill missing evidence."""
    validate_contract(contract)
    failed = []
    runtime = evidence.get("runtime") or {}
    old_turn = evidence.get("session_1_old_turn") or {}
    correction_turn = evidence.get("session_1_correction_turn") or {}
    restart = evidence.get("restart") or {}
    recall = evidence.get("session_2_recall_turn") or {}
    history = evidence.get("history_integrity") or {}
    accounting = evidence.get("accounting") or {}

    if runtime.get("production_memory_access_count") != 0:
        failed.append("production_memory_access_nonzero")
    if old_turn.get("input") != contract["session_1"]["old_preference_input"]:
        failed.append("old_preference_input_mismatch")
    if correction_turn.get("input") != contract["session_1"]["correction_input"]:
        failed.append("correction_input_mismatch")
    for label, turn in (("old", old_turn), ("correction", correction_turn)):
        if turn.get("visible_output_language") != "Japanese":
            failed.append(f"{label}_visible_language_mismatch")
        if not turn.get("episode_id"):
            failed.append(f"{label}_episode_id_missing")
        if turn.get("durable_episode_write_count") != 1:
            failed.append(f"{label}_durable_episode_write_mismatch")
    if old_turn.get("episode_id") == correction_turn.get("episode_id"):
        failed.append("source_episode_ids_not_distinct")
    if restart.get("old_process_exit_observed") is not True:
        failed.append("old_process_exit_not_observed")
    if restart.get("old_pid") == restart.get("new_pid") or not restart.get("new_pid"):
        failed.append("pid_not_changed")
    if restart.get("old_session_id") == restart.get("new_session_id") or not restart.get("new_session_id"):
        failed.append("session_id_not_changed")
    if restart.get("runtime_root_before") != restart.get("runtime_root_after"):
        failed.append("runtime_root_changed")
    if restart.get("memory_db_before") != restart.get("memory_db_after"):
        failed.append("memory_db_changed")
    if restart.get("post_turn_memory_injection_count") != 0:
        failed.append("post_turn_memory_injection_nonzero")

    second = contract["session_2"]
    exact_fields = {
        "input": second["recall_input"],
        "visible_output": second["expected_visible_output"],
        "visible_output_language": second["visible_output_language_required"],
        "contract_status": second["expected_contract_status"],
        "selected_speaker": second["expected_selected_speaker"],
        "candidate_count": second["expected_candidate_count"],
        "current_value_jp": second["expected_current_value_jp"],
        "revoked_value_jp": second["expected_revoked_value_jp"],
        "planner_path": second["expected_planner_path"],
        "graph_node_visible": second["graph_node_required"],
        "product_planner_model_call_count": second["maximum_product_planner_model_calls"],
        "fact_memory_write_count": second["fact_memory_write_count"],
        "database_rewrite_count": second["database_rewrite_count"],
        "raw_dialogue_persisted_in_trace": second["raw_dialogue_persisted_in_trace"],
    }
    for key, expected in exact_fields.items():
        if recall.get(key) != expected:
            failed.append(f"recall_mismatch:{key}")
    if recall.get("visible_surface_matches_contract") is not True:
        failed.append("visible_surface_not_contract_authoritative")
    if recall.get("current_value_digest") == recall.get("revoked_value_digest"):
        failed.append("current_and_revoked_digests_not_distinct")
    if not recall.get("current_value_digest") or not recall.get("revoked_value_digest"):
        failed.append("current_or_revoked_digest_missing")

    if history.get("old_episode_present_after_restart") is not True:
        failed.append("old_episode_not_preserved")
    if history.get("correction_episode_present_after_restart") is not True:
        failed.append("correction_episode_not_preserved")
    if history.get("historical_memory_id") != old_turn.get("episode_id"):
        failed.append("historical_memory_id_not_old_episode")
    if history.get("correction_memory_id") != correction_turn.get("episode_id"):
        failed.append("correction_memory_id_not_correction_episode")
    if history.get("historical_trace_id") != f"stored:episode:{old_turn.get('episode_id')}":
        failed.append("historical_trace_id_mismatch")
    if history.get("correction_trace_id") != f"stored:episode:{correction_turn.get('episode_id')}":
        failed.append("correction_trace_id_mismatch")
    if history.get("both_sources_predate_new_process") is not True:
        failed.append("source_timestamps_not_pre_restart")
    if history.get("history_preserved") is not True:
        failed.append("history_preserved_flag_missing")

    ceilings = contract["execution_ceiling"]
    for key in (
        "real_product_turns",
        "process_starts",
        "process_restart_count",
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
    return {
        "schema": "uruha_p4_f_preference_supersession_gate_result_v1",
        "status": "pass" if not failed else "fail",
        "failed_gates": failed,
        "claim_boundary": contract["claim_boundary"],
    }


if __name__ == "__main__":
    print(json.dumps(load_contract(), ensure_ascii=False, indent=2))
