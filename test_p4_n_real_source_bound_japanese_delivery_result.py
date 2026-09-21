import hashlib
import json
from pathlib import Path

import p4_n_real_source_bound_japanese_delivery_gate as gate


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_n_real_source_bound_japanese_delivery_result_2026-09-22.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load():
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_result_is_bound_to_freeze_and_recomputes_same_terminal_failure():
    result = _load()
    binding = result["freeze_binding"]
    assert _sha256(ROOT / binding["path"]) == binding["sha256"]
    assert gate.evaluate_evidence(gate.load_contract(), result) == result["gate_evaluation"]
    assert result["status"] == "fail"
    assert len(result["gate_evaluation"]["failed_gates"]) == 21


def test_write_succeeded_and_typed_record_survived_real_restart_unchanged():
    result = _load()
    first = result["process_1_turn"]
    restart = result["restart"]
    state = result["persistent_state"]
    assert first["visible_output"] == "ん、その好みは覚えとく。"
    assert first["current_value"] == "そば茶"
    assert first["current_memory_id"] == restart["process_2_start_observed_first_active_id"]
    assert restart["old_pid"] != restart["new_pid"]
    assert restart["old_session_id"] != restart["new_session_id"]
    assert state["typed_record_content_hash_before_recall"] == state["typed_record_content_hash_after_recall"]
    assert state["source_language_persisted_as_ja"] is True
    assert state["source_provenance_hashes_unchanged"] is True


def test_recall_crashed_before_contract_surface_graph_or_episode_without_retry():
    result = _load()
    second = result["process_2_turn"]
    assert second["status"] == "exception_before_contract_delivery"
    assert second["exception_type"] == "ValueError"
    assert second["exception_message_class"] == "reference_time_none_rejected"
    assert second["visible_output"] is None
    assert second["p4_j_graph_label"] is None
    assert second["durable_episode_write_count"] == 0
    assert result["persistent_state"]["episode_record_count_after_recall"] == 1
    accounting = result["accounting"]
    assert accounting["retry_count"] == 0
    assert accounting["local_product_planner_model_calls"] == 0
    assert accounting["fallback_count"] == 0
    assert accounting["pre_turn_frontend_noop_reached_backend"] is False


def test_failure_is_not_misreported_as_memory_loss_or_delivery_success():
    result = _load()
    failure = result["failure_localization"]
    assert failure["typed_record_survived_restart"] is True
    assert failure["memory_loss_detected"] is False
    assert failure["wrong_value_selected_detected"] is False
    assert failure["same_case_retry_performed"] is False
    assert "terminal failure" in result["claim_boundary"]
    assert "does not establish successful" in result["claim_boundary"]
