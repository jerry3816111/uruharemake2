"""P4-BD scorer rejects semantic mutants the P4-BB compiler itself accepts."""
from copy import deepcopy
import json
from pathlib import Path

import p4_bd_role_aware_scoring as scoring


DATASET = json.loads(
    (Path(__file__).resolve().parent / "datasets/p4_bd_role_aware_evidence_v1.json")
    .read_text(encoding="utf-8")
)


def test_gold_and_preaccepted_alternates_pass_but_strict_single_gold_stays_distinct():
    changed_boundaries = 0
    for case in DATASET["positive_cases"]:
        gold = case["expected_spec"]
        assert scoring.score_packet(case, gold, gold["evidence_atoms"])["role_aware_packet_exact"]
        for index, atom in enumerate(gold["evidence_atoms"]):
            for alternative in case["role_annotations"][atom["role"]]["accepted_exact_spans"]:
                variant = deepcopy(gold)
                variant["evidence_atoms"][index]["text"] = alternative
                result = scoring.score_packet(case, variant, variant["evidence_atoms"])
                assert result["role_aware_packet_exact"]
                if alternative != atom["text"]:
                    assert variant != gold
                    changed_boundaries += 1
    assert changed_boundaries == 8


def test_hard_negative_wrong_role_or_scope_rejected_even_when_source_exact():
    rejected = 0
    for case in DATASET["positive_cases"]:
        gold = case["expected_spec"]
        for index, atom in enumerate(gold["evidence_atoms"]):
            variant = deepcopy(gold)
            variant["evidence_atoms"][index]["text"] = case["role_annotations"][atom["role"]]["hard_negative"]
            result = scoring.score_packet(case, variant, variant["evidence_atoms"])
            assert result["raw_accepted_atom_count"] == 2
            assert result["accepted_atom_count"] == 2
            assert result["non_span_exact"]
            assert not result["role_aware_packet_exact"]
            rejected += 1
    assert rejected == 18


def test_arbitrary_substring_translation_role_swap_and_extra_fields_never_pass():
    case = DATASET["positive_cases"][0]
    gold = case["expected_spec"]
    arbitrary = deepcopy(gold)
    arbitrary["evidence_atoms"][2]["text"] = "小步驟"
    assert not scoring.score_packet(case, arbitrary, arbitrary["evidence_atoms"])["role_aware_packet_exact"]
    translated = deepcopy(gold)
    translated["evidence_atoms"][0]["text"] = "スライド"
    assert not scoring.score_packet(case, translated, translated["evidence_atoms"])["role_aware_packet_exact"]
    swapped = deepcopy(gold)
    swapped["evidence_atoms"][0]["role"], swapped["evidence_atoms"][1]["role"] = (
        swapped["evidence_atoms"][1]["role"], swapped["evidence_atoms"][0]["role"]
    )
    assert not scoring.score_packet(case, swapped, swapped["evidence_atoms"])["role_aware_packet_exact"]
    extra = deepcopy(gold)
    extra["evidence_atoms"][0]["source_kind"] = "assistant"
    assert not scoring.score_packet(case, extra, extra["evidence_atoms"])["role_aware_packet_exact"]


def test_invalid_packet_cannot_become_eligible_through_good_raw_atoms():
    case = DATASET["positive_cases"][0]
    gold = case["expected_spec"]
    result = scoring.score_packet(case, None, gold["evidence_atoms"])
    assert result["raw_role_aware_evidence"] is True
    assert result["role_aware_evidence"] is False
    assert result["role_aware_packet_exact"] is False


def test_non_span_changes_remain_failures_even_with_accepted_evidence():
    case = DATASET["positive_cases"][0]
    gold = case["expected_spec"]
    for mutation in (
        ("source_id", "current:999"),
        ("template_id", "binary_rule_two_piles"),
        ("slots", {"work_object_jp": "発表資料"}),
        ("safety_class", "private_inference"),
    ):
        variant = deepcopy(gold)
        variant[mutation[0]] = mutation[1]
        result = scoring.score_packet(case, variant, variant["evidence_atoms"])
        assert result["role_aware_evidence"] is True
        assert result["non_span_exact"] is False
        assert result["role_aware_packet_exact"] is False
