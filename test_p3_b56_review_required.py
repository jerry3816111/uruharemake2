import p3_b56_allowlisted_diagnostic_transport as b56


def test_b56_review_record_binds_negative_result_and_denies_next_execution():
    review = b56.load_json(
        b56.ROOT
        / "research"
        / "p3_b56_allowlisted_diagnostic_transport_review_required_2026-09-19.json"
    )
    assert review["status"] == "review_required_after_single_authorized_diagnostic_failure"
    assert review["next_execution_authorized"] is False
    assert review["result"]["diagnostic_category"] == "ffmpeg_or_postprocessing"
    assert review["result"]["public_artifact_count"] == 0
    assert review["result"]["stderr_material_persisted"] is False
    assert all(value == 0 for value in review["aggregate_denied_action_counts"].values())
    assert review["offline_differential"]["yt_dlp_ffmpeg_postprocessor_available"] is True
    assert review["offline_differential"]["direct_ffmpeg_synthetic_pipeline_exit_code"] == 0
    for binding in review["bindings"].values():
        assert b56.sha256_file(b56.ROOT / binding["path"]) == binding["sha256"]
