import json
from pathlib import Path

import p4_ae_fresh_ambiguity_generalization_gate as gate


ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / "analysis" / "p4_ae_fresh_ambiguity_generalization_evidence_2026-09-23.json"
RESULT = ROOT / "analysis" / "p4_ae_fresh_ambiguity_generalization_result_2026-09-23.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_saved_first_and_only_execution_reproduces_frozen_failure():
    evidence = _load(EVIDENCE)
    result = _load(RESULT)
    assert gate.evaluate_evidence(gate.load_contract(), evidence) == result
    assert result["status"] == "fail"
    assert result["failed_gates"] == [
        "ae_control_zh_02:status_mismatch",
        "ae_control_zh_02:near_miss_false_positive",
        "metric_mismatch:near_miss_false_positive_count",
    ]
    assert evidence["execution_count"] == 1
    assert evidence["accounting"]["retry_count"] == 0
    assert evidence["accounting"]["fallback_count"] == 0


def test_positive_generalization_and_single_false_positive_are_both_preserved():
    evidence = _load(EVIDENCE)
    assert evidence["metrics"]["exact_status_count"] == 6
    assert evidence["metrics"]["required_candidate_modes_complete_count"] == 6
    assert evidence["metrics"]["private_unknown_boundary_count"] == 6
    assert evidence["metrics"]["near_miss_false_positive_count"] == 1
    false_positive = next(row for row in evidence["cases"] if row["case_id"] == "ae_control_zh_02")
    assert false_positive["status"] == "ambiguity_preserved"
    assert false_positive["candidate_count"] == 6


def test_failure_still_has_no_private_truth_reply_model_or_memory_side_effect():
    metrics = _load(EVIDENCE)["metrics"]
    assert metrics["selected_action_private_truth_commitment_count"] == 0
    assert metrics["raw_input_trace_count"] == 0
    assert metrics["visible_reply_changed_count"] == 0
    assert metrics["new_model_call_count"] == 0
    assert metrics["fact_write_count"] == 0
    assert metrics["profile_write_count"] == 0
    assert metrics["episode_write_count"] == 0
