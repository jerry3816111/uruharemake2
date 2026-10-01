import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_n_source_bound_japanese_identity_localization_contract_v1.json"
PRECHANGE = ROOT / "analysis" / "p4_n_source_bound_japanese_identity_localization_prechange_2026-09-22.json"


def test_contract_freezes_one_general_identity_localization_variable():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["status"] == "development_contract_frozen_before_implementation"
    assert contract["single_changed_variable"] == (
        "source_provenance_bounded_japanese_identity_localization"
    )
    boundary = contract["surface_boundary"]
    assert boundary["maximum_codepoints"] == 24
    assert boundary["ascii_letters_allowed"] is False
    assert boundary["control_characters_allowed"] is False
    assert boundary["sentence_punctuation_allowed"] is False


def test_contract_contains_positive_and_fail_closed_negative_fixtures():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    positive = contract["positive_development_fixtures"]
    negative = contract["negative_development_fixtures"]
    assert len(positive) == 3
    assert len(negative) == 7
    assert {item["source_language"] for item in negative if "source_language" in item} >= {
        "ja", "en", "zh"
    }
    assert any("\n" in item["value"] for item in negative)
    assert any("。" in item["value"] for item in negative)


def test_prechange_failure_is_not_promoted_to_product_or_general_evidence():
    before = json.loads(PRECHANGE.read_text(encoding="utf-8"))
    assert before["status"] == "fail_before_change"
    assert before["probe"]["required_provenance_present"] is True
    assert before["probe"]["observed_status"] == "unsupported_active_value_localization"
    assert before["causal_localization"]["general_source_bound_identity_rule_present"] is False
    assert before["p4_m_failure_reused_as_success_fixture"] is False
    assert before["real_product_turn_count"] == 0
    assert "not product evidence" in before["claim_boundary"]
