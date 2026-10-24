from copy import deepcopy

import pytest

import p3_b52_metadata_only_source_freeze as b52


def candidate(video_id, date, *, duration=3600):
    return {
        "source_id": f"youtube_{video_id}",
        "platform": "youtube",
        "video_id": video_id,
        "publisher_channel_id": "UC5LyYg6cCA4yHEYvtUsir3g",
        "published_at": date,
        "duration_seconds": duration,
        "availability": "public",
        "live_status": "was_live",
    }


def synthetic_candidates():
    return [
        candidate("new-source-a", "2026-05-01"),
        candidate("new-source-b", "2026-06-02", duration=5400),
        candidate("new-source-c", "2026-08-03", duration=7200),
    ]


def synthetic_exclusions(*ids):
    return {"excluded_video_ids": list(ids)}


def test_same_metadata_and_seed_produce_same_selection_receipt():
    first = b52.select_metadata_only_source(
        synthetic_candidates(), exclusions=synthetic_exclusions()
    )
    second = b52.select_metadata_only_source(
        list(reversed(synthetic_candidates())), exclusions=synthetic_exclusions()
    )

    assert first["selected_video_id"] == second["selected_video_id"]
    assert first["candidate_set_hash"] == second["candidate_set_hash"]
    assert first["receipt_hash"] == second["receipt_hash"]
    assert first["model_call_count"] == 0
    assert first["future_response_access_count"] == 0


@pytest.mark.parametrize(
    "forbidden_key",
    ["title", "description", "transcript", "comments", "view_count"],
)
def test_content_or_popularity_metadata_fails_closed(forbidden_key):
    rows = synthetic_candidates()
    rows[0][forbidden_key] = "must never influence selection"

    with pytest.raises(b52.B52ContractError, match="forbidden_keys"):
        b52.select_metadata_only_source(rows, exclusions=synthetic_exclusions())


def test_replacing_candidate_changes_candidate_and_receipt_hashes():
    first = b52.select_metadata_only_source(
        synthetic_candidates(), exclusions=synthetic_exclusions()
    )
    changed = synthetic_candidates()
    changed[-1] = candidate("new-source-d", "2026-08-03", duration=7200)
    second = b52.select_metadata_only_source(
        changed, exclusions=synthetic_exclusions()
    )

    assert first["candidate_set_hash"] != second["candidate_set_hash"]
    assert first["receipt_hash"] != second["receipt_hash"]


def test_changing_seed_changes_receipt_even_if_winner_happens_to_match():
    contract = b52.load_contract()
    first = b52.select_metadata_only_source(
        synthetic_candidates(), contract, synthetic_exclusions()
    )
    changed = deepcopy(contract)
    changed["selection"]["seed"] = "different-prospective-seed"
    second = b52.select_metadata_only_source(
        synthetic_candidates(), changed, synthetic_exclusions()
    )

    assert first["receipt_hash"] != second["receipt_hash"]
    assert first["selection_score"] != second["selection_score"]


def test_empty_input_and_empty_eligible_set_fail_closed():
    with pytest.raises(b52.B52ContractError, match="empty_candidate_set"):
        b52.select_metadata_only_source([], exclusions=synthetic_exclusions())
    outside = [candidate("too-old", "2025-01-01")]
    with pytest.raises(b52.B52ContractError, match="empty_eligible_set"):
        b52.select_metadata_only_source(outside, exclusions=synthetic_exclusions())


def test_known_source_wrong_channel_and_nonstream_are_ineligible():
    known = candidate("known", "2026-06-01")
    wrong = candidate("wrong-channel", "2026-06-01")
    wrong["publisher_channel_id"] = "UC_wrong"
    upload = candidate("ordinary-upload", "2026-06-01")
    upload["live_status"] = "not_live"
    fresh = candidate("fresh", "2026-06-01")

    result = b52.select_metadata_only_source(
        [known, wrong, upload, fresh],
        exclusions=synthetic_exclusions("known"),
    )

    assert result["selected_video_id"] == "fresh"
    assert result["eligible_count"] == 1
    assert result["rejected_counts"] == {
        "wrong_target": 1,
        "outside_date_window": 0,
        "outside_duration_window": 0,
        "not_public_completed_livestream": 1,
        "known_source": 1,
    }


def test_sanitizer_never_emits_raw_content_fields():
    raw = {
        "id": "fresh",
        "channel_id": "UC5LyYg6cCA4yHEYvtUsir3g",
        "upload_date": "20260601",
        "duration": 3600.0,
        "availability": "public",
        "live_status": "was_live",
        "title": "forbidden",
        "description": "forbidden",
        "comments": ["forbidden"],
    }
    sanitized = b52.sanitize_ytdlp_entry(raw, b52.load_contract())

    assert set(sanitized) == set(
        b52.load_contract()["candidate_schema"]["allowed_keys"]
    )
    assert not any(key in sanitized for key in ("title", "description", "comments"))
    assert sanitized["duration_seconds"] == 3600


def test_binding_drift_fails_before_selection():
    contract = b52.load_contract()
    drifted = deepcopy(contract)
    drifted["bindings"]["temporal_forecast_bridge"]["sha256"] = "0" * 64

    with pytest.raises(b52.B52ContractError, match="binding_hash_mismatch"):
        b52.select_metadata_only_source(
            synthetic_candidates(), drifted, synthetic_exclusions()
        )


def test_implementation_is_frozen_before_live_metadata_retrieval():
    report = b52.validate_implementation_freeze()

    assert report == {
        "valid": True,
        "frozen_artifact_count": 4,
        "live_metadata_retrieval_count_at_freeze": 0,
        "target_segment_access_count_at_freeze": 0,
        "model_call_count_at_freeze": 0,
    }
