import hashlib
import json
from pathlib import Path

import p4_j_typed_recall_gate as gate


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_j_cross_restart_typed_recall_result_2026-09-21.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load():
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_result_is_bound_to_freeze_and_recomputes_the_same_terminal_failure():
    result = _load()
    binding = result["freeze_binding"]
    assert _sha256(ROOT / binding["path"]) == binding["sha256"]
    recomputed = gate.evaluate_evidence(gate.load_contract(), result)
    assert recomputed == result["gate_evaluation"]
    assert result["status"] == "fail"


def test_failure_occurs_after_typed_state_resolution_but_before_final_surface_and_graph():
    result = _load()
    turn = result["process_2_turn"]
    assert turn["p4_j_status"] == "resolved_unique_active_typed_current_preference"
    assert turn["p4_j_plan_active_memory_id"] == result["process_1_turn"]["current_memory_id"]
    assert turn["p4_j_planned_core_jp"] == (
        "今の飲み物の好みはルイボスティー。前のじゃなくて、今の方ね。"
    )
    assert turn["visible_output"] != turn["p4_j_planned_core_jp"]
    assert turn["p4_j_final_surface_exact"] is False
    assert turn["episode_answer_use_count"] == 1
    assert result["safari"]["p4_j_graph_node_visible_on_recall"] is False


def test_failure_does_not_mutate_typed_profile_or_hide_resource_accounting():
    result = _load()
    state = result["persistent_state"]
    assert state["profile_record_count_before_recall"] == 1
    assert state["profile_record_count_after_recall"] == 1
    assert state["current_memory_id_unchanged"] is True
    assert state["typed_record_content_hash_unchanged"] is True
    accounting = result["accounting"]
    assert accounting["process_starts"] == 2
    assert accounting["real_product_turns"] == 2
    assert accounting["retry_count"] == 0
    assert accounting["local_product_planner_model_calls"] == 0
    assert accounting["production_memory_access_count"] == 0
