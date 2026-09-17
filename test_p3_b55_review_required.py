import p3_b55_reserved_source_context_transport_v2 as b55_v2


def test_b55_review_required_record_binds_both_failures_and_denies_next_execution():
    record = b55_v2.load_json(
        b55_v2.ROOT
        / "research"
        / "p3_b55_reserved_source_context_transport_review_required_2026-09-18.json"
    )
    assert record["status"] == "review_required_after_two_evidence_bounded_batches"
    assert record["next_execution_authorized"] is False
    assert record["aggregate_counts"] == {
        "network_attempt_count": 1,
        "public_artifact_count": 0,
        "hidden_future_media_request_count": 0,
        "manual_playback_count": 0,
        "semantic_inspection_count": 0,
        "prediction_execution_count": 0,
        "model_call_count": 0,
        "formal_m56_write_count": 0,
        "production_memory_write_count": 0,
    }
    for binding in record["bindings"].values():
        assert b55_v2.sha256_file(b55_v2.ROOT / binding["path"]) == binding["sha256"]
