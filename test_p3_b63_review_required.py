import p3_b63_schema_enforced_real_context_predictions as b63


def test_b63_review_allows_only_final_equal_budget_reallocation():
    review = b63.load_json(
        b63.ROOT / "research" / "p3_b63_schema_enforced_prediction_review_required_2026-09-20.json"
    )
    assert review["status"] == "prediction_not_frozen_after_representation_hit_token_ceiling"
    assert review["result"]["completion_tokens"] == review["result"]["num_predict"] == 256
    assert review["result"]["future_outcome_access_count"] == 0
    assert review["prediction_correction_batches_consumed"] == 1
    assert review["next_stage"]["id"] == "P3-B64"
    assert review["next_stage"]["correction_batch_ordinal"] == 2
    assert review["next_stage"]["final_prediction_execution_correction"] is True
    assert review["next_stage"]["future_outcome_unlock_authorized"] is False
    assert review["next_stage"]["retry_schema_relaxation_or_total_budget_increase_authorized"] is False
    for binding in review["bindings"].values():
        assert b63.sha256_file(b63.ROOT / binding["path"]) == binding["sha256"]
