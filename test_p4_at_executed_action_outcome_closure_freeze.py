import json
from pathlib import Path

import p4_at_executed_action_outcome_closure_gate as gate


ROOT = Path(__file__).resolve().parent


def test_p4_at_contract_and_partitions_are_frozen_before_implementation():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)

    assert contract["status"] == "prospectively_frozen_before_p4_at_implementation"
    assert dataset["status"] == "prospectively_frozen_before_p4_at_implementation"
    assert len(dataset["development_sequences"]) == 1
    assert len(dataset["fresh_positive_sequences"]) == 9
    assert len(dataset["fresh_control_sequences"]) == 7


def test_p4_at_freeze_separates_previous_action_feedback_from_current_request():
    dataset = gate.load_dataset(gate.load_contract())
    positives = dataset["fresh_positive_sequences"]

    assert {row["expected_previous_action_outcome"] for row in positives} == {
        "supported",
        "contradicted",
    }
    assert {row["expected_current_request_policy"] for row in positives} == {
        "solve_regulation",
        "listen_presence",
        "playful_tease",
    }
    assert all(row["expected_visible_action_act"] for row in positives)


def test_p4_at_controls_cover_unknown_attribution_and_single_act_boundaries():
    dataset = gate.load_dataset(gate.load_contract())
    controls = {row["case_id"]: row for row in dataset["fresh_control_sequences"]}

    assert {"unrelated-zh", "unrelated-en", "unrelated-ja"} <= set(controls)
    assert {"third-party-en", "metalinguistic-zh", "quoted-ja"} <= set(controls)
    assert controls["current-request-only-en"]["expected_previous_action_outcome"] == "unknown"
    assert controls["current-request-only-en"]["expected_current_request_policy"] == "solve_regulation"


def test_p4_at_temporal_contract_never_backdates_current_evidence():
    temporal = gate.load_dataset(gate.load_contract())["temporal_contract"]

    assert temporal["performed_action_turn_strictly_before_observed_turn"] is True
    assert temporal["prior_future_commitment_consumed_on_turn_2"] is True
    assert temporal["turn_2_outcome_evidence_is_current_not_relabelled_as_older_past"] is True
    assert temporal["turn_2_outcome_eligible_for_past_promotion_on_later_turn"] is True


def test_p4_at_failure_policy_keeps_existing_authorities_and_unknown_boundary():
    policy = gate.load_contract()["failure_policy"]

    assert policy["p4_ag_base_classifier_change_allowed"] is False
    assert policy["p1_or_m44_identity_weakening_allowed"] is False
    assert policy["candidate_score_or_order_change_allowed"] is False
    assert policy["exact_executed_receipt_required_for_prior_action_outcome"] is True
    assert policy["unknown_must_not_count_as_success"] is True
    assert policy["same_turn_verification_must_not_be_backdated"] is True


def test_p4_at_dataset_does_not_label_private_desire_as_truth():
    dataset = gate.load_dataset(gate.load_contract())
    serialized = json.dumps(dataset, ensure_ascii=False, sort_keys=True)

    assert "private_desire_truth" not in serialized
    assert "mind_reading" not in serialized
    assert "human_equation_proved" not in serialized


def test_p4_at_predecessor_files_remain_at_the_frozen_hashes():
    contract = gate.load_contract()
    for path, expected_sha in contract["predecessors"].values():
        assert gate._sha256(ROOT / path) == expected_sha
