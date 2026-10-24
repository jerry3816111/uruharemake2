import p3_b58_private_allowlisted_header_transport as b58


def test_b58_review_closes_direct_audio_retry_and_routes_to_metadata_only_probe():
    review = b58.load_json(
        b58.ROOT
        / "research"
        / "p3_b58_private_allowlisted_header_transport_review_required_2026-09-20.json"
    )
    assert review["status"] == "direct_audio_branch_closed_after_two_prospective_corrections"
    assert review["result"]["resolver_returncode"] == 0
    assert review["result"]["private_allowlisted_header_count"] == 3
    assert review["result"]["direct_ffmpeg_returncode"] == 8
    assert review["result"]["failure_category"] == "tls_or_network"
    assert review["result"]["private_url_or_header_material_persisted"] is False
    assert review["direct_audio_branch"]["correction_batches_consumed"] == 2
    assert review["direct_audio_branch"]["additional_parameter_retry_authorized"] is False
    assert review["direct_audio_branch"]["same_path_retry_authorized"] is False
    assert review["next_stage"]["id"] == "P3-B59"
    assert review["next_stage"]["caption_content_download_authorized"] is False
    assert review["next_stage"]["hidden_future_content_access_authorized"] is False
    assert review["next_stage"]["prediction_or_model_authorized"] is False
    assert all(value == 0 for value in review["aggregate_denied_action_counts"].values())
    for binding in review["bindings"].values():
        assert b58.sha256_file(b58.ROOT / binding["path"]) == binding["sha256"]
