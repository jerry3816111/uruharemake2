import json
from pathlib import Path

import p4_as_real_selected_action_surface_execution as gate


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_as_real_selected_action_surface_execution_evidence_2026-09-25.json"


def test_p4_as_real_result_preserves_the_frozen_exact_surface_failure():
    evidence = json.loads(RESULT.read_text(encoding="utf-8"))
    evaluated = gate.evaluate_real_evidence(gate.load_contract(), evidence)

    assert evidence["status"] == "fail"
    assert evaluated["status"] == "fail"
    assert evaluated["failed_gates"] == [
        "turn:visible_reply",
        "metric_mismatch:exact_visible_reply_count",
    ]
    assert evidence["turn"]["visible_reply_exact"] is False


def test_p4_as_real_result_keeps_the_successful_causal_chain_visible():
    row = json.loads(RESULT.read_text(encoding="utf-8"))["turn"]

    assert row["p4_as_status"] == "executed_and_committed"
    assert row["selected_policy"] == "calibrate_need"
    assert row["surface_verified"] is True
    assert row["m44_status"] == "registered_for_next_user_turn"
    assert row["receipt_identity_exact"] is True
    assert row["pending_preexisting_exact"] is True
    assert row["p4_ar_status"] == "authorized_executed_product_event"
    assert row["p4_ar_authorized"] is True
    assert row["p4_ar_failed_checks"] == []
    assert row["verification_binding_status"] == "pending"
    assert row["verification_binding_candidate_count"] == 6
    assert row["temporal_future_status"] == "committed_outcome_locked"


def test_p4_as_real_result_preserves_exact_runtime_and_visual_facts():
    evidence = json.loads(RESULT.read_text(encoding="utf-8"))
    row = evidence["turn"]
    artifacts = evidence["raw_runtime_artifacts"]

    assert [
        row["identity_node_index"],
        row["p4_as_node_index"],
        row["p4_ar_node_index"],
        row["temporal_node_index"],
        row["ordering_node_index"],
    ] == [64, 65, 66, 67, 68]
    assert row["utterance_node_index"] == 69
    assert row["required_nodes_before_utterance"] is True
    assert row["logic_runtime_graph_payload_exact"] is True
    assert row["safari_p4_as_node_visually_observed"] is True
    assert row["safari_p4_ar_node_visually_observed"] is True
    assert row["safari_temporal_node_visually_observed"] is True
    assert artifacts["conversation_jsonl_rows"] == 1
    assert artifacts["conversation_jsonl_sha256"] == (
        "a1a034f031fe1430c0b6d04bb6f88e875db96c190138769c1ddbb706518c5426"
    )
    assert artifacts["isolated_chroma_embedding_count"] == 1
    assert artifacts["server_left_running_for_user_inspection"] is True
    assert artifacts["safari_left_on_result_page"] is True
    assert artifacts["closed_tab_count"] == 0


def test_p4_as_formal_failure_separates_action_from_exact_wording():
    evidence = json.loads(RESULT.read_text(encoding="utf-8"))

    assert "action-level correctness and exact surface-string reproducibility" in evidence["analysis"]
    assert "Do not retune or rerun this case" in evidence["next_design_implication"]
