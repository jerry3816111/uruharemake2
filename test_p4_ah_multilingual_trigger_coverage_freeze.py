import hashlib
from pathlib import Path

import p4_ah_multilingual_trigger_coverage_gate as gate


ROOT = Path(__file__).resolve().parent


def test_frozen_contract_binds_dataset_and_predecessors():
    contract = gate.load_contract()
    dataset_path = ROOT / contract["dataset"]["path"]
    assert hashlib.sha256(dataset_path.read_bytes()).hexdigest() == contract["dataset"]["sha256"]
    for key, hash_key in (
        ("adaptive_module", "adaptive_module_sha256"),
        ("outcome_binding_module", "outcome_binding_module_sha256"),
        ("product_entry", "product_entry_sha256"),
    ):
        path = ROOT / contract["predecessor"][key]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == contract["predecessor"][hash_key]


def test_frozen_dataset_has_multilingual_positive_and_near_control_partitions():
    dataset = gate.load_dataset(gate.load_contract())
    assert len(dataset["development_cases"]) == 2
    assert len(dataset["fresh_positive_cases"]) == 9
    assert len(dataset["fresh_control_cases"]) == 12
    assert {row["language"] for row in dataset["fresh_positive_cases"]} == {"zh", "en", "ja"}
    assert {row["language"] for row in dataset["fresh_control_cases"]} == {"zh", "en", "ja"}
    assert all(row["expected_predicate"] is None for row in dataset["fresh_control_cases"])


def test_contract_forbids_full_sentence_patch_and_downstream_changes():
    contract = gate.load_contract()
    boundary = contract["implementation_boundary"]
    assert boundary["full_case_string_patch_allowed"] is False
    assert boundary["outcome_binding_change_allowed"] is False
    assert boundary["p4_af_authority_change_allowed"] is False
    assert boundary["visible_reply_change_allowed"] is False
