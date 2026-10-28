"""Offline harness tests; fakes the model transport and never starts a server."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

import run_p4_bd_role_aware_evidence as runner


ROOT = Path(__file__).resolve().parent
CONTRACT = json.loads((ROOT / "configs/p4_bd_role_aware_evidence_v1.json").read_text(encoding="utf-8"))
DATASET = json.loads((ROOT / "datasets/p4_bd_role_aware_evidence_v1.json").read_text(encoding="utf-8"))
BY_SOURCE = {row["source"]["id"]: row for row in DATASET["positive_cases"] + DATASET["control_cases"]}


def _fake_call(*, model, prompt, source, schema, contract, call_id):
    case = BY_SOURCE[source["id"]]
    slots = {key: "" for key in runner.bc.SLOT_KEYS}
    if "expected_spec" in case:
        gold = case["expected_spec"]
        slots.update(gold["slots"])
        atoms = deepcopy(gold["evidence_atoms"])
        if case["case_id"] == "p4_bd_zh_scaffold_001":
            atoms[1]["text"] = "目前整份空白"  # frozen equivalent, not strict gold
        parsed = {
            "status": "typed_spec", "source_id": source["id"], "source_span": source["text"],
            "template_id": gold["template_id"], "safety_class": "low_risk_reversible",
            "evidence_atoms": atoms, "slots": slots, "unavailable_reason": "none",
        }
    else:
        parsed = {
            "status": "unavailable", "source_id": source["id"], "source_span": source["text"],
            "template_id": "unavailable", "safety_class": "unavailable",
            "evidence_atoms": [], "slots": slots,
            "unavailable_reason": case["expected_unavailable_reason"],
        }
    return {
        "call_id": call_id, "model": model, "attempted": True, "completed": True,
        "json_parse_success": True, "wall_seconds": 2,
        "prompt_tokens": 100, "completion_tokens": 40,
        "parsed": parsed,
    }


def _fake_prewarm(model, keep_alive):
    return {"model": model, "attempted": True, "completed": True, "wall_seconds": 1}


def _fake_preflight(contract_path, output_path):
    return CONTRACT, DATASET, "frozen-test-sha"


def test_p4_bd_runner_reports_strict_and_role_aware_without_weakening_other_gates(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "preflight", _fake_preflight)
    monkeypatch.setattr(runner.bc, "prewarm_model", _fake_prewarm)
    monkeypatch.setattr(runner.bc, "model_json_call", _fake_call)
    output = tmp_path / "evidence.json"

    evidence = runner.run(output_path=output)

    assert evidence["status"] == "pass"
    assert evidence["selected_model"] == "qwen3.5:9b"  # equal fake cost: frozen order
    assert len(evidence["rows"]) == 28
    assert evidence["executed_exactly_once_per_model_case"] is True
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == "pass"
    for model in evidence["models"]:
        metrics = model["metrics"]
        assert model["eligible"] is True
        assert metrics["positive_exact_spec_count"] == 5
        assert metrics["positive_evidence_exact_count"] == 5
        assert metrics["positive_role_aware_evidence_count"] == 6
        assert metrics["positive_role_aware_packet_count"] == 6
        assert metrics["positive_non_span_exact_count"] == 6
        assert metrics["positive_downstream_compiled_count"] == 6
        assert metrics["control_reason_exact_count"] == 8
        assert metrics["maximum_call_seconds"] == 2
    with pytest.raises(FileExistsError):
        runner.run(output_path=output)


def test_p4_bd_prewarm_failure_stops_before_scored_calls_and_preserves_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "preflight", _fake_preflight)
    monkeypatch.setattr(
        runner.bc, "prewarm_model",
        lambda model, keep_alive: {"model": model, "attempted": True, "completed": False},
    )
    monkeypatch.setattr(
        runner.bc, "model_json_call",
        lambda **kwargs: pytest.fail("scored model call after failed prewarm"),
    )
    output = tmp_path / "prewarm_fail.json"

    evidence = runner.run(output_path=output)

    assert evidence["status"] == "prewarm_failed_no_scored_calls"
    assert evidence["rows"] == []
    assert len(evidence["prewarm"]) == 1
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == evidence["status"]


def test_p4_bd_summary_preserves_other_failed_gates_even_when_role_aware_passes():
    positive = {
        "kind": "positive", "model": "m", "call": {"completed": True, "json_parse_success": True, "wall_seconds": 21, "prompt_tokens": 1, "completion_tokens": 1},
        "typed_spec": True, "non_span_exact": True, "exact_spec": False,
        "template_exact": True, "evidence_exact": False,
        "role_aware_evidence": True, "role_aware_packet_exact": True,
        "role_aware_accepted_atom_count": 3, "raw_role_aware_evidence": True,
        "slots_exact": True, "downstream_compiled": True,
        "downstream_mechanism_exact": True, "natural_japanese": True,
        "assistant_or_private_source": False,
    }
    control = {
        "kind": "control", "model": "m", "call": {"completed": True, "json_parse_success": True, "wall_seconds": 2, "prompt_tokens": 1, "completion_tokens": 1},
        "unavailable": True, "reason_exact": False, "false_spec": False,
        "assistant_or_private_source": False,
    }
    small = deepcopy(CONTRACT)
    small["formal_gates_per_model"].update(
        case_count=2, json_parse_success_count=2,
        positive_typed_spec_count=1, positive_non_span_exact_count=1,
        positive_template_exact_count=1, positive_role_aware_evidence_count=1,
        positive_role_aware_packet_count=1, positive_slots_exact_count=1,
        positive_downstream_compiled_count=1, positive_downstream_mechanism_exact_count=1,
        positive_natural_japanese_count=1, control_unavailable_count=1,
        control_reason_exact_count=1,
    )
    summary = runner.summarize_model("m", [positive, control], small)
    assert summary["eligible"] is False
    assert summary["failed_gates"] == ["control_reason_exact_count", "maximum_call_seconds"]
    assert summary["metrics"]["positive_exact_spec_count"] == 0


def test_formal_preflight_rejects_alternate_output_before_any_model_request(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "_get_json", lambda url: pytest.fail("network request before fixed-path check"))
    with pytest.raises(RuntimeError, match="single frozen output path"):
        runner.preflight(runner.DEFAULT_CONTRACT, tmp_path / "alternate.json")


def test_source_identity_violation_is_not_hardcoded_false():
    source = {"id": "current:1", "kind": "current_user", "text": "one source"}
    assert runner._source_violation({"source_id": "current:1", "source_span": "one source"}, source) is False
    assert runner._source_violation({"source_id": "current:999", "source_span": "one source"}, source) is True
    assert runner._source_violation({"source_id": "current:1", "source_span": "altered"}, source) is True
    assert runner._source_violation(None, {**source, "kind": "assistant"}) is True
