import p3_b54_unidirectional_context_extraction as b54


def test_b54_release_bindings_and_claim_boundary_are_current():
    release = b54.load_json(
        b54.ROOT
        / "research"
        / "p3_b54_unidirectional_context_extraction_release_2026-09-18.json"
    )
    assert release["status"] == "synthetic_unidirectional_context_extraction_gate_passed"
    assert release["decision"] == "proceed_to_separately_frozen_reserved_source_observable_context_transport"
    for binding in release["bindings"].values():
        assert b54.sha256_file(b54.ROOT / binding["path"]) == binding["sha256"]
    assert release["execution_counts"] == {
        "reserved_source_media_access_count": 0,
        "hidden_future_access_count": 0,
        "prediction_execution_count": 0,
        "model_call_count": 0,
        "production_memory_write_count": 0,
    }
