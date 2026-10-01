import json
from pathlib import Path

import p3_b71b_source3_b70_prediction_batch as b71b


ROOT = Path(__file__).resolve().parent
RESULT_PATH = ROOT / "analysis" / "p3_b71b_source3_b70_prediction_result_2026-09-20.json"


def test_saved_b71b_result_is_complete_and_future_locked():
    result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    assert b71b.validate_result(result) == {"valid": True, "errors": []}
    assert result["status"] == "prediction_batch_frozen"
    assert result["model_call_count"] == 8
    assert result["prediction_count"] == 8
    assert result["prediction_side_future_access_count"] == 0
    assert result["outcome_score_count"] == 0
    assert result["retry_count"] == 0
    assert result["fallback_count"] == 0


def test_saved_b71b_result_records_cost_context_and_adapter_non_intervention():
    result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    assert [row["cue_count"] for row in result["public_context_artifacts"]] == [72, 60, 58, 68]
    assert result["actual_prompt_tokens_total"] == 17312
    assert result["actual_completion_tokens_total"] == 1763
    assert result["model_latency_seconds_total"] == 149.1632
    assert result["normalization_applied_count"] == 0
    assert all(item["input_weight_sum"] == 1.0 for item in result["predictions"])
    assert all(item["normalization_contract"] == "p3_b70_v1" for item in result["predictions"])
    assert result["result_hash"] == "343a3d9fa41850b7d0bb920a3ea5b05a46d57285eb6784ea2d2b87d5672a65bc"


def test_saved_b71b_top1_differs_on_two_of_four_rows_before_outcomes():
    result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    grouped = {}
    for prediction in result["predictions"]:
        grouped.setdefault(prediction["row_id"], {})[prediction["condition"]] = prediction["selected_behavior"]
    differences = [row for row, pair in grouped.items() if pair["BASELINE_LITERAL"] != pair["SYSTEM_PRAGMATIC_STATE"]]
    assert differences == ["s3r0600", "s3r1200"]
