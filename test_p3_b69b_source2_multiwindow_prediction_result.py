import json
from pathlib import Path

import p3_b69b_source2_multiwindow_predictions as b69b


ROOT = Path(__file__).resolve().parent
RESULT_PATH = ROOT / "analysis" / "p3_b69b_source2_multiwindow_prediction_result_2026-09-20.json"


def test_saved_b69b_result_is_terminal_schema_failure_with_futures_locked():
    result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    assert b69b.validate_result(result) == {"valid": True, "errors": []}
    assert result["status"] == "prediction_batch_failed"
    assert result["failure_stage"] == "prediction"
    assert result["failure_category"] == "schema"
    assert result["model_call_count"] == 7
    assert [record["status"] for record in result["call_records"]] == ["completed"] * 7
    assert result["call_records"][-1]["row_id"] == "s2r2400"
    assert result["call_records"][-1]["condition"] == "BASELINE_LITERAL"
    assert result["prediction_side_future_access_count"] == 0
    assert result["outcome_score_count"] == 0
    assert result["retry_count"] == 0
    assert result["fallback_count"] == 0


def test_saved_b69b_result_preserves_resource_and_isolation_evidence():
    result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    assert result["native_downloader_process_invocation_count"] == 1
    assert result["downloader_returncode"] == 0
    assert result["private_full_caption_deleted_before_context_reader_and_model"] is True
    assert result["private_runtime_deleted_before_context_reader_and_model"] is True
    assert result["public_context_artifact_count"] == 4
    assert [row["cue_count"] for row in result["public_context_artifacts"]] == [69, 66, 77, 55]
    assert sum(record["prompt_tokens"] for record in result["call_records"]) == 15429
    assert sum(record["completion_tokens"] for record in result["call_records"]) == 1650
    assert round(sum(record["latency_seconds"] for record in result["call_records"]), 6) == 133.887876
    assert result["result_hash"] == "9e1c39ce897e832a4502203a55378081c86233ffe0cb6a938a3660948a84774e"
