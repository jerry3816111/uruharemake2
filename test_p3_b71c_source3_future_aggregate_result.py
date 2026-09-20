import json
from pathlib import Path

import p3_b71c_source3_future_aggregate_scoring as b71c


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p3_b71c_source3_future_aggregate_result_2026-09-20.json"


def test_saved_result_is_valid_mixed_source3_proxy_result():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert b71c.validate_result(result) == {"valid": True, "errors": []}
    assert result["status"] == "aggregate_scored"
    assert result["aggregate"]["row_wins"] == {"BASELINE_LITERAL": 2, "SYSTEM_PRAGMATIC_STATE": 2, "TIE": 0}
    assert result["aggregate"]["BASELINE_LITERAL"]["mean_actual_label_probability"] == 0.375
    assert result["aggregate"]["SYSTEM_PRAGMATIC_STATE"]["mean_actual_label_probability"] == 0.2375
    assert result["aggregate"]["BASELINE_LITERAL"]["top1_hits"] == 2
    assert result["aggregate"]["SYSTEM_PRAGMATIC_STATE"]["top1_hits"] == 1


def test_saved_result_exposes_proxy_label_collapse_and_no_extra_calls():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert {row["actual_proxy_label"] for row in result["rows"]} == {"acknowledge_then_continue"}
    assert all(row["matched_proxy_marker"] is None for row in result["rows"])
    assert result["future_outcome_access_count"] == 4
    assert result["outcome_score_count"] == 8
    assert result["model_human_or_llm_judge_call_count"] == 0
    assert result["prediction_mutation_count"] == 0
    assert result["retry_count"] == 0
    assert result["result_hash"] == "ae87e582ebd46c76324881af6d11c2718f03f6ada938ab293c3c93fd5aecc11c"
