import hashlib
import json
from pathlib import Path

import uruha_goal_progress_delivery_m46 as m46


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_bb_typed_action_compiler_v1.json"
DATASET = ROOT / "datasets" / "p4_bb_typed_action_compiler_v1.json"


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load():
    return (
        json.loads(CONTRACT.read_text(encoding="utf-8")),
        json.loads(DATASET.read_text(encoding="utf-8")),
    )


def test_p4_bb_dataset_is_hash_bound_and_frozen_before_implementation():
    contract, dataset = _load()

    assert contract["status"] == "prospectively_frozen_before_implementation"
    assert dataset["status"] == "sealed_before_implementation"
    assert dataset["development_only"] is True
    assert contract["dataset"]["sha256"] == _sha(DATASET)
    assert dataset["reuse_policy"]["post_result_case_or_gate_change_allowed"] is False
    assert dataset["reuse_policy"]["these_cases_may_be_called_holdout"] is False


def test_p4_bb_freezes_all_six_allowed_progress_mechanisms_and_three_languages():
    contract, dataset = _load()
    positives = dataset["positive_cases"]

    assert len(positives) == 6
    assert {row["language"] for row in positives} == {"zh-TW", "en", "ja"}
    assert {row["task_spec"]["template_id"] for row in positives} == set(contract["templates"])
    assert {
        spec["progress_mechanism"] for spec in contract["templates"].values()
    } == m46.ALLOWED_PROGRESS_MECHANISMS


def test_p4_bb_expected_plans_are_source_exact_and_structurally_valid_before_code_exists():
    _contract, dataset = _load()

    for row in dataset["positive_cases"]:
        source = row["source"]
        spec = row["task_spec"]
        plan = row["expected_plan"]
        assert source["kind"] in {"current_user", "linked_previous_user"}
        assert spec["source_id"] == source["id"] == plan["goal_source_id"]
        assert spec["source_span"] == source["text"] == plan["goal_source_span"]
        assert m46.structural_plan_violations(plan, [source]) == []


def test_p4_bb_every_evidence_atom_is_observable_in_the_exact_source():
    contract, dataset = _load()

    for row in dataset["positive_cases"]:
        text = row["source"]["text"]
        spec = row["task_spec"]
        template = contract["templates"][spec["template_id"]]
        atoms = spec["evidence_atoms"]
        assert {atom["role"] for atom in atoms} == set(template["required_evidence_roles"])
        assert all(atom["text"] and atom["text"] in text for atom in atoms)
        assert set(spec["slots"]) == set(template["required_slots"])
        assert spec["safety_class"] == "low_risk_reversible"


def test_p4_bb_controls_cover_identity_provenance_schema_language_safety_and_unknowns():
    _contract, dataset = _load()
    controls = dataset["control_cases"]

    assert len(controls) == 12
    assert len({row["case_id"] for row in controls}) == 12
    assert {row["expected_reason"] for row in controls} == {
        "source_identity_mismatch",
        "source_kind_not_allowed",
        "evidence_atom_not_exact",
        "slot_contract_mismatch",
        "unsupported_template",
        "safety_class_not_allowed",
        "invalid_japanese_slot",
        "evidence_role_contract_mismatch",
        "slot_value_not_allowed",
        "missing_typed_task_spec",
    }
    assert {row["mutation"]["op"] for row in controls} == {"replace", "remove", "add"}


def test_p4_bb_formal_gates_require_exact_outputs_controls_zero_model_and_cost():
    contract, _dataset = _load()
    gates = contract["formal_gates"]

    assert gates["compiled_count"] == 6
    assert gates["exact_expected_plan_count"] == 6
    assert gates["structurally_valid_count"] == 6
    assert gates["exact_source_binding_count"] == 6
    assert gates["mechanism_exact_count"] == 6
    assert gates["natural_japanese_instruction_count"] == 6
    assert gates["deterministic_repeat_match_count"] == 6
    assert gates["control_blocked_count"] == 12
    assert gates["control_expected_reason_count"] == 12
    assert gates["false_plan_on_control_count"] == 0
    assert gates["model_call_count"] == 0
    assert gates["raw_dialogue_trace_count"] == 0
    assert gates["factual_memory_write_count"] == 0
    assert gates["maximum_compile_seconds"] == 0.01


def test_p4_bb_freeze_does_not_authorize_runtime_or_hide_upstream_work():
    contract, _dataset = _load()

    boundary = contract["representation_boundary"]
    failure = contract["failure_policy"]
    assert boundary["not_tested"] == "deriving the typed task spec from raw dialogue"
    assert boundary["unknown_or_unsupported_behavior"] == "fail_closed_without_plan"
    assert boundary["model_may_select_progress_mechanism"] is False
    assert failure["unsupported_template_may_fall_back_to_free_generation"] is False
    assert failure["offline_pass_may_authorize_product_runtime_change"] is False
    assert failure["p4_ba_negative_result_may_be_overwritten"] is False
    assert "Product integration and Safari remain unauthorized" in contract["next_authorization_if_pass"]
    assert not any(path.startswith("uruha_goal_progress_delivery_m46.py") for path in contract["allowed_files_after_freeze"])
