import json
from pathlib import Path

import p4_an_post_turn_temporal_graph_gate as gate


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_an_post_turn_temporal_graph_result_2026-09-25.json"


def test_p4_an_real_result_preserves_upstream_integration_failure():
    evidence = json.loads(RESULT.read_text(encoding="utf-8"))
    result = gate.evaluate_real_evidence(gate.load_contract(), evidence)
    assert evidence["status"] == "terminal_fail_after_first_formal_turn"
    assert result["status"] == "fail"
    assert "turn_count_mismatch" in result["failed_gates"]
    assert "metric_mismatch:six_candidate_present_count" in result["failed_gates"]
    assert "metric_mismatch:current_future_locked_count" in result["failed_gates"]


def test_p4_an_failure_separates_delivery_success_from_temporal_cycle_failure():
    evidence = json.loads(RESULT.read_text(encoding="utf-8"))
    row = evidence["turns"][0]
    assert row["node_before_utterance"] is True
    assert row["final_blackboard_contains_node"] is True
    assert evidence["metrics"]["graph_visible_count"] == 1
    assert row["typed_trigger_status"] == "single_observable_trigger"
    assert row["p4_ad_ledger_status"] == "not_applicable"
    assert row["present_candidate_count"] == 0
