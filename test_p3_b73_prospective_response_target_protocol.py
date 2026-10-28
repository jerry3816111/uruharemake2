from copy import deepcopy
import hashlib

import p3_b73_prospective_response_target_protocol as b73


def _packet(acoustic=False):
    response = "そういうことなら、もう少し聞かせて。"
    return {
        "schema": "uruha_p3_b73_response_episode_packet_v1",
        "episode_id": "episode_0001",
        "provenance": {
            "source_id": "synthetic-only",
            "source_url": "https://example.invalid/synthetic",
            "publisher": "synthetic-fixture",
            "observed_at": "2026-09-20T00:00:00Z",
        },
        "stimulus": {
            "surface_form_id": "surface_001",
            "context_variant_id": "context_a",
            "utterance_text": "もういい。",
            "pre_context_text": "synthetic context",
            "boundary_status": "usable_stimulus_response_pair",
            "pub_coverage_bucket": "IMPLICATURE",
            "relationship_evidence": [],
            "memory_evidence": [],
            "modality": {
                "text_available": True,
                "acoustic_summary_status": "available" if acoustic else "unavailable",
                "acoustic_features": {"pause_ms": 700} if acoustic else None,
            },
        },
        "outcome": {
            "response_text": response,
            "response_text_sha256": hashlib.sha256(response.encode("utf-8")).hexdigest(),
            "response_start_ms": 1000,
            "response_end_ms": 2500,
        },
        "blinding": {
            "prediction_frozen_before_outcome_access": True,
            "condition_identity_visible_to_coder": False,
            "model_prediction_visible_to_coder": False,
        },
    }


def _entry(episode_id, variant):
    choices = [
        ("ASK_CLARIFY", "SEEK_INFORMATION", "UNCERTAIN", "INDIRECT_CONTEXT_DEPENDENT"),
        ("SUPPORT_COMFORT", "AFFILIATE_OR_COMFORT", "WARM_SUPPORTIVE", "LITERAL_ALIGNED"),
        ("HUMOR_TEASE", "PLAY_OR_TEASE", "PLAYFUL", "OVERINTERPRETATION_RISK_CONTROL"),
    ]
    move, goal, stance, relation = choices[variant % len(choices)]
    return {
        "episode_id": episode_id,
        "response_moves": [move],
        "primary_interaction_goal": goal,
        "alternative_goals": [],
        "stance": stance,
        "literal_pragmatic_relation": relation,
        "evidence_anchor_count": 1,
        "private_motive_asserted": False,
        "completed_without_prediction_visibility": True,
        "coder_kind": "consenting_human",
    }


def _ledger(pseudonym, episode_ids, *, disagreement_from=None):
    entries = {}
    for index, episode_id in enumerate(episode_ids):
        variant = index % 3
        if disagreement_from is not None and index >= disagreement_from:
            variant = (variant + 1) % 3
        entries[episode_id] = _entry(episode_id, variant)
    return {
        "schema": "uruha_p3_b73_private_human_annotation_ledger_v1",
        "coder_pseudonym": pseudonym,
        "coder_kind": "consenting_human",
        "entries": entries,
    }


def test_contract_is_bound_before_new_content_and_has_zero_execution_counts():
    contract = b73.load_contract()
    assert b73.validate_contract(contract) == {"valid": True, "errors": []}
    assert all(value == 0 for value in contract["execution_limits"].values())
    assert contract["pilot_reliability"]["synthetic_or_llm_labels_authorize_human_reliability"] is False


def test_prediction_view_cannot_see_outcome_and_coder_view_cannot_see_condition():
    packet = _packet()
    assert b73.validate_episode_packet(packet) == []
    prediction = b73.build_prediction_view(packet)
    coder = b73.build_coder_view(packet)
    assert "outcome" not in prediction
    assert prediction["outcome_access_count"] == 0
    assert coder["outcome"]["response_text"] == packet["outcome"]["response_text"]
    assert coder["condition_identity_visible"] is False
    assert coder["model_prediction_visible"] is False


def test_missing_acoustics_must_be_unavailable_and_cannot_be_invented():
    packet = _packet()
    packet["stimulus"]["modality"]["acoustic_features"] = {"claimed_tone": "sad"}
    assert "modality:invented_acoustics" in b73.validate_episode_packet(packet)
    assert b73.validate_episode_packet(_packet(acoustic=True)) == []


def test_unusable_or_unbounded_episode_is_rejected_not_default_labeled():
    packet = _packet()
    packet["stimulus"]["boundary_status"] = "unusable_boundary"
    packet["outcome"]["response_end_ms"] = packet["outcome"]["response_start_ms"]
    errors = b73.validate_episode_packet(packet)
    assert "stimulus:boundary_status" in errors
    assert "outcome:boundary" in errors


def test_prediction_or_score_fields_are_forbidden_from_episode_packet():
    packet = _packet()
    packet["system_prediction"] = {"anything": True}
    assert "forbidden_prediction_fields" in b73.validate_episode_packet(packet)


def test_annotation_requires_human_kind_alternatives_and_no_private_motive():
    entry = _entry("episode_0001", 0)
    assert b73.validate_annotation_entry(entry) == []
    changed = deepcopy(entry)
    changed["coder_kind"] = "llm"
    changed["private_motive_asserted"] = True
    changed["alternative_goals"] = [changed["primary_interaction_goal"]]
    errors = b73.validate_annotation_entry(changed)
    assert "coder_kind" in errors
    assert "private_motive_asserted" in errors
    assert "alternative_goals" in errors


def test_identical_varied_two_human_ledgers_pass_synthetic_calculation_only():
    episode_ids = [f"episode_{index:04d}" for index in range(18)]
    ledger_a = _ledger("human-a", episode_ids)
    ledger_b = _ledger("human-b", episode_ids)
    report = b73.build_reliability_report(ledger_a, ledger_b, episode_ids)
    assert report["gates"]["human_reliability_passed"] is True
    assert set(report["primary_nominal_krippendorff_alpha"].values()) == {1.0}
    assert all(value == 3 for value in report["primary_observed_category_count"].values())
    assert report["synthetic_fixture_authorizes_human_reliability"] is False


def test_disagreement_fails_alpha_gate_and_is_preserved():
    episode_ids = [f"episode_{index:04d}" for index in range(18)]
    ledger_a = _ledger("human-a", episode_ids)
    ledger_b = _ledger("human-b", episode_ids, disagreement_from=6)
    report = b73.build_reliability_report(ledger_a, ledger_b, episode_ids)
    assert report["gates"]["human_reliability_passed"] is False
    assert any(value is not None and value < 0.667 for value in report["primary_nominal_krippendorff_alpha"].values())


def test_same_person_or_incomplete_ledger_fails_even_with_agreement():
    episode_ids = [f"episode_{index:04d}" for index in range(18)]
    ledger_a = _ledger("same-human", episode_ids)
    ledger_b = _ledger("same-human", episode_ids[:-1])
    report = b73.build_reliability_report(ledger_a, ledger_b, episode_ids)
    assert report["coder_pseudonyms_distinct"] is False
    assert report["gates"]["both_ledgers_complete_and_valid"] is False
    assert report["gates"]["human_reliability_passed"] is False


def test_readiness_result_does_not_claim_human_evidence():
    result = b73.build_readiness_result()
    assert result["status"] == "protocol_tooling_ready_human_reliability_not_started"
    assert result["pilot"]["actual_human_labels"] == 0
    assert result["pilot"]["reliability_status"] == "not_started"
    assert result["execution_counts"]["new_source_content_access_count"] == 0
    assert result["execution_counts"]["model_call_count"] == 0
