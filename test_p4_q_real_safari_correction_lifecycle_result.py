import hashlib
import json
from pathlib import Path

import p4_q_real_safari_correction_lifecycle_gate as gate


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_q_real_safari_correction_lifecycle_result_2026-09-22.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_result_binds_frozen_inputs_and_preserved_evidence():
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


def test_result_proves_replacement_lineage_and_active_only_recall():
    result = _load(RESULT)
    first = result["observed_flow"]["process_1"]
    second = result["observed_flow"]["process_2"]
    assert first["correction"]["previous_current_memory_id"] == first["write"]["current_memory_id"]
    assert second["active_memory_id"] == first["correction"]["current_memory_id"]
    assert second["answer_present_in_input"] is False
    assert second["visible_output"] == "今の飲み物の好みはびわ茶。前のじゃなくて、今の方ね。"
    assert second["historical_answer_use_count"] == 0
    assert second["explicit_negative_answer_use_count"] == 0
    assert result["persistent_state"]["three_record_lineage_unchanged"] is True


def test_result_keeps_claim_bounded_and_records_live_inspection_state():
    result = _load(RESULT)
    assert result["graph_and_ui"]["recall_graph_node_visible"] is True
    assert result["graph_and_ui"]["closed_user_tabs"] == 0
    assert result["accounting"]["retry_count"] == 0
    assert result["accounting"]["general_model_call_count"] == 0
    assert result["preserved_runtime_artifacts"]["process_2_left_running_for_user_inspection"] is True
    boundary = result["claim_boundary"]
    assert "does not prove arbitrary multilingual correction" in boundary
    assert "long-dialogue memory" in boundary
    assert "human equation" in boundary
