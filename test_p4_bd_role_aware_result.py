"""Immutable-result checks for the single P4-BD formal run; no model calls."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis/p4_bd_role_aware_evidence_2026-09-29.json"
CONTRACT = ROOT / "configs/p4_bd_role_aware_evidence_v1.json"
DATASET = ROOT / "datasets/p4_bd_role_aware_evidence_v1.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _model(evidence, name):
    return next(item for item in evidence["models"] if item["model"] == name)


def _row(evidence, name, case_id):
    return next(
        item for item in evidence["rows"]
        if item["model"] == name and item["case_id"] == case_id
    )


def test_p4_bd_formal_run_is_single_frozen_failure_without_runtime_selection():
    evidence = _load(RESULT)
    contract = _load(CONTRACT)

    assert evidence["schema"] == "uruha_p4_bd_role_aware_evidence_v1"
    assert evidence["status"] == "fail"
    assert evidence["freeze_sha"] == "26fb89821d7d1b846ff3d83aa4209f8ecd8384e8"
    assert evidence["runner_sha256"] == hashlib.sha256(
        (ROOT / "run_p4_bd_role_aware_evidence.py").read_bytes()
    ).hexdigest()
    assert evidence["contract"]["sha256"] == hashlib.sha256(CONTRACT.read_bytes()).hexdigest()
    assert evidence["dataset_sha256"] == hashlib.sha256(DATASET.read_bytes()).hexdigest()
    assert evidence["annotation_proxy_sha256"] == contract["annotation_proxy_decisions"]["sha256"]
    assert evidence["executed_exactly_once_per_model_case"] is True
    assert evidence["retry_count"] == 0
    assert evidence["selected_model"] is None
    assert evidence["product_runtime_changed"] is False
    assert all(not item["eligible"] for item in evidence["models"])


def test_p4_bd_formal_calls_are_complete_and_cost_accounted_but_not_a_quality_pass():
    evidence = _load(RESULT)
    rows = evidence["rows"]
    calls = [row["call"] for row in rows]

    assert len(rows) == len(calls) == 28
    assert len({call["call_id"] for call in calls}) == 28
    assert len(evidence["prewarm"]) == 2
    assert all(item["completed"] for item in evidence["prewarm"])
    assert all(call["attempted"] and call["completed"] and call["json_parse_success"] for call in calls)
    assert all(call["prompt_tokens"] > 0 and call["completion_tokens"] > 0 for call in calls)
    assert all(item["metrics"]["token_accounting_complete"] for item in evidence["models"])
    assert sum(call["prompt_tokens"] for call in calls) == 25516
    assert sum(call["completion_tokens"] for call in calls) == 6771


def test_p4_bd_both_models_fail_new_role_aware_gate_despite_control_and_latency_pass():
    evidence = _load(RESULT)
    expected = {
        "qwen3.5:9b": (5, 5, 5, 5, 15.05412, 10.12816, 3655),
        "qwen3.5:4b": (5, 4, 2, 4, 9.38962, 6.02785, 3116),
    }
    for name, (typed, non_span, atoms, compiled, maximum, median, completion) in expected.items():
        model = _model(evidence, name)
        metrics = model["metrics"]
        assert metrics["case_count"] == metrics["json_parse_success_count"] == 14
        assert metrics["positive_typed_spec_count"] == typed
        assert metrics["positive_non_span_exact_count"] == non_span
        assert metrics["positive_role_aware_atom_count"] == atoms
        assert metrics["positive_role_aware_evidence_count"] == 0
        assert metrics["positive_role_aware_packet_count"] == 0
        assert metrics["positive_exact_spec_count"] == 0
        assert metrics["positive_evidence_exact_count"] == 0
        assert metrics["positive_downstream_compiled_count"] == compiled
        assert metrics["control_unavailable_count"] == metrics["control_reason_exact_count"] == 8
        assert metrics["control_false_spec_count"] == metrics["assistant_or_private_source_count"] == 0
        assert metrics["maximum_call_seconds"] == maximum < 20
        assert metrics["median_call_seconds"] == median
        assert metrics["prompt_tokens"] == 12758
        assert metrics["completion_tokens"] == completion
        assert "positive_role_aware_evidence_count" in model["failed_gates"]
        assert "positive_non_span_exact_count" in model["failed_gates"]


def test_p4_bd_raw_source_exactness_does_not_hide_wrong_roles_or_invalid_packets():
    evidence = _load(RESULT)
    cases = {case["case_id"]: case for case in _load(DATASET)["positive_cases"]}
    positives = [row for row in evidence["rows"] if row["kind"] == "positive"]
    by_model = {name: [row for row in positives if row["model"] == name]
                for name in ("qwen3.5:9b", "qwen3.5:4b")}
    assert all(len(rows) == 6 for rows in by_model.values())
    assert sum(
        atom["text"] in cases[row["case_id"]]["source"]["text"]
        for row in by_model["qwen3.5:9b"] for atom in row["raw_model_output"]["evidence_atoms"]
    ) == 18
    assert sum(
        atom["text"] in cases[row["case_id"]]["source"]["text"]
        for row in by_model["qwen3.5:4b"] for atom in row["raw_model_output"]["evidence_atoms"]
    ) == 17

    nine_invalid = _row(evidence, "qwen3.5:9b", "p4_bd_ja_remove_001")
    four_invalid = _row(evidence, "qwen3.5:4b", "p4_bd_ja_atomic_001")
    for row in (nine_invalid, four_invalid):
        assert row["normalization"] == {"status": "invalid", "reason": "typed_spec_contract_mismatch"}
        assert row["typed_spec"] is False
        assert row["role_aware_packet_exact"] is False
    four_wrong_role = _row(evidence, "qwen3.5:4b", "p4_bd_ja_remove_001")
    assert four_wrong_role["raw_model_output"]["evidence_atoms"][0] == {
        "role": "task_object", "text": "未使用のタブ"
    }
    assert four_wrong_role["role_aware_per_role"]["task_object"]["accepted"] is False


def test_p4_bd_claim_boundary_remains_development_only():
    evidence = _load(RESULT)
    assert "developer-authored ontology cases" in evidence["claim_boundary"]
    assert "not establish general pragmatic understanding" in evidence["claim_boundary"]
    assert "human equation" in evidence["claim_boundary"]
