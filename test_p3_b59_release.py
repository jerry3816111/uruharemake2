import p3_b59_source_semantic_availability_probe as b59


def test_b59_release_binds_evidence_and_requires_b60_capability_separation():
    release = b59.load_json(
        b59.ROOT
        / "research"
        / "p3_b59_source_semantic_availability_probe_release_2026-09-20.json"
    )
    assert release["status"] == "released_metadata_only_caption_path_available"
    assert release["result"]["automatic_japanese_available"] is True
    assert release["result"]["selected_track_type"] == "automatic"
    assert release["result"]["selected_language_code"] == "ja"
    assert release["result"]["selected_format"] == "json3"
    assert release["result"]["caption_content_download_count"] == 0
    assert release["b60_design_authorized_under_standing_plan"] is True
    assert release["b60_content_execution_requires_separate_prospective_freeze"] is True
    separation = release["b60_required_separation"]
    assert separation["private_acquisition_may_temporarily_observe_full_caption"] is True
    assert separation["raw_or_post_cutoff_content_persistence_allowed"] is False
    assert separation["prediction_side_future_access_required"] == 0
    assert separation["public_context_start_seconds"] == 3000.0
    assert separation["public_context_end_seconds"] == 3180.0
    for binding in release["bindings"].values():
        assert b59.sha256_file(b59.ROOT / binding["path"]) == binding["sha256"]
