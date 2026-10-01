import json
from pathlib import Path

import p4_y_real_product_graph_delivery_gate as gate


ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / "analysis" / "p4_y_real_product_graph_delivery_evidence_2026-09-22.json"
RESULT = ROOT / "analysis" / "p4_y_real_product_graph_delivery_result_2026-09-22.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_saved_real_product_evidence_reproduces_frozen_pass():
    evidence = _load(EVIDENCE)
    result = _load(RESULT)
    assert gate.evaluate_evidence(gate.load_contract(), evidence) == result
    assert result["status"] == "pass"
    assert result["failed_gates"] == []


def test_real_safari_chain_payload_and_durable_evidence_are_complete():
    evidence = _load(EVIDENCE)
    assert len(evidence["turns"]) == 2
    assert all(row["delivery_complete"] for row in evidence["turns"])
    assert all(row["exact_logic_to_graph_payload_count"] == 3 for row in evidence["turns"])
    assert evidence["metrics"]["exact_logic_to_graph_payload_count"] == 6
    assert evidence["metrics"]["durable_episode_count"] == 2
    assert evidence["metrics"]["typed_write_count"] == 0
    assert evidence["raw_runtime_artifacts"]["user_profile_count"] == 0


def test_resource_and_no_rerun_boundaries_are_preserved():
    evidence = _load(EVIDENCE)
    assert evidence["resource_notes"]["semantic_authorization_model_calls"] == 2
    assert evidence["resource_notes"]["p4_y_added_model_calls"] == 0
    assert evidence["resource_notes"]["token_accounting"] == "unavailable"
    assert evidence["decision"]["same_case_rerun_allowed"] is False
    assert evidence["safari"]["new_result_tab_left_open"] is True
    assert evidence["accounting"]["closed_user_tab_count"] == 0
