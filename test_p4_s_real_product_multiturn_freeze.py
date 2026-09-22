import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FREEZE = ROOT / "research" / "p4_s_real_product_multiturn_freeze_2026-09-22.json"


def _load():
    return json.loads(FREEZE.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_freeze_binds_prior_result_dataset_contract_gate_tests_and_launcher():
    freeze = _load()
    assert freeze["status"] == "frozen_before_real_execution"
    for binding in freeze["bindings"].values():
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_execution_shape_and_resource_ceilings_are_frozen():
    execution = _load()["execution"]
    assert execution["listener"] == "127.0.0.1:7869"
    assert execution["process_starts"] == 2
    assert execution["restart_after_turn"] == 6
    assert execution["real_product_turns"] == 12
    assert execution["retry_count"] == 0
    assert execution["local_product_planner_model_calls_maximum"] == 7
    assert execution["maximum_turn_latency_seconds"] == 20.0
    assert execution["maximum_total_latency_seconds"] == 180.0


def test_failure_policy_forbids_same_case_rescue():
    policy = _load()["failure_policy"]
    assert policy["same_case_rerun_allowed"] is False
    assert policy["input_value_expected_surface_gate_or_budget_change_allowed"] is False
    assert policy["manual_memory_seed_allowed"] is False


def test_claim_boundary_separates_product_integration_from_strong_llm_evidence():
    boundary = _load()["claim_boundary"]
    assert "full-pipeline integration evidence only" in boundary
    assert "not a strong-LLM comparison" in boundary
    assert "50-turn" in boundary
