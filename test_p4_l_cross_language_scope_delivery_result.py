import hashlib
import json
from pathlib import Path

import p4_l_cross_language_scope_delivery_gate as gate


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_l_cross_language_scope_delivery_result_2026-09-21.json"


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


def test_cross_language_scope_survives_restart_into_exact_surface_and_graph():
    result = _load()
    first = result["process_1_turn"]
    second = result["process_2_turn"]
    assert first["scope_source"] == "canonical_alias_projection"
    assert first["p4_l_alias_id"] == "drink:zh-Hant:v1"
    assert first["current_memory_id"] == second["active_memory_id"]
    assert second["visible_output"] == "今の飲み物の好みは麦茶。前のじゃなくて、今の方ね。"
    assert second["p4_j_final_surface_exact"] is True
    assert result["safari"]["p4_l_graph_node_visible_on_write"] is True
    assert result["safari"]["p4_j_graph_node_visible_on_recall"] is True


def test_recall_does_not_mutate_profile_and_preserves_alias_provenance():
    result = _load()
    state = result["persistent_state"]
    assert state["profile_record_count_before_recall"] == 1
    assert state["profile_record_count_after_recall"] == 1
    assert state["current_memory_id_unchanged"] is True
    assert state["typed_record_content_hash_unchanged"] is True
    assert state["canonical_scope_persisted_after_restart"] is True
    assert state["alias_provenance_persisted_after_restart"] is True
    assert result["accounting"]["retry_count"] == 0
    assert result["accounting"]["local_product_planner_model_calls"] == 0


def test_claim_boundary_does_not_promote_alias_delivery_to_general_understanding():
    boundary = _load()["claim_boundary"]
    assert "semantic overlap" in boundary
    assert "not novel value semantics" in boundary
    assert "not" in boundary and "LLM superiority" in boundary and "human equation" in boundary
