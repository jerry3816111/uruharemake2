"""P4-BE one-shot paired harness tests with a fake transport; no model calls."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

import run_p4_be_role_value_prompt as runner


ROOT = Path(__file__).resolve().parent
CONTRACT = json.loads((ROOT / "configs/p4_be_role_value_prompt_v1.json").read_text(encoding="utf-8"))
DATASET = json.loads((ROOT / "datasets/p4_be_role_value_prompt_v1.json").read_text(encoding="utf-8"))
BY_SOURCE = {case["source"]["id"]: case for case in DATASET["positive_cases"] + DATASET["control_cases"]}


def _fake_preflight(_contract_path, _output_path):
    return CONTRACT, DATASET, "fake-frozen-sha"


def _fake_prewarm(model, keep_alive):
    assert model == CONTRACT["model"]
    assert keep_alive == CONTRACT["controlled_constants"]["keep_alive"]
    return {"model": model, "attempted": True, "completed": True, "wall_seconds": 1.0}


def _fake_call(mode):
    def send(*, model, prompt, source, schema, contract, call_id):
        case = BY_SOURCE[source["id"]]
        slots = {key: "" for key in runner.bc.SLOT_KEYS}
        is_baseline = ":bc_frozen_prompt:" in call_id
        if "expected_spec" in case:
            gold = case["expected_spec"]
            slots.update(gold["slots"])
            atoms = deepcopy(gold["evidence_atoms"])
            if is_baseline and case["case_id"] == "p4_be_zh_scaffold_001":
                if mode == "role_win":
                    atoms[2]["text"] = "小步驟"  # exact source, misses one/now anchors
                elif mode == "slot_only":
                    slots["unknown_constraint_jp"] = ""
                elif mode == "bad_source_identity":
                    atoms[2]["text"] = "小步驟"
            parsed = {
                "status": "typed_spec", "source_id": source["id"], "source_span": source["text"],
                "template_id": gold["template_id"], "safety_class": "low_risk_reversible",
                "evidence_atoms": atoms, "slots": slots, "unavailable_reason": "none",
            }
            if is_baseline and case["case_id"] == "p4_be_zh_scaffold_001" and mode == "bad_source_identity":
                parsed["source_id"] = "current:wrong"
        else:
            parsed = {
                "status": "unavailable", "source_id": source["id"], "source_span": source["text"],
                "template_id": "unavailable", "safety_class": "unavailable",
                "evidence_atoms": [], "slots": slots,
                "unavailable_reason": case["expected_unavailable_reason"],
            }
        return {
            "call_id": call_id, "model": model, "attempted": True, "completed": True,
            "json_parse_success": True, "wall_seconds": 2.0,
            "prompt_tokens": 100, "completion_tokens": 40,
            "system_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "schema_sha256": hashlib.sha256(
                json.dumps(schema, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest(),
            "parsed": parsed,
        }
    return send


def _run_fake(tmp_path, monkeypatch, mode):
    monkeypatch.setattr(runner, "preflight", _fake_preflight)
    monkeypatch.setattr(runner.bc, "prewarm_model", _fake_prewarm)
    monkeypatch.setattr(runner.bc, "model_json_call", _fake_call(mode))
    output = tmp_path / "evidence.json"
    return runner.run(output_path=output), output


def test_p4_be_paired_runner_only_selects_a_true_raw_role_improvement(tmp_path, monkeypatch):
    evidence, output = _run_fake(tmp_path, monkeypatch, "role_win")
    baseline, candidate = evidence["arms"]
    comparison = evidence["comparison"]

    assert evidence["status"] == "pass_bounded_offline"
    assert evidence["selected_prompt"] == "be_role_value_prompt"
    assert evidence["executed_exactly_once_per_arm_case"] is True
    assert evidence["retry_count"] == 0
    assert evidence["product_runtime_changed"] is False
    assert len(evidence["rows"]) == 28
    assert baseline["metrics"]["positive_full_accept_count"] == 5
    assert candidate["metrics"]["positive_full_accept_count"] == 6
    assert candidate["absolute_eligible"] is True
    assert comparison["paired_advantage"] is True
    assert comparison["metrics"]["be_only_full_accept"] == 1
    assert comparison["metrics"]["bc_only_full_accept"] == 0
    assert comparison["metrics"]["be_only_raw_role_value_evidence_with_both_source_identities_valid"] == 1
    assert evidence["prompt_sha256_by_arm"]["bc_frozen_prompt"] != evidence["prompt_sha256_by_arm"]["be_role_value_prompt"]
    first = [row for row in evidence["rows"] if row["case_id"] == "p4_be_zh_scaffold_001"]
    second = [row for row in evidence["rows"] if row["case_id"] == "p4_be_zh_group_001"]
    assert [row["arm"] for row in first] == CONTRACT["arms"]
    assert [row["arm"] for row in second] == list(reversed(CONTRACT["arms"]))
    assert first[0]["call"]["schema_sha256"] == first[1]["call"]["schema_sha256"]
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == evidence["status"]
    with pytest.raises(FileExistsError):
        runner.run(output_path=output)


def test_p4_be_slot_only_repair_cannot_masquerade_as_role_value_uplift(tmp_path, monkeypatch):
    evidence, _output = _run_fake(tmp_path, monkeypatch, "slot_only")
    comparison = evidence["comparison"]
    baseline = next(
        row for row in evidence["rows"]
        if row["arm"] == "bc_frozen_prompt" and row["case_id"] == "p4_be_zh_scaffold_001"
    )
    assert baseline["normalization"]["status"] == "invalid"
    assert baseline["raw_role_value_evidence"] is True
    assert baseline["role_value_evidence"] is False
    assert evidence["arms"][1]["absolute_eligible"] is True
    assert comparison["metrics"]["be_only_full_accept"] == 1
    assert comparison["metrics"]["be_only_raw_role_value_evidence_with_both_source_identities_valid"] == 0
    assert "be_only_raw_role_value_evidence_with_both_source_identities_valid_minimum" in comparison["failed_paired_gates"]
    assert evidence["status"] == "fail"
    assert evidence["next_state_if_failed"] == "REVIEW_REQUIRED"


def test_p4_be_raw_role_uplift_requires_both_exact_source_identities(tmp_path, monkeypatch):
    evidence, _output = _run_fake(tmp_path, monkeypatch, "bad_source_identity")
    comparison = evidence["comparison"]
    assert comparison["metrics"]["be_only_full_accept"] == 1
    assert comparison["metrics"]["be_only_raw_role_value_evidence_with_both_source_identities_valid"] == 0
    assert evidence["status"] == "fail"


def test_p4_be_failed_prewarm_stops_before_scored_calls(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "preflight", _fake_preflight)
    monkeypatch.setattr(
        runner.bc, "prewarm_model",
        lambda model, keep_alive: {"model": model, "attempted": True, "completed": False},
    )
    monkeypatch.setattr(
        runner.bc, "model_json_call",
        lambda **kwargs: pytest.fail("scored call after failed prewarm"),
    )
    evidence = runner.run(output_path=tmp_path / "prewarm_failed.json")
    assert evidence["status"] == "prewarm_failed_no_scored_calls"
    assert evidence["rows"] == []


def test_p4_be_formal_preflight_rejects_unfrozen_output_path_before_network(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "_get_json", lambda url: pytest.fail("network before fixed path check"))
    with pytest.raises(RuntimeError, match="single frozen output path"):
        runner.preflight(runner.DEFAULT_CONTRACT, tmp_path / "different.json")


def test_p4_be_zero_token_accounting_fails_even_if_frozen_quality_metrics_pass(tmp_path, monkeypatch):
    evidence, _output = _run_fake(tmp_path, monkeypatch, "role_win")
    changed = deepcopy(evidence["rows"])
    next(row for row in changed if row["arm"] == "be_role_value_prompt")["call"]["completion_tokens"] = 0
    summary = runner.summarize_arm("be_role_value_prompt", changed, CONTRACT)
    assert summary["metrics"]["token_accounting_complete"] is False
    assert "token_accounting_complete" in summary["failed_absolute_gates"]
