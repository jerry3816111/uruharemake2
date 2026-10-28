import p3_b57_split_resolver_direct_ffmpeg as b57


def test_b57_review_record_binds_result_and_denies_header_aware_execution():
    review = b57.load_json(
        b57.ROOT
        / "research"
        / "p3_b57_split_resolver_direct_ffmpeg_review_required_2026-09-19.json"
    )
    assert review["status"] == "review_required_after_resolver_success_and_direct_ffmpeg_transport_failure"
    assert review["next_execution_authorized"] is False
    assert review["result"]["resolver_returncode"] == 0
    assert review["result"]["direct_ffmpeg_returncode"] == 8
    assert review["result"]["failure_category"] == "tls_or_network"
    assert review["result"]["private_url_material_persisted"] is False
    assert review["result"]["public_artifact_count"] == 0
    assert "Cookie" not in review["allowed_header_names_for_review"]
    assert "Authorization" not in review["allowed_header_names_for_review"]
    assert all(value == 0 for value in review["aggregate_denied_action_counts"].values())
    for binding in review["bindings"].values():
        assert b57.sha256_file(b57.ROOT / binding["path"]) == binding["sha256"]
