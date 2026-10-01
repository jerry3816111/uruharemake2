import json
from pathlib import Path

import p4_s_real_product_multiturn_gate as gate


ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / "analysis" / "p4_s_real_product_multiturn_evidence_2026-09-22.json"
RESULT = ROOT / "analysis" / "p4_s_real_product_multiturn_result_2026-09-22.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_preserved_real_evidence_passes_the_prospectively_frozen_gate():
    evidence = _load(EVIDENCE)
    expected = _load(RESULT)
    assert gate.evaluate_evidence(gate.load_contract(), evidence) == expected
    assert evidence["metrics"]["maximum_total_latency_seconds"] == 121.1807
    assert evidence["metrics"]["maximum_turn_latency_seconds"] == 16.3151
    assert evidence["raw_runtime_artifacts"]["conversation_jsonl_rows"] == 12
    assert evidence["raw_runtime_artifacts"]["turn_episode_count"] == 12


def test_result_does_not_hide_surface_failures_outside_the_narrow_gate():
    evidence = _load(EVIDENCE)
    observations = evidence["surface_quality_observations_outside_frozen_gate"]
    assert [row["turn"] for row in observations] == [4, 7, 9, 10]
    assert all(row["verifier_false_negative"] is True for row in observations)
    assert evidence["accounting"]["local_product_planner_model_calls_maximum"] == 0
    assert evidence["accounting"]["local_semantic_authorization_model_calls"] == 9
    assert evidence["accounting"]["local_semantic_authorization_token_accounting"] == "unavailable"


def test_final_typed_state_and_restart_lineage_are_exact():
    evidence = _load(EVIDENCE)
    assert evidence["restart"]["old_pid"] != evidence["restart"]["new_pid"]
    assert evidence["restart"]["old_session_id"] != evidence["restart"]["new_session_id"]
    assert evidence["final_state"]["drink_active_values"] == ["なた豆茶"]
    assert evidence["final_state"]["drink_historical_values"] == ["松葉茶"]
    assert evidence["final_state"]["drink_explicit_negative_values"] == ["松葉茶"]
    assert evidence["final_state"]["game_active_values"] == ["ストラテジーゲーム"]
    assert evidence["final_state"]["correction_previous_link_valid"] is True
    assert evidence["final_state"]["negative_correction_link_valid"] is True
