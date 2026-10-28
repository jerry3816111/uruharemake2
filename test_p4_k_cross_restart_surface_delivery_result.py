import hashlib
import json
from pathlib import Path

import p4_k_surface_delivery_gate as gate


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_k_cross_restart_surface_delivery_result_2026-09-21.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load():
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_result_is_bound_to_freeze_and_recomputes_the_same_pass():
    result = _load()
    binding = result["freeze_binding"]
    assert _sha256(ROOT / binding["path"]) == binding["sha256"]
    recomputed = gate.evaluate_evidence(gate.load_contract(), result)
    assert recomputed == result["gate_evaluation"]
    assert result["status"] == "pass"


def test_restart_reuses_the_typed_record_in_exact_surface_and_graph():
    result = _load()
    first = result["process_1_turn"]
    second = result["process_2_turn"]
    assert first["current_memory_id"] == second["active_memory_id"]
    assert second["visible_output"] == "今の飲み物の好みは紅茶。前のじゃなくて、今の方ね。"
    assert second["p4_j_final_surface_exact"] is True
    assert second["p4_j_graph_label"] == "typed_current_preference_recall_p4"
    assert second["p4_j_graph_stage"] == "select"
    assert result["safari"]["p4_j_graph_node_visible_on_recall"] is True


def test_recall_does_not_mutate_profile_or_hide_resource_accounting():
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


def test_claim_boundary_does_not_promote_delivery_to_general_memory_or_research_advantage():
    boundary = _load()["claim_boundary"]
    assert "semantic overlap" in boundary
    assert "not unseen semantic generalization" in boundary
    assert "not" in boundary and "LLM superiority" in boundary and "human equation" in boundary
