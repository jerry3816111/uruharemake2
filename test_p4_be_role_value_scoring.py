"""Pre-model tests for the P4-BE source-window/semantic-anchor proxy."""
from copy import deepcopy
import json
from pathlib import Path

import p4_be_role_value_scoring as scoring
import uruha_typed_action_compiler_p4 as compiler


ROOT = Path(__file__).resolve().parent
DATASET = json.loads((ROOT / "datasets/p4_be_role_value_prompt_v1.json").read_text(encoding="utf-8"))


def _changed(case, role, text):
    atoms = deepcopy(case["expected_spec"]["evidence_atoms"])
    for atom in atoms:
        if atom["role"] == role:
            atom["text"] = text
            break
    return atoms


def test_p4_be_18_roles_accept_short_and_long_benign_boundaries_before_generation():
    count = 0
    for case in DATASET["positive_cases"]:
        source = case["source"]["text"]
        gold = case["expected_spec"]
        assert scoring.score_packet(case, gold, gold["evidence_atoms"])["role_value_packet_exact"]
        for role, annotation in case["role_annotations"].items():
            window = annotation["allowed_window"]
            assert source.count(window) == 1
            assert annotation["benign_short"] != annotation["benign_long"]
            for field in ("benign_short", "benign_long"):
                value = annotation[field]
                assert value in window
                atoms = _changed(case, role, value)
                assert scoring.score_atoms(case, atoms)["all_accepted"]
            count += 1
    assert count == 18


def test_p4_be_18_source_exact_hard_negatives_can_compile_but_fail_role_score():
    count = 0
    for case in DATASET["positive_cases"]:
        gold = case["expected_spec"]
        for role, annotation in case["role_annotations"].items():
            negative = annotation["hard_negative"]
            assert negative in case["source"]["text"]
            mutated = deepcopy(gold)
            mutated["evidence_atoms"] = _changed(case, role, negative)
            plan, trace = compiler.compile_typed_action_p4_bb(case["source"], mutated)
            assert plan is not None and trace["status"] == "compiled"
            score = scoring.score_packet(case, mutated, mutated["evidence_atoms"])
            assert score["role_value_evidence"] is False
            assert score["role_value_packet_exact"] is False
            assert score["per_role"][role]["accepted"] is False
            count += 1
    assert count == 18


def test_p4_be_rejects_wrong_role_order_translation_whole_source_and_invalid_packet():
    case = DATASET["positive_cases"][2]
    gold = case["expected_spec"]
    swapped = deepcopy(gold["evidence_atoms"])
    swapped[0]["role"], swapped[1]["role"] = swapped[1]["role"], swapped[0]["role"]
    assert not scoring.score_atoms(case, swapped)["all_accepted"]
    translated = _changed(case, "task_object", "会議メモ")
    assert not scoring.score_atoms(case, translated)["all_accepted"]
    whole_source = _changed(case, "task_object", case["source"]["text"])
    assert not scoring.score_atoms(case, whole_source)["all_accepted"]
    raw_good = scoring.score_packet(case, None, gold["evidence_atoms"])
    assert raw_good["raw_role_value_evidence"] is True
    assert raw_good["role_value_evidence"] is False
    assert raw_good["role_value_packet_exact"] is False


def test_p4_be_reports_fragment_boundary_separately_from_role_value_coverage():
    japanese = DATASET["positive_cases"][4]
    bad_japanese = _changed(japanese, "task_object", "の作業画面")
    result = scoring.score_atoms(japanese, bad_japanese)
    assert result["per_role"]["task_object"]["within_window"] is True
    assert result["per_role"]["task_object"]["required_present"] is True
    assert result["per_role"]["task_object"]["boundary_valid"] is False
    assert result["all_accepted"] is True  # bounded anchor coverage, not quote polish

    english = DATASET["positive_cases"][3]
    bad_english = _changed(english, "task_object", "its subject")
    result = scoring.score_atoms(english, bad_english)
    assert result["per_role"]["task_object"]["within_window"] is True
    assert result["per_role"]["task_object"]["required_present"] is True
    assert result["per_role"]["task_object"]["boundary_valid"] is False
    assert result["all_accepted"] is True


def test_p4_be_rejects_in_window_fragments_that_omit_relation_or_completion():
    examples = (
        (DATASET["positive_cases"][0], "request", "小步驟"),
        (DATASET["positive_cases"][1], "rule", "公司名稱"),
        (DATASET["positive_cases"][2], "completion", "then stop"),
        (DATASET["positive_cases"][3], "condition", "the project's name"),
        (DATASET["positive_cases"][4], "limit", "一つだけ"),
        (DATASET["positive_cases"][5], "limit", "今日の日付"),
    )
    for case, role, value in examples:
        observed = scoring.score_atoms(case, _changed(case, role, value))
        assert observed["per_role"][role]["within_window"] is True
        assert observed["per_role"][role]["required_present"] is False
        assert observed["all_accepted"] is False


def test_p4_be_non_span_contract_still_fails_when_a_canonical_slot_changes():
    case = DATASET["positive_cases"][0]
    changed = deepcopy(case["expected_spec"])
    changed["slots"]["unknown_constraint_jp"] = ""
    score = scoring.score_packet(case, changed, changed["evidence_atoms"])
    assert score["role_value_evidence"] is True
    assert score["non_span_exact"] is False
    assert score["role_value_packet_exact"] is False
