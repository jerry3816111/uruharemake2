from copy import deepcopy
from pathlib import Path

import pytest

import p4_al_past_present_future_commitment_gate as gate
import uruha_past_present_future_commitment_p4 as temporal


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets/p4_al_past_present_future_commitment_v1.json"


def test_frozen_temporal_commitment_cases_pass():
    evidence = temporal.build_dataset_evidence_p4_al(DATASET)
    result = gate.evaluate_evidence(gate.load_contract(), evidence)
    assert result["status"] == "pass", result["failed_gates"]
    assert result["failed_gates"] == []


def test_commitment_tampering_and_nonpast_records_fail_closed():
    frozen = gate.load_dataset(gate.load_contract())["cases"][0]
    pending = temporal._synthetic_pending(frozen)
    commitment = temporal.build_temporal_commitment_p4(
        frozen["past_records"], pending, frozen["current_turn"]
    )
    tampered = deepcopy(commitment)
    tampered["future"]["selected_policy_prediction"] = "playful_tease"
    assert temporal.validate_commitment_hash_p4(tampered) is False
    invalid_past = deepcopy(frozen["past_records"])
    invalid_past[0]["observed_turn"] = frozen["current_turn"]
    with pytest.raises(temporal.P4ALTemporalError, match="past_not_strictly_before_present"):
        temporal.build_temporal_commitment_p4(invalid_past, pending, frozen["current_turn"])


def test_graph_payload_shows_three_time_slices_before_utterance_without_raw_content():
    frozen = gate.load_dataset(gate.load_contract())["cases"][2]
    pending = temporal._synthetic_pending(frozen)
    commitment = temporal.build_temporal_commitment_p4(
        frozen["past_records"], pending, frozen["current_turn"]
    )
    result = temporal.append_temporal_commitment_node_p4(
        {
            "logic": {},
            "runtime_trace": {
                "blackboard": [{"stage": "surface", "label": "utterance", "payload": {}}]
            },
        },
        commitment,
    )
    labels = [row["label"] for row in result["runtime_trace"]["blackboard"]]
    assert labels == [temporal.LABEL, "utterance"]
    payload = result["logic"][temporal.LABEL]
    assert payload["past"]["record_count"] == 2
    assert payload["present"]["candidate_count"] == 6
    assert payload["future"]["status"] == "committed_outcome_locked"
    assert payload["raw_dialogue_persisted"] is False
    assert payload["private_state_truth_claimed"] is False
