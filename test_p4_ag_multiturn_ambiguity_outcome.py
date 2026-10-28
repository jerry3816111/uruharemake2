from pathlib import Path

import p4_ag_multiturn_ambiguity_outcome_gate as gate
import uruha_desired_response_outcome_binding_p4 as outcome


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "p4_ag_multiturn_ambiguity_outcome_v1.json"


def _synthetic_binding():
    return {
        "schema": outcome.SCHEMA,
        "status": "pending",
        "ledger_id": "p4-ag-test",
        "prediction_id": "prediction-test",
        "selected_policy": "calibrate_need",
        "candidate_snapshots": [
            {
                "candidate_id": "p4-ag-test:calibrate_need",
                "policy_id": "calibrate_need",
                "mode": "low_pressure_clarification",
                "selected_before_outcome": True,
            },
            {
                "candidate_id": "p4-ag-test:playful_tease",
                "policy_id": "playful_tease",
                "mode": "playful_tease",
                "selected_before_outcome": False,
            },
        ],
    }


def test_explicit_correction_revokes_selected_and_supports_only_named_replacement():
    resolved = outcome.resolve_outcome_binding_p4(
        _synthetic_binding(),
        {
            "status": "contradicted",
            "previous_prediction_id": "prediction-test",
            "feedback_linked_to_previous_prediction": True,
            "feedback_linkage_reason": "explicit_feedback_reference",
            "explicit_target_policy": "playful_tease",
            "evidence": {"digest": "digest-only"},
        },
        2,
    )
    updates = {row["policy_id"]: row for row in resolved["candidate_updates"]}
    assert resolved["identity_bound"] is True
    assert resolved["outcome"] == "contradicted"
    assert updates["calibrate_need"]["outcome"] == "contradicted"
    assert updates["calibrate_need"]["operational_priority_allowed"] is False
    assert updates["playful_tease"]["outcome"] == "supported"
    assert updates["playful_tease"]["operational_priority_allowed"] is True
    assert resolved["reversible_next_use"]["private_truth_commitment"] is False


def test_unlinked_turn_keeps_all_candidates_unknown_and_never_counts_success():
    resolved = outcome.resolve_outcome_binding_p4(
        _synthetic_binding(),
        {
            "status": "uncertain",
            "previous_prediction_id": "prediction-test",
            "feedback_linked_to_previous_prediction": False,
            "evidence": {"digest": "digest-only"},
        },
        2,
    )
    assert resolved["identity_bound"] is True
    assert resolved["outcome"] == "unknown"
    assert resolved["unknown_counted_as_success"] is False
    assert resolved["outcome_counts_as_success"] is False
    assert all(row["outcome"] == "unknown" for row in resolved["candidate_updates"])
    assert resolved["reversible_next_use"]["status"] == "not_available"


def test_frozen_multiturn_sequences_preserve_initial_upstream_coverage_failure():
    evidence = outcome.build_dataset_evidence_p4_ag(DATASET)
    result = gate.evaluate_evidence(gate.load_contract(), evidence)
    assert result["status"] == "fail"
    assert evidence["metrics"]["first_turn_eligible_count"] == 7
    assert evidence["metrics"]["stable_prediction_binding_count"] == 7
    assert evidence["metrics"]["unknown_counted_as_success_count"] == 0
    assert {
        row["case_id"]
        for row in evidence["sequences"]
        if not row["first_turn_eligible"]
    } == {
        "ag_fresh_contradict_with_tease_ja",
        "ag_fresh_unrelated_topic_en",
    }
    assert "ag_fresh_contradict_with_tease_ja:first_turn_not_eligible" in result["failed_gates"]
    assert "ag_fresh_unrelated_topic_en:first_turn_not_eligible" in result["failed_gates"]
