import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p3_b73_prospective_response_target_protocol_readiness_2026-09-20.json"


def test_saved_readiness_result_is_honest_about_zero_human_evidence():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["status"] == "protocol_tooling_ready_human_reliability_not_started"
    assert result["pilot"] == {
        "actual_human_labels": 0,
        "reliability_status": "not_started",
        "required_distinct_humans": 2,
        "required_episodes_each": 18,
    }
    assert all(value == 0 for value in result["execution_counts"].values())
    assert result["blinding"]["prediction_view_outcome_access_count"] == 0
    assert result["blinding"]["coder_condition_or_prediction_visibility"] is False


def test_saved_result_keeps_four_evidence_layers_separate():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["layers"] == [
        "observable_response_moves",
        "pragmatic_target",
        "surface_realization",
        "separate_subjective_preference",
    ]
    assert "two_distinct_humans" in result["next_gate"]
