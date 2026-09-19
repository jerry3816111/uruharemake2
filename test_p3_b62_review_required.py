import p3_b62_real_context_prediction_freeze as b62


def test_b62_review_corrects_call_count_and_keeps_future_locked():
    review = b62.load_json(
        b62.ROOT / "research" / "p3_b62_real_context_prediction_review_required_2026-09-20.json"
    )
    assert review["status"] == "prediction_not_frozen_after_first_representation_schema_failure"
    assert review["raw_result"]["recorded_model_call_count"] == 0
    assert review["operational_accounting_correction"]["actual_model_call_count"] == 1
    assert review["operational_accounting_correction"]["prompt_tokens"] == "unavailable"
    assert review["operational_accounting_correction"]["zero_is_not_a_valid_substitute"] is True
    assert review["next_stage"]["id"] == "P3-B63"
    assert review["next_stage"]["research_question_or_condition_change_allowed"] is False
    assert review["next_stage"]["future_outcome_unlock_authorized"] is False
    assert review["next_stage"]["retry_or_fallback_authorized"] is False
    for binding in review["bindings"].values():
        assert b62.sha256_file(b62.ROOT / binding["path"]) == binding["sha256"]
