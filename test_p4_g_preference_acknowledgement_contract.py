import json
from pathlib import Path

import pytest

import p4_g_preference_acknowledgement_contract as contract_module


ROOT = Path(__file__).resolve().parent


def test_contract_freezes_multilingual_positive_and_negative_scope():
    contract = contract_module.load_contract()
    assert len(contract["positive_cases"]) == 6
    assert len(contract["negative_cases"]) == 6
    assert {(row["language"], row["act"]) for row in contract["positive_cases"]} == {
        ("en", "write"),
        ("zh", "write"),
        ("ja", "write"),
        ("en", "correction"),
        ("zh", "correction"),
        ("ja", "correction"),
    }


def test_contract_freezes_exact_authoritative_surfaces_and_invariants():
    contract = contract_module.load_contract()
    assert contract["authoritative_surfaces"] == {
        "write": "ん、その好みは覚えとく。",
        "correction": "ん、訂正の内容はそのまま覚えとく。",
    }
    assert contract["invariants"] == {
        "non_generic_natural_reply_unchanged": True,
        "visible_output_japanese_only": True,
        "model_call_added": False,
        "episode_write_count_changed": False,
        "memory_ranking_changed": False,
        "raw_dialogue_persisted_in_trace": False,
        "p4_f_supersession_or_recall_changed": False,
        "safety_surface_remains_authoritative": True,
    }
    assert "understanding result" in contract["claim_boundary"]


def test_contract_rejects_surface_or_case_drift():
    contract = contract_module.load_contract()
    contract["authoritative_surfaces"]["write"] = "了解しました。"
    with pytest.raises(contract_module.P4GPreferenceAcknowledgementContractError):
        contract_module.validate_contract(contract)

    contract = json.loads(contract_module.CONTRACT.read_text(encoding="utf-8"))
    contract["positive_cases"].pop()
    with pytest.raises(contract_module.P4GPreferenceAcknowledgementContractError):
        contract_module.validate_contract(contract)
