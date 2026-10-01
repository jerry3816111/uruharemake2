import hashlib
import json
from pathlib import Path

import p4_ag_multiturn_ambiguity_outcome_gate as gate


ROOT = Path(__file__).resolve().parent


def test_frozen_contract_binds_dataset_and_immutable_predecessors():
    contract = gate.load_contract()
    dataset_path = ROOT / contract["dataset"]["path"]
    assert hashlib.sha256(dataset_path.read_bytes()).hexdigest() == contract["dataset"]["sha256"]
    for key, hash_key in (
        ("eligibility_module", "eligibility_module_sha256"),
        ("product_entry", "product_entry_sha256"),
    ):
        path = ROOT / contract["predecessor"][key]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == contract["predecessor"][hash_key]


def test_frozen_dataset_contains_support_contradiction_unknown_and_fresh_languages():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)
    sequences = [*dataset["development_sequences"], *dataset["fresh_sequences"]]
    assert len(sequences) == 9
    assert {row["expected_outcome"] for row in sequences} == {"supported", "contradicted", "unknown"}
    assert {row["language"] for row in dataset["fresh_sequences"]} == {"en", "ja"}
    assert sum(row["expected_outcome"] == "supported" for row in sequences) == 3
    assert sum(row["expected_outcome"] == "contradicted" for row in sequences) == 3
    assert sum(row["expected_outcome"] == "unknown" for row in sequences) == 3


def test_contract_forbids_relabeling_unknown_or_changing_released_behavior():
    contract = gate.load_contract()
    boundary = contract["implementation_boundary"]
    assert boundary["existing_feedback_classifier_change_allowed"] is False
    assert boundary["visible_reply_change_allowed"] is False
    assert boundary["unknown_counted_as_success_allowed"] is False
    assert boundary["factual_memory_write_allowed"] is False
    dataset = json.loads((ROOT / contract["dataset"]["path"]).read_text(encoding="utf-8"))
    assert dataset["outcome_contract"]["private_truth_claim_allowed"] is False
