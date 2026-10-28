import hashlib
from pathlib import Path

import p4_al_past_present_future_commitment_gate as gate


ROOT = Path(__file__).resolve().parent


def test_contract_binds_temporal_method_outcome_binding_and_preserved_failure():
    contract = gate.load_contract()
    dataset_path = ROOT / contract["dataset"]["path"]
    assert hashlib.sha256(dataset_path.read_bytes()).hexdigest() == contract["dataset"]["sha256"]
    for path_text, digest in contract["bindings"].values():
        assert hashlib.sha256((ROOT / path_text).read_bytes()).hexdigest() == digest


def test_frozen_cases_define_strict_temporal_order_and_balanced_outcomes():
    cases = gate.load_dataset(gate.load_contract())["cases"]
    assert len(cases) == 3
    assert {row["expected_outcome"] for row in cases} == {"supported", "contradicted", "unknown"}
    assert all(
        past["observed_turn"] < row["current_turn"]
        for row in cases
        for past in row["past_records"]
    )


def test_frozen_dataset_contains_no_dialogue_or_private_state_payload():
    dataset = gate.load_dataset(gate.load_contract())
    serialized = str(dataset).lower()
    for forbidden in ("raw_text", "user_input", "private_emotion", "private_motive", "target_reply"):
        assert forbidden not in serialized


def test_claim_and_authorization_boundaries_are_explicit():
    contract = gate.load_contract()
    assert contract["implementation_boundary"]["p4_ak_status_rewrite_allowed"] is False
    assert contract["failure_policy"]["real_person_prediction_authorized"] is False
    assert "does not establish predictive accuracy" in contract["claim_boundary"]
