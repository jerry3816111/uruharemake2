import json

import p4_aw_cjk_subject_ellipsis_action_authority_gate as gate


def test_p4_aw_contract_and_cases_are_frozen_before_implementation():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)

    assert contract["status"] == "prospectively_frozen_before_implementation"
    assert dataset["status"] == "prospectively_frozen_before_implementation"
    assert len(dataset["cases"]) == 21
    assert sum(row["split"] == "exposed_development" for row in dataset["cases"]) == 1
    assert sum(row["split"] == "fresh_positive" for row in dataset["cases"]) == 6
    assert sum(row["split"] == "fresh_control" for row in dataset["cases"]) == 12
    assert sum(row["split"] == "predecessor_control" for row in dataset["cases"]) == 2


def test_p4_aw_freeze_requires_final_exact_chain_and_new_safari_case():
    contract = gate.load_contract()
    failure = contract["failure_policy"]

    assert failure["provisional_ellipsis_without_final_exact_chain_may_authorize"] is False
    assert failure["third_party_quote_report_hypothetical_resolved_or_physical_control_may_authorize"] is False
    assert failure["offline_pass_may_rewrite_p4_av_real_failure"] is False
    assert failure["offline_pass_may_authorize_p4_av_real_product_claim"] is False
    assert failure["fresh_safari_case_required_after_offline_pass"] is True


def test_p4_aw_controls_cover_all_required_false_authority_families():
    dataset = gate.load_dataset(gate.load_contract())
    families = {
        row.get("control_family")
        for row in dataset["cases"]
        if row["split"] == "fresh_control"
    }

    assert families == {
        "third_party",
        "quoted_metalinguistic",
        "news_or_report",
        "physical_object_motion",
        "resolved_state",
        "ambiguous_role",
    }
    for family in families:
        rows = [
            row
            for row in dataset["cases"]
            if row.get("control_family") == family
        ]
        assert {row["language"] for row in rows} == {"zh", "ja"}


def test_p4_aw_fresh_cases_do_not_reuse_the_exposed_real_input():
    dataset = gate.load_dataset(gate.load_contract())
    exposed = {
        row["input"]
        for row in dataset["cases"]
        if row["split"] == "exposed_development"
    }
    fresh = {
        row["input"]
        for row in dataset["cases"]
        if row["split"] in {"fresh_positive", "fresh_control"}
    }

    assert len(exposed) == 1
    assert exposed.isdisjoint(fresh)


def test_p4_aw_dataset_claims_no_private_truth_or_open_domain_coreference():
    dataset = gate.load_dataset(gate.load_contract())
    serialized = json.dumps(dataset, ensure_ascii=False, sort_keys=True)

    assert "not open-domain coreference" in dataset["claim_boundary"]
    assert "private-state truth" in dataset["claim_boundary"]
    assert "preferred_reply" not in serialized
    assert "mind_reading" not in serialized
