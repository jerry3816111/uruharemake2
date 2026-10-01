import json
from pathlib import Path

import p4_ar_real_executed_action_identity_gate as gate


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_ar_real_executed_action_identity_gate_evidence_2026-09-25.json"


def test_p4_ar_real_result_passes_the_frozen_authority_gate():
    evidence = json.loads(RESULT.read_text(encoding="utf-8"))
    evaluated = gate.evaluate_real_evidence(gate.load_contract(), evidence)

    assert evidence["status"] == "pass"
    assert evaluated["status"] == "pass"
    assert evaluated["failed_gates"] == []


def test_p4_ar_real_result_preserves_shadow_ambiguity_without_false_verification():
    evidence = json.loads(RESULT.read_text(encoding="utf-8"))
    row = evidence["turn"]

    assert row["ordering_status"] == "repaired_extended_trigger_downstream_order"
    assert row["guard_status"] == "blocked_unexecuted_shadow_action"
    assert row["ambiguity_candidate_count"] == 6
    assert row["verification_binding_status"] == "not_available"
    assert row["verification_binding_candidate_count"] == 0
    assert row["suppressed_shadow_candidate_count"] == 6
    assert row["temporal_present_candidate_count"] == 0
    assert row["temporal_future_status"] == "not_available"
    assert row["fallback_identity_promoted_to_p1"] is False
    assert row["outcome_verification_authorized"] is False
    assert row["p1_identity_node_absent"] is True


def test_p4_ar_real_result_preserves_exact_runtime_and_visual_facts():
    evidence = json.loads(RESULT.read_text(encoding="utf-8"))
    row = evidence["turn"]
    artifacts = evidence["raw_runtime_artifacts"]

    assert [
        row["guard_node_index"],
        row["ordering_node_index"],
        row["binding_node_index"],
        row["temporal_node_index"],
    ] == [64, 65, 66, 67]
    assert row["utterance_node_index"] == 68
    assert row["required_nodes_before_utterance"] is True
    assert row["logic_runtime_graph_payload_exact"] is True
    assert row["safari_guard_node_visually_expanded"] is True
    assert artifacts["conversation_jsonl_rows"] == 1
    assert artifacts["conversation_jsonl_sha256"] == (
        "d034772f40261d4d85a50c68027b41667a48378d78d63838664a8be64364fb86"
    )
    assert artifacts["isolated_chroma_embedding_count"] == 1
    assert artifacts["server_left_running_for_user_inspection"] is True
    assert artifacts["safari_left_on_result_page"] is True
    assert artifacts["closed_tab_count"] == 0


def test_p4_ar_pass_does_not_hide_the_surface_quality_failure():
    evidence = json.loads(RESULT.read_text(encoding="utf-8"))

    assert evidence["turn"]["visible_reply"] == "うちの頭は考えで埋まって今夜落ち着かないんだね。"
    assert "speaker ownership" in evidence["quality_observation_outside_frozen_gate"]
    assert "not felt-understanding" in evidence["quality_observation_outside_frozen_gate"]
