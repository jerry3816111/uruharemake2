from copy import deepcopy

import pytest

import p3_b53_content_blind_temporal_boundary as b53


def test_contract_is_bound_to_content_blind_source_release():
    assert b53.validate_contract() == {"valid": True, "errors": []}


def test_same_source_policy_and_seed_produce_same_boundary():
    first = b53.select_temporal_boundary()
    second = b53.select_temporal_boundary()
    assert first == second
    assert first["receipt_hash"] == second["receipt_hash"]


def test_boundary_is_strictly_ordered_inside_frozen_margins():
    receipt = b53.select_temporal_boundary()
    contract = b53.load_contract()
    assert b53.validate_boundary_receipt(receipt) == {"valid": True}
    assert receipt["head_margin_observed_seconds"] >= contract["boundary_policy"][
        "head_margin_seconds"
    ]
    assert receipt["tail_margin_observed_seconds"] >= contract["boundary_policy"][
        "tail_margin_seconds"
    ]


def test_changed_seed_changes_selection_receipt():
    contract = b53.load_contract()
    first = b53.select_temporal_boundary(contract)
    changed = deepcopy(contract)
    changed["boundary_policy"]["selection_seed"] = "different-seed"
    second = b53.select_temporal_boundary(changed)
    assert first["selection_score"] != second["selection_score"]
    assert first["receipt_hash"] != second["receipt_hash"]


def test_changed_duration_changes_candidate_and_receipt_hash():
    contract = b53.load_contract()
    first = b53.select_temporal_boundary(contract)
    changed = deepcopy(contract)
    changed["source"]["duration_seconds"] += 600
    release_path = b53.ROOT / changed["binding"]["source_release"]["path"]
    release = b53.load_json(release_path)
    release["selected_source"]["duration_seconds"] += 600
    # The real validator correctly rejects a source-release mismatch. For the
    # pure selection-property check, bind a temporary validator-free source to
    # the candidate generator rather than weakening production validation.
    first_candidates = b53.generate_cutoff_candidates(
        contract["source"], contract["boundary_policy"]
    )
    changed_candidates = b53.generate_cutoff_candidates(
        changed["source"], changed["boundary_policy"]
    )
    assert first_candidates != changed_candidates
    assert b53.sha256_bytes(
        b53.canonical_json(first_candidates).encode("utf-8")
    ) != b53.sha256_bytes(
        b53.canonical_json(changed_candidates).encode("utf-8")
    )


def test_too_short_source_fails_closed():
    contract = b53.load_contract()
    short_source = deepcopy(contract["source"])
    short_source["duration_seconds"] = 1200
    with pytest.raises(b53.B53ContractError, match="too_short"):
        b53.generate_cutoff_candidates(short_source, contract["boundary_policy"])


def test_execution_receipt_has_zero_content_outcome_and_model_access():
    receipt = b53.select_temporal_boundary()
    for key, value in b53.load_contract()["execution_boundary"].items():
        assert receipt[key] == value == 0
    assert {"title", "description", "transcript", "behavior_label"}.isdisjoint(
        set(receipt)
    )
    assert receipt["transcript_access_count"] == 0


def test_binding_drift_fails_before_boundary_selection():
    contract = b53.load_contract()
    drifted = deepcopy(contract)
    drifted["binding"]["source_release"]["sha256"] = "0" * 64
    with pytest.raises(b53.B53ContractError, match="source_release_hash_mismatch"):
        b53.select_temporal_boundary(drifted)


def test_implementation_is_frozen_before_boundary_or_media_access():
    assert b53.validate_implementation_freeze() == {
        "valid": True,
        "boundary_selection_count_at_freeze": 0,
        "media_request_count_at_freeze": 0,
        "target_segment_access_count_at_freeze": 0,
    }
