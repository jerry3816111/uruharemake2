#!/usr/bin/env python3
"""Validate the frozen P4-G product surface contract without runtime imports."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_g_preference_acknowledgement_contract_v1.json"


class P4GPreferenceAcknowledgementContractError(RuntimeError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_contract(payload)
    return payload


def validate_contract(contract: dict) -> None:
    if contract.get("schema") != "uruha_p4_g_preference_acknowledgement_contract_v1":
        raise P4GPreferenceAcknowledgementContractError("contract_schema_invalid")
    surfaces = contract.get("authoritative_surfaces") or {}
    if surfaces != {
        "write": "ん、その好みは覚えとく。",
        "correction": "ん、訂正の内容はそのまま覚えとく。",
    }:
        raise P4GPreferenceAcknowledgementContractError("authoritative_surfaces_changed")
    positives = contract.get("positive_cases") or []
    if len(positives) != 6:
        raise P4GPreferenceAcknowledgementContractError("positive_case_count_invalid")
    if {(row.get("language"), row.get("act")) for row in positives} != {
        ("en", "write"),
        ("zh", "write"),
        ("ja", "write"),
        ("en", "correction"),
        ("zh", "correction"),
        ("ja", "correction"),
    }:
        raise P4GPreferenceAcknowledgementContractError("positive_language_act_coverage_invalid")
    if len(contract.get("negative_cases") or []) != 6:
        raise P4GPreferenceAcknowledgementContractError("negative_case_count_invalid")
    generic = contract.get("generic_formal_acknowledgements") or []
    if not generic or any("ん、" in value for value in generic):
        raise P4GPreferenceAcknowledgementContractError("generic_ack_allowlist_invalid")
    invariants = contract.get("invariants") or {}
    expected_invariants = {
        "non_generic_natural_reply_unchanged": True,
        "visible_output_japanese_only": True,
        "model_call_added": False,
        "episode_write_count_changed": False,
        "memory_ranking_changed": False,
        "raw_dialogue_persisted_in_trace": False,
        "p4_f_supersession_or_recall_changed": False,
        "safety_surface_remains_authoritative": True,
    }
    if invariants != expected_invariants:
        raise P4GPreferenceAcknowledgementContractError("invariant_missing")


if __name__ == "__main__":
    print(json.dumps(load_contract(), ensure_ascii=False, indent=2))
