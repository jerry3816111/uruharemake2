import p3_b55_reserved_source_context_transport as b55_v1
import p3_b55_reserved_source_context_transport_v2 as b55_v2


def test_saved_v1_and_v2_failures_are_valid_and_preserve_zero_future_access():
    paths = [
        b55_v2.ROOT / "analysis" / "p3_b55_v1_pre_network_tool_probe_failure_2026-09-18.json",
        b55_v2.ROOT / "analysis" / "p3_b55_v2_reserved_source_transport_failure_2026-09-18.json",
    ]
    results = [b55_v2.load_json(path) for path in paths]
    for result in results:
        assert b55_v1.validate_result(result) == {"valid": True, "errors": []}
        assert result["hidden_future_media_request_count"] == 0
        assert result["prediction_execution_count"] == 0
        assert result["model_call_count"] == 0
        assert result["public_artifact_count"] == 0
    assert [result["network_attempt_count"] for result in results] == [0, 1]
    assert results[0]["failure_stage"] == "unexpected"
    assert results[1]["failure_stage"] == "network_transport"
    assert results[1]["transport_returncode"] == 1
