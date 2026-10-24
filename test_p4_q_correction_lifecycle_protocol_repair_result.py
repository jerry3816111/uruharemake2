import hashlib
import json
from pathlib import Path

import p4_q_correction_lifecycle_protocol_repair_gate as gate


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_q_correction_lifecycle_protocol_repair_result_2026-09-22.json"


def _load():
    return json.loads(RESULT.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_result_is_bound_to_freeze_and_recomputes_pass():
    result = _load()
    binding = result["freeze_binding"]
    assert _sha256(ROOT / binding["path"]) == binding["sha256"]
    recomputed = gate.evaluate_evidence(gate.load_contract(), result)
    assert recomputed["status"] == "pass"
    assert recomputed["failed_gates"] == []
    assert result["status"] == "pass_offline"


def test_three_record_lineage_survives_restart_and_recall_unchanged():
    result = _load()
    first = result["process_1"]
    second = result["process_2"]
    assert first["active_current_ids"] == [first["correction_memory_id"]]
    assert first["historical_current_ids"] == [first["write_memory_id"]]
    assert first["negative_correction_current_memory_id"] == first["correction_memory_id"]
    assert second["record_hashes_before"] == first["record_hashes_after"]
    assert second["record_hashes_after"] == first["record_hashes_after"]
    assert second["answer_memory_ids"] == [first["correction_memory_id"]]
    assert result["restart"]["old_pid"] != result["restart"]["new_pid"]


def test_visible_answer_uses_only_new_japanese_value():
    result = _load()
    second = result["process_2"]
    assert second["visible_surface"] == "今の飲み物の好みははと麦茶。前のじゃなくて、今の方ね。"
    assert "洛神花茶" not in second["visible_surface"]
    assert second["value_surface_strategy"] == "bounded_japanese_identity"
    assert second["historical_answer_use_count"] == 0
    assert second["explicit_negative_answer_use_count"] == 0


def test_causal_claim_and_next_stage_remain_bounded():
    result = _load()
    causal = result["causal_interpretation"]
    assert causal["p4_p_status"] == "terminal_protocol_failure"
    assert causal["p4_q_status"] == "pass_offline"
    assert causal["p4_p_and_p4_q_share_write_and_recall_phase_functions"] is True
    assert causal["product_code_changed_between_p4_p_and_p4_q"] is False
    assert result["next_stage"]["id"] == "P4-Q-REAL"
    assert "offline evidence only" in result["claim_boundary"]
