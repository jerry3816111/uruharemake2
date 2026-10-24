import hashlib
import json
from pathlib import Path

import p4_o_real_persisted_reference_time_delivery_gate as gate


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_o_real_persisted_reference_time_delivery_result_2026-09-22.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_result_binds_frozen_inputs_and_evidence():
    result = _load(RESULT)
    assert result["status"] == "pass"
    for binding in result["freeze_checkpoint"].values():
        if isinstance(binding, dict):
            assert _sha256(ROOT / binding["path"]) == binding["sha256"]
    evidence = result["evidence"]
    assert _sha256(ROOT / evidence["path"]) == evidence["sha256"]


def test_frozen_gate_recomputes_pass_from_preserved_evidence():
    result = _load(RESULT)
    evidence = _load(ROOT / result["evidence"]["path"])
    recomputed = gate.evaluate_evidence(gate.load_contract(), evidence)
    assert recomputed["status"] == "pass"
    assert recomputed["failed_gates"] == []
    assert result["gate_result"]["failed_gate_count"] == 0


def test_result_proves_exact_restart_delivery_without_profile_mutation_or_retry():
    result = _load(RESULT)
    first = result["observed_flow"]["process_1"]
    second = result["observed_flow"]["process_2"]
    assert first["current_memory_id"] == second["active_memory_id"]
    assert second["answer_present_in_input"] is False
    assert second["value_surface_strategy"] == "bounded_japanese_identity"
    assert second["visible_output"] == "今の飲み物の好みはたんぽぽ茶。前のじゃなくて、今の方ね。"
    assert second["profile_write_count"] == 0
    assert result["persistent_state"]["typed_record_hash_unchanged"] is True
    assert result["accounting"]["retry_count"] == 0
    assert result["accounting"]["general_model_call_count"] == 0


def test_result_keeps_claim_bounded_and_records_live_inspection_state():
    result = _load(RESULT)
    assert result["graph_and_ui"]["p4_j_graph_node_visible"] is True
    assert result["graph_and_ui"]["bounded_japanese_identity_visible"] is True
    assert result["graph_and_ui"]["closed_user_tabs"] == 0
    assert result["preserved_runtime_artifacts"]["process_2_left_running_for_user_inspection"] is True
    boundary = result["claim_boundary"]
    assert "does not prove arbitrary or open-domain memory" in boundary
    assert "human equation" in boundary
