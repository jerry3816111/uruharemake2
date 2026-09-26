from copy import deepcopy
import json
from pathlib import Path

import pytest

import rightbrain_language_quality as language
import uruha_goal_progress_delivery_m46 as m46
import uruha_typed_action_compiler_p4 as compiler


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "p4_bb_typed_action_compiler_v1.json"
EVIDENCE = ROOT / "analysis" / "p4_bb_typed_action_compiler_evidence_2026-09-27.json"


def _load():
    return json.loads(DATASET.read_text(encoding="utf-8"))


def _mutate(case, mutation):
    row = deepcopy(case)
    parts = mutation["path"].split(".")
    parent = row
    for part in parts[:-1]:
        parent = parent[int(part)] if isinstance(parent, list) else parent[part]
    leaf = parts[-1]
    if mutation["op"] == "remove":
        if isinstance(parent, list):
            parent.pop(int(leaf))
        else:
            parent.pop(leaf)
    else:
        if isinstance(parent, list):
            parent[int(leaf)] = mutation["value"]
        else:
            parent[leaf] = mutation["value"]
    return row


@pytest.mark.parametrize("case", _load()["positive_cases"], ids=lambda row: row["case_id"])
def test_p4_bb_compiles_each_frozen_positive_to_the_exact_expected_m46_plan(case):
    plan, trace = compiler.compile_typed_action_p4_bb(case["source"], case["task_spec"])

    assert plan == case["expected_plan"]
    assert trace["status"] == "compiled"
    assert trace["reason"] == "typed_template_compiled"
    assert trace["progress_mechanism"] == case["expected_plan"]["progress_mechanism"]
    assert m46.structural_plan_violations(plan, [case["source"]]) == []
    assert trace["model_calls"] == 0
    assert trace["raw_dialogue_persisted"] is False
    assert trace["factual_memory_write_count"] == 0


@pytest.mark.parametrize("case", _load()["positive_cases"], ids=lambda row: row["case_id"])
def test_p4_bb_output_is_deterministic_natural_japanese_and_source_exact(case):
    first_plan, first_trace = compiler.compile_typed_action_p4_bb(case["source"], case["task_spec"])
    second_plan, second_trace = compiler.compile_typed_action_p4_bb(case["source"], case["task_spec"])

    assert first_plan == second_plan
    assert first_trace["plan_digest"] == second_trace["plan_digest"]
    assert first_plan["goal_source_id"] == case["source"]["id"]
    assert first_plan["goal_source_span"] == case["source"]["text"]
    instruction = first_plan["instruction_jp"]
    assert language.has_japanese(instruction)
    assert not language.has_bad_language(instruction)
    assert first_trace["compile_seconds"] <= 0.01
    assert second_trace["compile_seconds"] <= 0.01


@pytest.mark.parametrize("control", _load()["control_cases"], ids=lambda row: row["case_id"])
def test_p4_bb_blocks_every_frozen_control_with_the_expected_reason(control):
    positives = {row["case_id"]: row for row in _load()["positive_cases"]}
    mutated = _mutate(positives[control["base_case_id"]], control["mutation"])
    plan, trace = compiler.compile_typed_action_p4_bb(
        mutated.get("source"), mutated.get("task_spec")
    )

    assert plan is None
    assert trace["status"] == "blocked"
    assert trace["reason"] == control["expected_reason"]
    assert trace["model_calls"] == 0
    assert trace["raw_dialogue_persisted"] is False
    assert trace["factual_memory_write_count"] == 0


def test_p4_bb_template_contract_matches_the_prospective_freeze():
    contract = json.loads(
        (ROOT / "configs" / "p4_bb_typed_action_compiler_v1.json").read_text(encoding="utf-8")
    )

    observed = {
        key: {
            "progress_mechanism": value["progress_mechanism"],
            "required_evidence_roles": sorted(value["evidence_roles"]),
            "required_slots": sorted(value["slots"]),
        }
        for key, value in compiler.TEMPLATE_CONTRACTS.items()
    }
    frozen = {
        key: {
            "progress_mechanism": value["progress_mechanism"],
            "required_evidence_roles": sorted(value["required_evidence_roles"]),
            "required_slots": sorted(value["required_slots"]),
        }
        for key, value in contract["templates"].items()
    }
    assert observed == frozen
    assert set(compiler._COMPILERS) == set(frozen)
    assert set(value["progress_mechanism"] for value in frozen.values()) == m46.ALLOWED_PROGRESS_MECHANISMS


def test_p4_bb_trace_keeps_raw_source_out_of_the_audit_payload():
    case = _load()["positive_cases"][0]
    _plan, trace = compiler.compile_typed_action_p4_bb(case["source"], case["task_spec"])
    serialized = json.dumps(trace, ensure_ascii=False, sort_keys=True)

    assert case["source"]["text"] not in serialized
    assert all(atom["text"] not in serialized for atom in case["task_spec"]["evidence_atoms"])
    assert trace["source"]["digest"]
    assert "upstream understanding" in trace["claim_boundary"]


def test_p4_bb_formal_evidence_preserves_the_bounded_pass_and_no_runtime_change():
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    metrics = evidence["metrics"]

    assert evidence["status"] == "pass"
    assert evidence["freeze_commit"] == "a4dd116"
    assert metrics["compiled_count"] == 6
    assert metrics["exact_expected_plan_count"] == 6
    assert metrics["structurally_valid_count"] == 6
    assert metrics["exact_source_binding_count"] == 6
    assert metrics["mechanism_exact_count"] == 6
    assert metrics["natural_japanese_instruction_count"] == 6
    assert metrics["deterministic_repeat_match_count"] == 6
    assert metrics["control_blocked_count"] == 12
    assert metrics["control_expected_reason_count"] == 12
    assert metrics["false_plan_on_control_count"] == 0
    assert metrics["model_call_count"] == 0
    assert metrics["raw_dialogue_trace_count"] == 0
    assert metrics["factual_memory_write_count"] == 0
    assert metrics["maximum_compile_seconds"] <= 0.01
    assert evidence["product_runtime_changed"] is False


def test_p4_bb_formal_evidence_does_not_claim_raw_dialogue_understanding():
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    assert "correct authorized typed task spec already exists" in evidence["analysis"]
    assert "new raw-dialogue cases" in evidence["next_design_implication"]
    assert "Do not integrate P4-BB into product runtime" in evidence["next_design_implication"]
