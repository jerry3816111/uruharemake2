import json
from pathlib import Path

import p4_ao_reachable_temporal_graph_gate as gate


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_ao_reachable_temporal_graph_result_2026-09-25.json"


def test_p4_ao_real_result_preserves_second_turn_identity_failure():
    evidence = json.loads(RESULT.read_text(encoding="utf-8"))
    result = gate.evaluate_real_evidence(gate.load_contract(), evidence)
    assert evidence["status"] == "terminal_fail_during_second_formal_turn"
    assert result["status"] == "fail"
    assert "turn_count_mismatch" in result["failed_gates"]
    assert "metric_mismatch:later_explicit_calibrate_path_count" in result["failed_gates"]
    assert "metric_mismatch:third_turn_verified_past_count" in result["failed_gates"]
    assert "safari_three_turn_missing" in result["failed_gates"]
    assert "P1 prediction sequence skipped the next event" in evidence["termination_reason"]


def test_p4_ao_failure_keeps_first_turn_delivery_success_separate():
    evidence = json.loads(RESULT.read_text(encoding="utf-8"))
    row = evidence["turns"][0]
    assert row["trigger_path"] == "released_m37_cognitive_overactivity"
    assert row["present_candidate_count"] == 6
    assert row["current_future_status"] == "committed_outcome_locked"
    assert row["node_before_utterance"] is True
    assert row["logic_graph_payload_exact"] is True
    assert row["safari_node_visually_observed"] is True
    assert row["raw_or_private_payload_leak"] is False
    assert evidence["safari"]["actual_three_turn_acceptance"] is False
