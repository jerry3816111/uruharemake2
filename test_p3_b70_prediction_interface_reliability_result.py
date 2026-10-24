import json
from pathlib import Path

import p3_b55_reserved_source_context_transport as b55


ROOT = Path(__file__).resolve().parent
RESULT_PATH = ROOT / "analysis" / "p3_b70_prediction_interface_reliability_result_2026-09-20.json"


def test_saved_b70_result_passes_only_the_offline_mechanism_gate():
    result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    assert result["status"] == "passed_offline_interface_reliability_gate"
    assert result["direct_test_count"] == 12
    assert result["affected_test_count"] == 38
    assert result["selected_behavior_before"] == result["selected_behavior_after"]
    assert result["selected_behavior_preserved"] is True
    assert abs(sum(result["example_normalized_probabilities"].values()) - 1.0) <= 1e-12
    assert result["same_adapter_both_conditions"] is True


def test_saved_b70_result_has_zero_external_or_future_activity_and_valid_hash():
    result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    for field in (
        "model_call_count",
        "network_request_count",
        "future_access_count",
        "b69_retry_count",
        "training_write_count",
        "formal_m56_write_count",
        "production_write_count",
    ):
        assert result[field] == 0
    expected = result.pop("result_hash")
    assert b55.sha256_bytes(b55.canonical_json(result).encode("utf-8")) == expected
