import hashlib
import json
from pathlib import Path

import p4_f_preference_supersession_gate as gate


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_f_cross_restart_preference_supersession_result_2026-09-21.json"


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
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    recomputed = gate.evaluate_evidence(gate.load_contract(), result)
    assert recomputed["status"] == "pass"
    assert recomputed["failed_gates"] == []
    assert result["gate_evaluation"]["status"] == "pass"
    assert result["gate_evaluation"]["failed_gates"] == []


def test_two_immutable_episodes_resolve_current_and_revoked_values_after_restart():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    old_turn = result["session_1_old_turn"]
    correction_turn = result["session_1_correction_turn"]
    restart = result["restart"]
    recall = result["session_2_recall_turn"]
    history = result["history_integrity"]

    assert old_turn["episode_id"] != correction_turn["episode_id"]
    assert restart["old_process_exit_observed"] is True
    assert restart["old_pid"] != restart["new_pid"]
    assert restart["old_session_id"] != restart["new_session_id"]
    assert recall["answer_values_present_in_input"] is False
    assert recall["contract_status"] == "resolved_explicit_preference_supersession"
    assert recall["current_value_jp"] == "紅茶"
    assert recall["revoked_value_jp"] == "ハーブティー"
    assert recall["current_value_digest"] != recall["revoked_value_digest"]
    assert recall["product_planner_model_call_count"] == 0
    assert history["historical_memory_id"] == old_turn["episode_id"]
    assert history["correction_memory_id"] == correction_turn["episode_id"]
    assert history["old_retrieval_score"] > history["correction_retrieval_score"]
    assert history["history_preserved"] is True


def test_execution_ceiling_claim_boundary_and_surface_gap_are_preserved():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    accounting = result["accounting"]
    assert accounting["real_product_turns"] == 3
    assert accounting["process_starts"] == 2
    assert accounting["process_restart_count"] == 1
    assert accounting["retry_count"] == 0
    assert accounting["local_product_planner_model_calls"] == 2
    assert accounting["paid_api_call_count"] == 0
    assert accounting["production_memory_access_count"] == 0

    surface_gap = result["observed_surface_gap_outside_p4_f_gate"]
    assert surface_gap["status"] == "retained"
    assert surface_gap["future_product_surface_follow_up_needed"] is True
    assert result["session_1_old_turn"]["visible_output"] == "了解しました"
    assert result["session_1_correction_turn"]["visible_output"] == "了解しました。"
    assert result["remaining"]["research_advantage"] == "unchanged_and_not_established"
