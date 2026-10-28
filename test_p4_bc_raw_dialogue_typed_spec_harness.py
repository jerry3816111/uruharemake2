from copy import deepcopy

import run_p4_bc_raw_dialogue_typed_spec as runner


CONTRACT = {
    "formal_gates_per_model": {
        "case_count": 2,
        "json_parse_success_count": 2,
        "positive_typed_spec_count": 1,
        "positive_exact_spec_count": 1,
        "positive_template_exact_count": 1,
        "positive_evidence_exact_count": 1,
        "positive_slots_exact_count": 1,
        "positive_downstream_compiled_count": 1,
        "positive_downstream_mechanism_exact_count": 1,
        "positive_natural_japanese_count": 1,
        "control_unavailable_count": 1,
        "control_reason_exact_count": 1,
        "control_false_spec_count": 0,
        "assistant_or_private_source_count": 0,
        "token_accounting_complete": True,
        "maximum_call_seconds": 20,
    }
}


def _call(seconds=2):
    return {
        "completed": True,
        "json_parse_success": True,
        "wall_seconds": seconds,
        "prompt_tokens": 10,
        "completion_tokens": 5,
    }


def _positive(model="m"):
    return {
        "kind": "positive", "model": model, "call": _call(),
        "typed_spec": True, "exact_spec": True, "template_exact": True,
        "evidence_exact": True, "slots_exact": True,
        "downstream_compiled": True, "downstream_mechanism_exact": True,
        "natural_japanese": True, "assistant_or_private_source": False,
    }


def _control(model="m"):
    return {
        "kind": "control", "model": model, "call": _call(),
        "unavailable": True, "reason_exact": True, "false_spec": False,
        "assistant_or_private_source": False,
    }


def test_output_schema_binds_source_and_requires_every_wide_slot():
    source = {"id": "current:1", "text": "x"}
    contract = {"output_contract": {
        "status": ["typed_spec", "unavailable"],
        "template_id": [*runner.compiler.TEMPLATE_CONTRACTS, "unavailable"],
        "safety_class": ["low_risk_reversible", "unavailable"],
    }}
    dataset = {"reason_vocabulary": ["no_action_request"]}
    schema = runner.output_schema(source, contract, dataset)

    assert schema["properties"]["source_id"]["enum"] == ["current:1"]
    assert schema["properties"]["source_span"]["enum"] == ["x"]
    assert set(schema["properties"]["slots"]["required"]) == set(runner.SLOT_KEYS)
    assert schema["additionalProperties"] is False


def test_normalize_output_strips_unused_slots_only_for_a_valid_typed_spec():
    source = {"id": "current:1", "text": "source"}
    parsed = {
        "status": "typed_spec", "source_id": "current:1", "source_span": "source",
        "template_id": "write_one_atomic_value", "safety_class": "low_risk_reversible",
        "evidence_atoms": [
            {"role": "task_object", "text": "s"},
            {"role": "value", "text": "o"},
            {"role": "limit", "text": "u"},
        ],
        "slots": {key: "" for key in runner.SLOT_KEYS},
        "unavailable_reason": "none",
    }
    parsed["slots"].update(atomic_object_jp="今日の日付", unknown_constraint_jp="指定の日付形式は不明")

    spec, trace = runner.normalize_output(parsed, source)

    assert trace["status"] == "typed_spec"
    assert set(spec["slots"]) == {"atomic_object_jp", "unknown_constraint_jp"}
    assert spec["template_id"] == "write_one_atomic_value"


def test_normalize_output_requires_empty_payload_for_unavailable():
    source = {"id": "current:1", "text": "source"}
    parsed = {
        "status": "unavailable", "source_id": "current:1", "source_span": "source",
        "template_id": "unavailable", "safety_class": "unavailable",
        "evidence_atoms": [], "slots": {key: "" for key in runner.SLOT_KEYS},
        "unavailable_reason": "no_action_request",
    }
    spec, trace = runner.normalize_output(parsed, source)
    assert spec is None
    assert trace == {
        "status": "unavailable", "reason": "no_action_request",
        "unavailable_contract_valid": True,
    }

    broken = deepcopy(parsed)
    broken["slots"]["atomic_object_jp"] = "今日の日付"
    _spec, broken_trace = runner.normalize_output(broken, source)
    assert broken_trace["status"] == "invalid"


def test_summary_requires_every_positive_negative_cost_and_accounting_gate():
    summary = runner.summarize_model("m", [_positive(), _control()], CONTRACT)

    assert summary["eligible"] is True
    assert summary["failed_gates"] == []
    assert summary["metrics"]["maximum_call_seconds"] == 2
    assert summary["metrics"]["token_accounting_complete"] is True


def test_summary_preserves_timeout_false_spec_and_inexact_spec_as_failures():
    positive = _positive()
    positive["exact_spec"] = False
    positive["call"] = {"completed": False, "json_parse_success": False, "wall_seconds": 30}
    control = _control()
    control["false_spec"] = True
    rows = [positive, control]

    summary = runner.summarize_model("m", rows, CONTRACT)

    assert summary["eligible"] is False
    assert "json_parse_success_count" in summary["failed_gates"]
    assert "positive_exact_spec_count" in summary["failed_gates"]
    assert "control_false_spec_count" in summary["failed_gates"]
    assert "token_accounting_complete" in summary["failed_gates"]


def test_selection_uses_only_eligible_models_then_latency_and_tokens():
    summaries = [
        {"model": "slow", "eligible": True, "metrics": {"median_call_seconds": 5, "completion_tokens": 10}},
        {"model": "fast", "eligible": True, "metrics": {"median_call_seconds": 3, "completion_tokens": 20}},
        {"model": "failed", "eligible": False, "metrics": {"median_call_seconds": 1, "completion_tokens": 1}},
    ]
    assert runner.select_model(summaries) == "fast"
    assert runner.select_model([summaries[-1]]) is None
