import json

import p4_as_selected_action_surface_execution_gate as gate


def test_p4_as_contract_and_cases_are_frozen_before_implementation():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)

    assert contract["status"] == "prospectively_frozen_before_p4_as_implementation"
    assert dataset["status"] == "prospectively_frozen_before_p4_as_implementation"
    assert len(dataset["development_cases"]) == 1
    assert len(dataset["fresh_positive_cases"]) == 6
    assert len(dataset["fresh_control_cases"]) == 6


def test_p4_as_freeze_requires_real_surface_execution_before_event_commit():
    policy = gate.load_contract()["failure_policy"]

    assert policy["user_first_person_without_third_party_required"] is True
    assert policy["verified_surface_before_receipt_required"] is True
    assert policy["exact_p1_receipt_and_pending_required"] is True
    assert policy["p1_guard_weakening_allowed"] is False
    assert policy["m39_or_m44_source_change_allowed"] is False
    assert policy["surface_change_outside_exact_authority_allowed"] is False


def test_p4_as_controls_cover_attribution_quote_resolution_and_literal_motion():
    dataset = gate.load_dataset(gate.load_contract())
    ids = {row["case_id"] for row in dataset["fresh_control_cases"]}

    assert {"third-party-en", "third-party-zh"} <= ids
    assert {"metalinguistic-ja", "metalinguistic-en"} <= ids
    assert {"resolved-user-state-en", "ordinary-object-motion-zh"} <= ids


def test_p4_as_fresh_cases_do_not_relabel_the_p4_ar_real_case():
    dataset = gate.load_dataset(gate.load_contract())
    development_inputs = {row["input"] for row in dataset["development_cases"]}
    fresh_inputs = {
        row["input"]
        for key in ("fresh_positive_cases", "fresh_control_cases")
        for row in dataset[key]
    }

    assert development_inputs == {
        "Thought after thought fills my head and cannot settle tonight."
    }
    assert development_inputs.isdisjoint(fresh_inputs)


def test_p4_as_dataset_never_labels_private_state_as_truth():
    dataset = gate.load_dataset(gate.load_contract())
    serialized = json.dumps(dataset, ensure_ascii=False, sort_keys=True)

    assert "private_state_truth" not in serialized
    assert "preferred_reply" not in serialized
    assert "mind_reading" not in serialized
