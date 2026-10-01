import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FREEZE = ROOT / "research" / "p4_r_multiturn_interference_freeze_2026-09-22.json"


def _load():
    return json.loads(FREEZE.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_freeze_binds_prior_result_dataset_contract_gate_and_tests():
    freeze = _load()
    assert freeze["status"] == "frozen_before_holdout_execution"
    for binding in freeze["bindings"].values():
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_freeze_declares_one_mechanism_difference_and_zero_model_execution():
    freeze = _load()
    assert "baseline selects the latest tea token" in freeze["single_causal_difference"]
    execution = freeze["execution"]
    assert execution["dataset_execution_count"] == 1
    assert execution["retry_count"] == 0
    assert execution["local_model_call_count"] == 0
    assert execution["safari_turn_count"] == 0


def test_failure_policy_forbids_same_case_rescue():
    policy = _load()["failure_policy"]
    assert policy["same_case_rerun_allowed"] is False
    assert policy["value_transcript_baseline_or_gate_change_allowed"] is False
    assert policy["failed_result_must_be_preserved"] is True


def test_claim_boundary_does_not_call_diagnostic_baseline_a_strong_llm():
    boundary = _load()["claim_boundary"]
    assert "zero-model mechanism comparison" in boundary
    assert "cannot establish advantage over a strong LLM" in boundary
    assert "50-turn" in boundary
