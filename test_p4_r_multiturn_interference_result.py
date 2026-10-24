import hashlib
import json
from pathlib import Path

import p4_r_multiturn_interference_gate as gate


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_r_multiturn_interference_result_2026-09-22.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_result_binds_freeze_and_one_preserved_execution():
    result = _load(RESULT)
    assert result["status"] == "pass"
    assert _sha256(ROOT / result["freeze_checkpoint"]["freeze"]["path"]) == result[
        "freeze_checkpoint"
    ]["freeze"]["sha256"]
    assert _sha256(ROOT / result["evidence"]["path"]) == result["evidence"]["sha256"]
    assert result["accounting"]["dataset_execution_count"] == 1
    assert result["accounting"]["retry_count"] == 0


def test_frozen_gate_recomputes_pass_from_preserved_evidence():
    result = _load(RESULT)
    evidence = _load(ROOT / result["evidence"]["path"])
    recomputed = gate.evaluate_evidence(gate.load_contract(), evidence)
    assert recomputed["status"] == "pass"
    assert recomputed["failed_gates"] == []
    assert result["gate_result"]["failed_gate_count"] == 0


def test_result_keeps_diagnostic_baseline_distinct_from_strong_llm_evidence():
    result = _load(RESULT)
    assert result["comparison"]["baseline"]["exact_recall"] == "0/2"
    assert result["comparison"]["system"]["exact_recall"] == "2/2"
    relation = result["relationship_to_prior_long_dialogue_work"]
    assert relation["v2_22_strong_full_context_comparison_replaced"] is False
    assert "not new strong-LLM evidence" in relation["new_result"]


def test_result_proves_scope_and_correction_lineage_without_mental_fact_write():
    evidence = _load(ROOT / _load(RESULT)["evidence"]["path"])
    assert evidence["final_state"]["drink_active_values"] == ["よもぎ茶"]
    assert evidence["final_state"]["drink_historical_values"] == ["月桃茶"]
    assert evidence["final_state"]["game_active_values"] == ["cooperative games"]
    assert evidence["final_state"]["correction_previous_link_valid"] is True
    assert evidence["final_state"]["negative_correction_link_valid"] is True
    assert evidence["metrics"]["unverified_mental_fact_write_count"] == 0


def test_claim_boundary_excludes_full_product_fifty_turn_and_human_equation_claims():
    boundary = _load(RESULT)["claim_boundary"]
    assert "does not prove advantage over a strong LLM" in boundary
    assert "full product or Safari behavior" in boundary
    assert "50-turn memory" in boundary
    assert "human equation" in boundary
