import hashlib
import json
from pathlib import Path

import rightbrain_language_quality as language
import uruha_goal_progress_delivery_m46 as m46
import uruha_typed_action_compiler_p4 as compiler


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_bc_raw_dialogue_typed_spec_v1.json"
DATASET = ROOT / "datasets" / "p4_bc_raw_dialogue_typed_spec_v1.json"
PROMPT = ROOT / "configs" / "p4_bc_raw_dialogue_typed_spec_prompt_v1.txt"
P4_BB_DATASET = ROOT / "datasets" / "p4_bb_typed_action_compiler_v1.json"


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load():
    return (
        json.loads(CONTRACT.read_text(encoding="utf-8")),
        json.loads(DATASET.read_text(encoding="utf-8")),
    )


def test_p4_bc_dataset_prompt_and_downstream_compiler_are_hash_bound_before_calls():
    contract, dataset = _load()

    assert contract["status"] == "prospectively_frozen_before_model_execution"
    assert dataset["status"] == "sealed_before_model_execution"
    assert contract["dataset"]["sha256"] == _sha(DATASET)
    assert contract["prompt"]["sha256"] == _sha(PROMPT)
    assert contract["downstream_compiler"]["sha256"] == _sha(ROOT / contract["downstream_compiler"]["path"])
    assert dataset["reuse_policy"]["same_model_case_may_be_retried"] is False


def test_p4_bc_formal_sources_are_new_and_not_the_exposed_p4_bb_sources():
    _contract, dataset = _load()
    exposed = json.loads(P4_BB_DATASET.read_text(encoding="utf-8"))
    fresh_texts = {row["source"]["text"] for row in dataset["positive_cases"] + dataset["control_cases"]}
    exposed_texts = {row["source"]["text"] for row in exposed["positive_cases"]}

    assert fresh_texts.isdisjoint(exposed_texts)
    assert len(fresh_texts) == 14
    assert dataset["reuse_policy"]["p4_bb_cases_are_exposed_development_only"] is True
    assert dataset["reuse_policy"]["may_be_called_holdout"] is False


def test_p4_bc_positive_targets_cover_all_templates_languages_and_compile_before_generation():
    contract, dataset = _load()
    positives = dataset["positive_cases"]

    assert len(positives) == 6
    assert {row["language"] for row in positives} == {"zh-TW", "en", "ja"}
    assert {row["expected_spec"]["template_id"] for row in positives} == set(compiler.TEMPLATE_CONTRACTS)
    for row in positives:
        source = row["source"]
        spec = row["expected_spec"]
        plan, trace = compiler.compile_typed_action_p4_bb(source, spec)
        assert trace["status"] == "compiled"
        assert plan["progress_mechanism"] == compiler.TEMPLATE_CONTRACTS[spec["template_id"]]["progress_mechanism"]
        assert m46.structural_plan_violations(plan, [source]) == []
        assert language.has_japanese(plan["instruction_jp"])
        assert not language.has_bad_language(plan["instruction_jp"])


def test_p4_bc_positive_expected_evidence_is_exact_and_role_complete():
    _contract, dataset = _load()

    for row in dataset["positive_cases"]:
        source = row["source"]
        spec = row["expected_spec"]
        frozen = compiler.TEMPLATE_CONTRACTS[spec["template_id"]]
        assert spec["source_id"] == source["id"]
        assert spec["source_span"] == source["text"]
        assert [atom["role"] for atom in spec["evidence_atoms"]] == {
            "blank_work_three_headings": ["task_object", "state", "request"],
            "binary_rule_two_piles": ["task_object", "rule", "completion"],
            "extract_one_by_named_rule": ["task_object", "selection_rule", "completion"],
            "verify_one_named_condition": ["task_object", "condition", "limit"],
            "close_one_named_obstacle": ["task_object", "obstacle", "limit"],
            "write_one_atomic_value": ["task_object", "value", "limit"],
        }[spec["template_id"]]
        assert {atom["role"] for atom in spec["evidence_atoms"]} == frozen["evidence_roles"]
        assert all(atom["text"] in source["text"] for atom in spec["evidence_atoms"])


def test_p4_bc_controls_cover_eight_distinct_unavailable_boundaries():
    _contract, dataset = _load()
    controls = dataset["control_cases"]

    assert len(controls) == 8
    assert {row["expected_unavailable_reason"] for row in controls} == set(dataset["reason_vocabulary"])
    assert len(dataset["reason_vocabulary"]) == 8
    assert {row["language"] for row in controls} == {"zh-TW", "en", "ja"}


def test_p4_bc_models_prewarms_one_call_budget_and_fair_constants_are_frozen():
    contract, _dataset = _load()
    constants = contract["controlled_constants"]
    execution = contract["execution"]

    assert contract["models"] == ["qwen3.5:9b", "qwen3.5:4b"]
    assert constants["temperature"] == 0
    assert constants["seed"] == 20260927
    assert constants["same_prompt"] is True
    assert constants["same_dynamic_schema"] is True
    assert constants["same_cases_and_order"] is True
    assert constants["prewarm_models_once_in_fixed_order"] == contract["models"]
    assert constants["prewarm_scored_as_case_latency"] is False
    assert constants["retry_count"] == 0
    assert execution["execute_each_model_case_once"] is True
    assert execution["single_call_latency_target_seconds"] == 20


def test_p4_bc_every_model_must_pass_exact_positive_negative_cost_and_accounting_gates():
    contract, _dataset = _load()
    gates = contract["formal_gates_per_model"]

    assert gates["case_count"] == 14
    assert gates["json_parse_success_count"] == 14
    assert gates["positive_typed_spec_count"] == 6
    assert gates["positive_exact_spec_count"] == 6
    assert gates["positive_template_exact_count"] == 6
    assert gates["positive_evidence_exact_count"] == 6
    assert gates["positive_slots_exact_count"] == 6
    assert gates["positive_downstream_compiled_count"] == 6
    assert gates["positive_downstream_mechanism_exact_count"] == 6
    assert gates["positive_natural_japanese_count"] == 6
    assert gates["control_unavailable_count"] == 8
    assert gates["control_reason_exact_count"] == 8
    assert gates["control_false_spec_count"] == 0
    assert gates["assistant_or_private_source_count"] == 0
    assert gates["token_accounting_complete"] is True
    assert gates["maximum_call_seconds"] == 20


def test_p4_bc_failure_policy_blocks_retuning_runtime_changes_and_overclaim():
    contract, _dataset = _load()
    failure = contract["failure_policy"]
    prompt = PROMPT.read_text(encoding="utf-8")

    assert failure["same_model_case_retry_allowed"] is False
    assert failure["post_result_dataset_prompt_schema_or_gate_change_allowed"] is False
    assert failure["approximate_template_or_reason_may_count_as_exact"] is False
    assert failure["compiler_pass_may_replace_wrong_typed_spec"] is False
    assert failure["failed_model_may_be_hidden_by_other_model"] is False
    assert failure["runtime_integration_before_result_allowed"] is False
    assert "Do not force a near match" in prompt
    assert "not mind reading" in prompt
    assert "not establish open-domain pragmatic understanding" in contract["claim_boundary"]
    assert not any(path in contract["allowed_files_after_freeze"] for path in (
        "uruha_state_changing_candidates_m51.py",
        "uruha_goal_progress_delivery_m46.py",
        "uruha_actionable_help_delivery_m45.py",
    ))
