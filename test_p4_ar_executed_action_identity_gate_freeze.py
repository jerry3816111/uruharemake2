import json
from pathlib import Path

import p4_ar_executed_action_identity_gate as gate


ROOT = Path(__file__).resolve().parent


def test_p4_ar_contract_and_dataset_are_frozen_before_implementation():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)

    assert contract["status"] == "prospectively_frozen_before_p4_ar_implementation"
    assert dataset["status"] == "prospectively_frozen_before_p4_ar_implementation"
    assert len(dataset["development_cases"]) == 1
    assert len(dataset["fresh_authorized_cases"]) == 3
    assert len(dataset["fresh_blocked_cases"]) == 5
    assert len(dataset["control_cases"]) == 2


def test_p4_ar_freeze_forbids_identity_or_evidence_shortcuts():
    policy = gate.load_contract()["failure_policy"]

    assert policy["weaken_p1_identity_allowed"] is False
    assert policy["fallback_id_may_be_promoted_to_p1"] is False
    assert policy["unexecuted_action_may_enter_outcome_verification"] is False
    assert policy["visible_reply_change_allowed"] is False
    assert policy["model_call_allowed"] is False
    assert policy["factual_memory_write_allowed"] is False


def test_p4_ar_fresh_cases_do_not_relabel_the_exposed_p4_aq_case():
    dataset = gate.load_dataset(gate.load_contract())
    development_ids = {row["case_id"] for row in dataset["development_cases"]}
    fresh_ids = {
        row["case_id"]
        for key in ("fresh_authorized_cases", "fresh_blocked_cases")
        for row in dataset[key]
    }

    assert development_ids == {"p4-aq-exposed-fallback-without-executed-action"}
    assert development_ids.isdisjoint(fresh_ids)


def test_p4_ar_dataset_contains_no_raw_dialogue_or_private_claim():
    dataset = gate.load_dataset(gate.load_contract())
    serialized = json.dumps(dataset, ensure_ascii=False, sort_keys=True)

    assert "user_text" not in serialized
    assert "assistant_reply" not in serialized
    assert "private_state_truth" not in serialized
