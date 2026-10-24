import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_bc_raw_dialogue_typed_spec_evidence_2026-09-27.json"
DATASET = ROOT / "datasets" / "p4_bc_raw_dialogue_typed_spec_v1.json"


def _load():
    return json.loads(RESULT.read_text(encoding="utf-8"))


def _dataset():
    return json.loads(DATASET.read_text(encoding="utf-8"))


def _summary(model):
    return next(row for row in _load()["models"] if row["model"] == model)


def _row(model, case_id):
    return next(
        row for row in _load()["rows"]
        if row["model"] == model and row["case_id"] == case_id
    )


def test_p4_bc_preserves_the_single_no_retry_formal_failure():
    evidence = _load()

    assert evidence["status"] == "fail"
    assert evidence["selected_model"] is None
    assert evidence["executed_exactly_once_per_model_case"] is True
    assert evidence["retry_count"] == 0
    assert evidence["product_runtime_changed"] is False
    assert len(evidence["rows"]) == 28
    assert all(row["eligible"] is False for row in evidence["models"])


def test_p4_bc_all_calls_completed_with_parseable_json_and_complete_tokens():
    rows = _load()["rows"]
    calls = [row["call"] for row in rows]

    assert len(calls) == 28
    assert all(call["attempted"] is True for call in calls)
    assert all(call["completed"] is True for call in calls)
    assert all(call["json_parse_success"] is True for call in calls)
    assert all(call["prompt_tokens"] > 0 for call in calls)
    assert all(call["completion_tokens"] > 0 for call in calls)
    assert all(row["metrics"]["token_accounting_complete"] is True for row in _load()["models"])


def test_p4_bc_9b_kept_templates_slots_and_compilation_but_failed_exact_spans_reason_and_latency():
    summary = _summary("qwen3.5:9b")
    metrics = summary["metrics"]

    assert metrics["positive_typed_spec_count"] == 6
    assert metrics["positive_template_exact_count"] == 6
    assert metrics["positive_slots_exact_count"] == 6
    assert metrics["positive_downstream_compiled_count"] == 6
    assert metrics["positive_downstream_mechanism_exact_count"] == 6
    assert metrics["positive_natural_japanese_count"] == 6
    assert metrics["positive_exact_spec_count"] == 0
    assert metrics["positive_evidence_exact_count"] == 0
    assert metrics["control_unavailable_count"] == 8
    assert metrics["control_reason_exact_count"] == 7
    assert metrics["maximum_call_seconds"] == 21.71181
    assert summary["failed_gates"] == [
        "positive_exact_spec_count",
        "positive_evidence_exact_count",
        "control_reason_exact_count",
        "maximum_call_seconds",
    ]


def test_p4_bc_4b_met_cost_and_controls_but_one_required_slot_was_missing():
    summary = _summary("qwen3.5:4b")
    metrics = summary["metrics"]
    atomic = _row("qwen3.5:4b", "p4_bc_ja_atomic_001")

    assert metrics["maximum_call_seconds"] == 14.39932
    assert metrics["median_call_seconds"] == 9.32895
    assert metrics["control_unavailable_count"] == 8
    assert metrics["control_reason_exact_count"] == 8
    assert metrics["control_false_spec_count"] == 0
    assert metrics["positive_typed_spec_count"] == 5
    assert metrics["positive_downstream_compiled_count"] == 5
    assert atomic["observed_status"] == "typed_spec"
    assert atomic["observed_template_id"] == "write_one_atomic_value"
    assert atomic["normalization"] == {
        "status": "invalid", "reason": "typed_spec_contract_mismatch"
    }
    assert atomic["observed_nonempty_slots"] == {"atomic_object_jp": "今日の日付"}
    assert "unknown_constraint_jp" not in atomic["observed_nonempty_slots"]


def test_p4_bc_observed_evidence_was_role_complete_and_source_exact_but_not_gold_boundary_exact():
    dataset = _dataset()
    positives = {row["case_id"]: row for row in dataset["positive_cases"]}

    for row in [item for item in _load()["rows"] if item["kind"] == "positive"]:
        source = positives[row["case_id"]]["source"]["text"]
        expected_roles = {
            atom["role"] for atom in positives[row["case_id"]]["expected_spec"]["evidence_atoms"]
        }
        observed = row["observed_evidence_atoms"]
        assert {atom["role"] for atom in observed} == expected_roles
        assert all(atom["text"] in source for atom in observed)
        assert row["evidence_exact"] is False


def test_p4_bc_controls_failed_closed_without_false_typed_specs():
    evidence = _load()
    controls = [row for row in evidence["rows"] if row["kind"] == "control"]

    assert len(controls) == 16
    assert all(row["unavailable"] is True for row in controls)
    assert all(row["false_spec"] is False for row in controls)
    mismatch = _row("qwen3.5:9b", "p4_bc_control_ambiguous_no_object_001")
    assert mismatch["expected_unavailable_reason"] == "ambiguous_missing_object"
    assert mismatch["observed_unavailable_reason"] == "unsupported_open_task"


def test_p4_bc_records_real_cost_difference_without_selecting_a_failed_model():
    nine = _summary("qwen3.5:9b")["metrics"]
    four = _summary("qwen3.5:4b")["metrics"]

    assert nine["median_call_seconds"] == 14.93361
    assert four["median_call_seconds"] == 9.32895
    assert nine["prompt_tokens"] == four["prompt_tokens"] == 12652
    assert nine["completion_tokens"] == 3551
    assert four["completion_tokens"] == 3521
    assert _load()["selected_model"] is None


def test_p4_bc_claim_boundary_does_not_overstate_bounded_proxy_evidence():
    evidence = _load()

    assert "bounded raw-source classification/extraction" in evidence["claim_boundary"]
    assert "not establish open-domain pragmatic understanding" in evidence["claim_boundary"]
    assert "human equation" in evidence["claim_boundary"]
