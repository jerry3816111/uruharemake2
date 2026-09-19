import p3_b60_private_caption_cutoff_extractor as b60


def test_b60_review_allows_only_final_native_downloader_correction():
    review = b60.load_json(
        b60.ROOT / "research" / "p3_b60_private_caption_cutoff_extractor_review_required_2026-09-20.json"
    )
    assert review["status"] == "caption_get_failed_before_private_raw_access"
    assert review["result"]["failure_stage"] == "caption_get"
    assert review["result"]["private_acquisition_full_caption_access_count"] == 0
    assert review["result"]["prediction_side_future_access_count"] == 0
    assert review["caption_path_correction_batches_consumed"] == 1
    assert review["next_stage"]["id"] == "P3-B61"
    assert review["next_stage"]["correction_batch_ordinal"] == 2
    assert review["next_stage"]["final_caption_path_correction"] is True
    assert review["next_stage"]["same_source_track_cutoff_and_reader_required"] is True
    assert review["next_stage"]["retry_cookie_login_or_paid_access_authorized"] is False
    for binding in review["bindings"].values():
        assert b60.sha256_file(b60.ROOT / binding["path"]) == binding["sha256"]
