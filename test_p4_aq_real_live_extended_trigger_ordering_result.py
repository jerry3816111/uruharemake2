import json
from pathlib import Path

import p4_aq_real_live_extended_trigger_ordering_gate as gate


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_aq_real_live_extended_trigger_ordering_result_2026-09-25.json"


def test_p4_aq_real_result_preserves_first_turn_identity_failure():
    evidence = json.loads(RESULT.read_text(encoding="utf-8"))
    evaluated = gate.evaluate_real_evidence(gate.load_contract(), evidence)

    assert evidence["status"] == "terminal_fail_after_first_formal_turn"
    assert evaluated["status"] == "fail"
    assert "turn_count_mismatch" in evaluated["failed_gates"]
    assert "metric_mismatch:identity_node_count" in evaluated["failed_gates"]
    assert "metric_mismatch:prediction_sequence_exact_count" in evaluated["failed_gates"]
    assert "metric_mismatch:shadow_pending_identity_exact_count" in evaluated["failed_gates"]
    assert "safari_three_turn_missing" in evaluated["failed_gates"]
    assert "additive_shadow_identity" in evidence["root_cause"]


def test_p4_aq_failure_keeps_ordering_success_separate():
    evidence = json.loads(RESULT.read_text(encoding="utf-8"))
    row = evidence["turns"][0]

    assert row["trigger_path"] == "p4_ah_additive_compositional_trigger"
    assert row["ordering_status"] == "repaired_extended_trigger_downstream_order"
    assert row["ordering_repair"]["before_candidate_count"] == 0
    assert row["ordering_repair"]["after_candidate_count"] == 6
    assert row["present_candidate_count"] == 6
    assert row["current_future_status"] == "committed_outcome_locked"
    assert row["prediction_id_source"] == "additive_shadow_identity"
    assert row["prediction_sequence"] is None
    assert row["identity_node_absent"] is True
    assert row["all_required_nodes_before_utterance"] is False
    assert row["raw_or_private_payload_leak"] is False
    assert evidence["safari"]["actual_three_turn_acceptance"] is False


def test_p4_aq_failure_preserves_exact_runtime_artifact_facts():
    evidence = json.loads(RESULT.read_text(encoding="utf-8"))
    artifacts = evidence["raw_runtime_artifacts"]

    assert artifacts["conversation_jsonl_rows"] == 1
    assert artifacts["conversation_jsonl_sha256"] == (
        "47459426f3f76f0fe453f269f74ec7329edf986f16783bd50b1bf0d40cf28250"
    )
    assert artifacts["isolated_chroma_embedding_count"] == 1
    assert artifacts["server_left_running_for_user_inspection"] is True
    assert artifacts["safari_left_on_result_page"] is True
    assert artifacts["closed_tab_count"] == 0
