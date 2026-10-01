import json
from pathlib import Path

import p4_am_real_runtime_temporal_graph_gate as gate


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_am_real_runtime_temporal_graph_result_2026-09-25.json"


def test_p4_am_real_result_is_preserved_as_terminal_failure():
    evidence = json.loads(RESULT.read_text(encoding="utf-8"))
    result = gate.evaluate_real_evidence(gate.load_contract(), evidence)
    assert evidence["status"] == "terminal_fail_after_first_formal_turn"
    assert result["status"] == "fail"
    assert "turn_count_mismatch" in result["failed_gates"]
    assert "metric_mismatch:graph_visible_count" in result["failed_gates"]
    assert "safari_three_turn_missing" in result["failed_gates"]
    assert "safari_temporal_node_missing" in result["failed_gates"]


def test_failure_keeps_payload_presence_separate_from_graph_delivery():
    evidence = json.loads(RESULT.read_text(encoding="utf-8"))
    row = evidence["turns"][0]
    assert row["logic_graph_payload_exact"] is True
    assert row["node_before_utterance"] is False
    assert evidence["metrics"]["graph_visible_count"] == 0
    assert evidence["metrics"]["temporal_node_count"] == 0
