"""P4-BE prospective freeze tests; never calls a model or product runtime."""
import hashlib
import json
from pathlib import Path

import p4_be_role_value_scoring as scoring
import rightbrain_language_quality as language
import uruha_typed_action_compiler_p4 as compiler


ROOT = Path(__file__).resolve().parent
CONTRACT = json.loads((ROOT / "configs/p4_be_role_value_prompt_v1.json").read_text(encoding="utf-8"))
DATASET = json.loads((ROOT / CONTRACT["dataset"]["path"]).read_text(encoding="utf-8"))


def test_p4_be_every_operational_input_is_hash_bound_and_prompt_is_the_only_producer_change():
    for label in (
        "dataset", "baseline_prompt", "intervention_prompt", "role_value_scorer",
        "downstream_compiler", "read_only_p4_bc_runner",
    ):
        record = CONTRACT[label]
        assert hashlib.sha256((ROOT / record["path"]).read_bytes()).hexdigest() == record["sha256"]
    assert CONTRACT["status"] == "prospectively_frozen_before_model_execution"
    assert DATASET["status"] == "sealed_before_model_execution"
    assert DATASET["development_only"] is True
    assert DATASET["reuse_policy"]["may_be_called_holdout"] is False

    old = (ROOT / CONTRACT["baseline_prompt"]["path"]).read_text(encoding="utf-8")
    new = (ROOT / CONTRACT["intervention_prompt"]["path"]).read_text(encoding="utf-8")
    old_line = next(line for line in old.splitlines() if line.startswith("- evidence_atoms"))
    new_line = next(line for line in new.splitlines() if line.startswith("- evidence_atoms"))
    role_line = next(line for line in new.splitlines() if line.startswith("- Interpret the roles"))
    assert new.replace(new_line + "\n" + role_line + "\n", old_line + "\n") == old
    assert "whole email or body" not in new
    assert "first reply step" not in new
    assert all(case["source"]["text"] not in new for case in DATASET["positive_cases"])


def test_p4_be_new_same_case_pairing_is_six_templates_three_languages_and_eight_reasons():
    positives = DATASET["positive_cases"]
    controls = DATASET["control_cases"]
    assert len(positives) == 6
    assert len(controls) == 8
    assert {case["language"] for case in positives} == {"zh-TW", "en", "ja"}
    assert {lang: sum(case["language"] == lang for case in positives) for lang in ("zh-TW", "en", "ja")} == {
        "zh-TW": 2, "en": 2, "ja": 2,
    }
    assert {case["expected_spec"]["template_id"] for case in positives} == set(compiler.TEMPLATE_CONTRACTS)
    assert {case["expected_unavailable_reason"] for case in controls} == set(DATASET["reason_vocabulary"])
    assert len({case["source"]["id"] for case in positives + controls}) == 14
    assert len({case["source"]["text"] for case in positives + controls}) == 14
    assert all(case["source"]["kind"] == "current_user" for case in positives + controls)
    old_source_texts = set()
    for filename in (
        "p4_bb_typed_action_compiler_v1.json",
        "p4_bc_raw_dialogue_typed_spec_v1.json",
        "p4_bd_role_aware_evidence_v1.json",
    ):
        old = json.loads((ROOT / "datasets" / filename).read_text(encoding="utf-8"))
        old_source_texts.update(case["source"]["text"] for case in old["positive_cases"])
        old_source_texts.update(case["source"]["text"] for case in old.get("control_cases", []) if "source" in case)
    assert {case["source"]["text"] for case in positives + controls}.isdisjoint(old_source_texts)
    assert "specific risk" in DATASET["reason_adjudication_priority"]


def test_p4_be_gold_compiles_and_18_role_windows_reject_predeclared_hard_negatives():
    seen_roles = 0
    for case in DATASET["positive_cases"]:
        source = case["source"]
        gold = case["expected_spec"]
        assert gold["source_id"] == source["id"]
        assert gold["source_span"] == source["text"]
        assert [atom["role"] for atom in gold["evidence_atoms"]] == {
            "blank_work_three_headings": ["task_object", "state", "request"],
            "binary_rule_two_piles": ["task_object", "rule", "completion"],
            "extract_one_by_named_rule": ["task_object", "selection_rule", "completion"],
            "verify_one_named_condition": ["task_object", "condition", "limit"],
            "close_one_named_obstacle": ["task_object", "obstacle", "limit"],
            "write_one_atomic_value": ["task_object", "value", "limit"],
        }[gold["template_id"]]
        assert set(atom["role"] for atom in gold["evidence_atoms"]) == compiler.TEMPLATE_CONTRACTS[
            gold["template_id"]
        ]["evidence_roles"]
        assert len(case["role_annotations"]) == 3
        score = scoring.score_packet(case, gold, gold["evidence_atoms"])
        assert score["role_value_packet_exact"] is True
        plan, trace = compiler.compile_typed_action_p4_bb(source, gold)
        assert plan is not None and trace["status"] == "compiled"
        assert language.has_japanese(plan["instruction_jp"])
        assert not language.has_bad_language(plan["instruction_jp"])
        for role, annotation in case["role_annotations"].items():
            window = annotation["allowed_window"]
            assert source["text"].count(window) == 1
            assert window.count(annotation["benign_short"]) == 1
            assert window.count(annotation["benign_long"]) == 1
            assert annotation["hard_negative"] in source["text"]
            assert annotation["forbidden_anchors"]  # metadata, not independent tested guard
            assert len(annotation["required_anchors"]) >= 1
            seen_roles += 1
    assert seen_roles == CONTRACT["role_value_scoring"]["per_role_hard_negative_mutants_must_fail"] == 18


def test_p4_be_model_cost_and_no_retry_gates_are_prospectively_bounded():
    constants = CONTRACT["controlled_constants"]
    execution = CONTRACT["execution"]
    gates = CONTRACT["formal_gates_for_intervention"]
    paired = CONTRACT["paired_advantage_gates"]
    bc = json.loads((ROOT / "configs/p4_bc_raw_dialogue_typed_spec_v1.json").read_text(encoding="utf-8"))
    assert CONTRACT["model"] == "qwen3.5:9b"
    assert CONTRACT["arms"] == ["bc_frozen_prompt", "be_role_value_prompt"]
    assert CONTRACT["output_contract"] == bc["output_contract"]
    assert (constants["temperature"], constants["seed"], constants["num_ctx"], constants["num_predict"]) == (
        0, 20260927, 4096, 480,
    )
    assert constants["retry_count"] == 0
    assert execution["max_scored_calls"] == 28
    assert execution["single_call_latency_target_seconds"] == 20
    assert (gates["positive_role_value_packet_count"], gates["positive_full_accept_count"]) == (6, 6)
    assert gates["positive_accepted_atom_count"] == 18
    assert gates["control_unavailable_count"] == gates["control_reason_exact_count"] == 8
    assert gates["control_false_spec_count"] == gates["assistant_or_private_source_count"] == 0
    assert gates["maximum_call_seconds"] == 20
    assert paired["be_only_full_accept_minimum"] == 1
    assert paired["bc_only_full_accept_maximum"] == 0
    assert paired["be_only_raw_role_value_evidence_with_both_source_identities_valid_minimum"] == 1
    assert CONTRACT["failure_policy"]["if_intervention_fails_next_state"] == "REVIEW_REQUIRED"
