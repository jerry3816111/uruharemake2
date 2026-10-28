import hashlib
import json
from pathlib import Path

import p4_i_current_preference_gate as gate


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_i_cross_restart_current_preference_result_2026-09-21.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load():
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_result_is_bound_to_freeze_and_recomputes_pass():
    result = _load()
    binding = result["freeze_binding"]
    assert _sha256(ROOT / binding["path"]) == binding["sha256"]
    recomputed = gate.evaluate_evidence(gate.load_contract(), result)
    assert recomputed == result["gate_evaluation"]
    assert result["status"] == "pass"


def test_restart_keeps_same_isolated_database_but_changes_process_and_session():
    restart = _load()["restart"]
    assert restart["old_process_exit_observed"] is True
    assert restart["old_listener_closed_before_new_process"] is True
    assert restart["old_pid"] != restart["new_pid"]
    assert restart["old_session_id"] != restart["new_session_id"]
    assert restart["runtime_root_before"] == restart["runtime_root_after"]
    assert restart["memory_db_before"] == restart["memory_db_after"]
    assert restart["post_turn_memory_injection_count"] == 0


def test_correction_preserves_old_positive_as_history_and_activates_new_state():
    result = _load()
    first = result["process_1_turn"]
    second = result["process_2_turn"]
    state = result["persistent_state"]
    assert second["previous_current_memory_id"] == first["current_memory_id"]
    assert first["current_memory_id"] in second["historical_current_ids"]
    assert second["current_memory_id"] in second["active_current_ids"]
    assert second["negative_old_memory_id"]
    assert state["old_positive_state"] == "historical"
    assert state["new_positive_state"] == "active"
    assert state["negative_old_record_state"] == "active"
    assert state["old_and_new_positive_predicate_match"] is True
    assert state["old_records_deleted_or_rewritten"] is False


def test_visible_japanese_graph_and_resource_accounting_are_bounded():
    result = _load()
    for row in (result["process_1_turn"], result["process_2_turn"]):
        assert row["visible_output_language"] == "Japanese"
        assert row["p4_h_graph_stage"] == "select"
        assert row["p4_i_graph_stage"] == "memory"
        assert row["p4_i_answer_use_authorized"] is False
        assert row["p4_i_raw_dialogue_persisted"] is False
        assert row["end_to_end_seconds"] <= 20.0
    assert result["safari"]["p4_i_graph_node_visible_both_turns"] is True
    accounting = result["accounting"]
    assert accounting["process_starts"] == 2
    assert accounting["real_product_turns"] == 2
    assert accounting["retry_count"] == 0
    assert accounting["local_product_planner_model_calls"] == 0
    assert accounting["production_memory_access_count"] == 0
