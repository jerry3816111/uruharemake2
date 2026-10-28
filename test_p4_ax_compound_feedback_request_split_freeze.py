import json

import p4_ax_compound_feedback_request_split_gate as gate


def test_p4_ax_contract_and_cases_are_frozen_before_implementation():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)

    assert contract["status"] == "prospectively_frozen_before_implementation"
    assert dataset["status"] == "prospectively_frozen_before_implementation"
    assert len(dataset["cases"]) == 28
    assert sum(row["split"] == "exposed_development" for row in dataset["cases"]) == 1
    assert sum(row["split"] == "fresh_positive" for row in dataset["cases"]) == 9
    assert sum(row["split"] == "fresh_control" for row in dataset["cases"]) == 12
    assert sum(row["split"] == "predecessor_control" for row in dataset["cases"]) == 6


def test_p4_ax_fresh_positive_matrix_is_three_families_by_three_languages():
    dataset = gate.load_dataset(gate.load_contract())
    positives = [row for row in dataset["cases"] if row["split"] == "fresh_positive"]

    assert {row["language"] for row in positives} == {"zh", "en", "ja"}
    assert {row["positive_family"] for row in positives} == {
        "response_kind_confirmation",
        "need_direction_clarification",
        "preanswer_need_clarity",
    }
    for family in {row["positive_family"] for row in positives}:
        assert {row["language"] for row in positives if row["positive_family"] == family} == {"zh", "en", "ja"}


def test_p4_ax_controls_cover_false_link_families_in_all_languages():
    dataset = gate.load_dataset(gate.load_contract())
    controls = [row for row in dataset["cases"] if row["split"] == "fresh_control"]
    families = {row["control_family"] for row in controls}

    assert families == {
        "third_party",
        "quoted_metalinguistic",
        "generic_confirmation",
        "hypothetical",
    }
    for family in families:
        assert {row["language"] for row in controls if row["control_family"] == family} == {"zh", "en", "ja"}


def test_p4_ax_fresh_cases_are_disjoint_from_exposed_and_prior_p4_at_dataset():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)
    prior = json.loads((gate.ROOT / "datasets/p4_at_executed_action_outcome_closure_v1.json").read_text(encoding="utf-8"))
    exposed = {row["input"] for row in dataset["cases"] if row["split"] == "exposed_development"}
    fresh = {row["input"] for row in dataset["cases"] if row["split"] in {"fresh_positive", "fresh_control"}}
    prior_turns = {
        row.get("turn_2")
        for partition in ("development_sequences", "fresh_positive_sequences", "fresh_control_sequences")
        for row in prior.get(partition, [])
    }

    assert len(exposed) == 1
    assert exposed.isdisjoint(fresh)
    assert fresh.isdisjoint(prior_turns)


def test_p4_ax_failure_policy_preserves_independent_delivery_gates():
    failure = gate.load_contract()["failure_policy"]

    assert failure["generic_confirmation_may_count_as_previous_action_support"] is False
    assert failure["third_party_quote_or_hypothetical_may_count_as_support"] is False
    assert failure["missing_exact_receipt_may_count_as_support"] is False
    assert failure["offline_pass_may_rewrite_p4_aw_real_failure"] is False
    assert failure["offline_pass_may_bypass_m46_m45_failure"] is False
    assert failure["fresh_safari_case_required_after_offline_pass"] is True
