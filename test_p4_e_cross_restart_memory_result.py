import hashlib
import json
from pathlib import Path

import p4_e_cross_restart_memory_gate as gate


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_e_cross_restart_memory_recall_result_2026-09-20.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_result_is_bound_to_frozen_pre_execution_contract():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    binding = result["freeze_binding"]
    assert _sha256(ROOT / binding["path"]) == binding["sha256"]
    assert result["status"] == "pass"


def test_frozen_gate_recomputes_exact_pass_from_result():
    contract = gate.load_contract()
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    recomputed = gate.evaluate_evidence(contract, result)
    assert recomputed["status"] == "pass"
    assert recomputed["failed_gates"] == []
    assert result["gate_evaluation"]["failed_gates"] == []


def test_actual_restart_retrieval_owner_and_graph_evidence_is_complete():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    restart = result["restart"]
    assert restart["old_process_exit_observed"] is True
    assert restart["old_pid"] != restart["new_pid"]
    assert restart["old_session_id"] != restart["new_session_id"]
    assert restart["runtime_root_before"] == restart["runtime_root_after"]
    assert restart["memory_db_before"] == restart["memory_db_after"]
    recall = result["session_2_turn"]
    assert recall["answer_value_present_in_input"] is False
    assert recall["selected_speaker"] == "user"
    assert recall["retrieved_memory_id"]
    assert recall["retrieved_trace_id"] == f"stored:episode:{recall['retrieved_memory_id']}"
    assert recall["retrieved_source_predates_new_session"] is True
    assert recall["graph_node_visible"] == "speaker_qualified_fact_p3"
    assert recall["product_planner_model_call_count"] == 0
    assert result["ownership_negative_controls"]["forbidden_visible_claim_hit_count"] == 0


def test_vrm_locality_resource_accounting_and_claim_boundary_are_preserved():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["vrm_restart_boundary"]["stage_after_new_page_load"] == "waiting_for_local_vrm"
    assert result["vrm_restart_boundary"]["server_persisted_previous_local_file"] is False
    accounting = result["accounting"]
    assert accounting["real_product_turns"] == 2
    assert accounting["retry_count"] == 0
    assert accounting["paid_api_call_count"] == 0
    assert accounting["function_tool_execution_count"] == 0
    assert result["remaining"]["preference_supersession_and_correction"] == "not_tested"
    assert "does not prove open-domain or human-like memory" in result["claim_boundary"]
