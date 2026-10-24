import json
from pathlib import Path

import p4_x_real_product_frame_repair_gate as gate


ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / "analysis" / "p4_x_real_product_frame_repair_evidence_2026-09-22.json"
RESULT = ROOT / "analysis" / "p4_x_real_product_frame_repair_result_2026-09-22.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_preserved_real_product_evidence_reproduces_frozen_failure():
    evidence = _load(EVIDENCE)
    result = _load(RESULT)
    assert gate.evaluate_evidence(gate.load_contract(), evidence) == result
    assert result["status"] == "fail"
    assert result["failed_gates"] == [
        "turn_1_surface_trace_missing",
        "turn_2_surface_trace_missing",
        "turn_3_surface_trace_missing",
        "turn_4_surface_trace_missing",
        "metric_mismatch:p4_t_trace_count",
        "metric_mismatch:p4_v_trace_count",
        "metric_mismatch:p4_w_trace_count",
    ]


def test_logic_trace_existed_but_surface_graph_delivery_was_zero():
    evidence = _load(EVIDENCE)
    assert len(evidence["turns"]) == 4
    assert all(
        row["logic_p4_t_present"]
        and row["logic_p4_v_present"]
        and row["logic_p4_w_present"]
        for row in evidence["turns"]
    )
    assert evidence["metrics"]["p4_t_trace_count"] == 0
    assert evidence["metrics"]["p4_v_trace_count"] == 0
    assert evidence["metrics"]["p4_w_trace_count"] == 0
    assert evidence["metrics"]["minimum_natural_repair_trigger_count"] == 3
    assert evidence["metrics"]["branch_consistent_turn_count"] == 4
    assert evidence["metrics"]["visible_after_digest_match_count"] == 4
    assert evidence["metrics"]["unresolved_after_repair_count"] == 0


def test_semantic_failures_and_no_rerun_boundary_are_preserved():
    evidence = _load(EVIDENCE)
    observations = evidence["surface_quality_observations_outside_frozen_gate"]
    assert [row["turn"] for row in observations] == [1, 3, 4]
    assert evidence["decision"]["p4_x_pass_claim_allowed"] is False
    assert evidence["decision"]["same_case_rerun_allowed"] is False
    assert evidence["safari"]["new_result_tab_left_open"] is True
    assert evidence["accounting"]["closed_user_tab_count"] == 0
