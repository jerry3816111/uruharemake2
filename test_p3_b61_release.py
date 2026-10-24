import p3_b61_native_subtitle_cutoff_extractor as b61


def test_b61_release_binds_real_context_and_locks_future_until_prediction_freeze():
    release = b61.load_json(
        b61.ROOT / "research" / "p3_b61_native_subtitle_cutoff_extractor_release_2026-09-20.json"
    )
    assert release["status"] == "released_real_pre_cutoff_context"
    result = release["result"]
    assert result["context_seconds"] == [3000.0, 3180.0]
    assert result["public_cue_count"] == 65
    assert result["public_first_cue_start_seconds"] >= 3000.0
    assert result["public_last_cue_end_seconds"] <= 3180.0
    assert result["prediction_side_future_access_count"] == 0
    assert result["prediction_execution_count"] == 0
    assert release["b62_design_authorized_under_standing_plan"] is True
    assert release["b62_execution_requires_prediction_contract_and_freeze_before_future_unlock"] is True
    assert release["b62_required_controls"]["same_context_artifact_for_all_conditions"] is True
    assert release["b62_required_controls"]["future_outcome_access_before_prediction_freeze_required"] == 0
    assert release["b62_required_controls"]["same_base_model_and_generation_budget"] is True
    for binding in release["bindings"].values():
        assert b61.sha256_file(b61.ROOT / binding["path"]) == binding["sha256"]
