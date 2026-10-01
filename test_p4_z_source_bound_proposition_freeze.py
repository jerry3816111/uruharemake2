import json
from pathlib import Path

from p4_z_source_bound_proposition_gate import load_contract, load_dataset
from uruha_source_semantic_atoms_m33 import extract_source_semantic_atoms_m33
from uruha_utterance_frame_shadow_extension_p4 import inspect_utterance_frame_coverage_extension_p4


ROOT = Path(__file__).resolve().parent


def test_p4_z_contract_is_bound_and_partitions_are_disjoint():
    contract = load_contract()
    dataset = load_dataset(contract)
    assert dataset["status"] == "prospectively_frozen_before_implementation"
    assert len(dataset["development_failures"]) == 3
    assert len(dataset["holdout_failures"]) == 9
    assert len(dataset["faithful_controls"]) == 6
    assert len(dataset["unsupported_controls"]) == 3
    dev = {row["source"] for row in dataset["development_failures"]}
    holdout = {row["source"] for row in dataset["holdout_failures"]}
    assert dev.isdisjoint(holdout)
    assert dataset["novelty"]["p4_x_inputs_reused_as_holdout"] is False
    assert dataset["novelty"]["p4_y_inputs_reused_as_holdout"] is False


def test_p4_z_before_evidence_reproduces_the_semantic_gap():
    contract = load_contract()
    dataset = load_dataset(contract)
    m33_unavailable = 0
    frame_after_zero = 0
    exact_proposition_failures = 0
    for row in dataset["development_failures"]:
        ledger = extract_source_semantic_atoms_m33(row["source"], {"projection_required": True})
        m33_unavailable += int(ledger["status"] == "source_pattern_unavailable")
        frame = inspect_utterance_frame_coverage_extension_p4(row["source"], row["candidate"])
        frame_after_zero += int(frame["violations"] == [])
        exact_proposition_failures += int(row["candidate"] != row["expected_reply"])
    assert {
        "development_m33_unavailable_count": m33_unavailable,
        "development_existing_frame_after_zero_count": frame_after_zero,
        "development_exact_proposition_failure_count": exact_proposition_failures,
    } == contract["before_gates"]


def test_p4_z_contract_requires_source_only_fail_closed_behavior():
    dataset = load_dataset(load_contract())
    proposition = dataset["proposition_contract"]
    assert proposition["known_inferred_unknown_separated"] is True
    assert proposition["source_only"] is True
    assert proposition["candidate_may_not_supply_missing_source_fields"] is True
    assert proposition["unsupported_patterns_fail_closed_unchanged"] is True
    assert proposition["required_fields"] == [
        "family",
        "embedding_stance",
        "speaker_owner",
        "subject_jp",
        "predicate_jp",
        "object_jp",
        "time_jp",
        "location_jp",
    ]


def test_p4_z_dataset_contains_no_duplicate_case_ids():
    dataset = load_dataset(load_contract())
    rows = [
        *dataset["development_failures"],
        *dataset["holdout_failures"],
        *dataset["faithful_controls"],
        *dataset["unsupported_controls"],
    ]
    case_ids = [row["case_id"] for row in rows]
    assert len(case_ids) == len(set(case_ids))
    json.dumps(dataset, ensure_ascii=False)
