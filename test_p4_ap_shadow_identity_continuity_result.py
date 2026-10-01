import json
from pathlib import Path

import p4_ap_shadow_identity_continuity_gate as gate


ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / "analysis" / "p4_ap_shadow_identity_continuity_evidence_2026-09-25.json"
RESULT = ROOT / "analysis" / "p4_ap_shadow_identity_continuity_result_2026-09-25.json"


def test_p4_ap_committed_real_result_matches_frozen_gate():
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    expected = gate.evaluate_real_evidence(gate.load_contract(), evidence)
    committed = json.loads(RESULT.read_text(encoding="utf-8"))
    assert evidence["status"] == "pass"
    assert expected == committed
    assert committed["status"] == "pass"
    assert committed["failed_gates"] == []


def test_p4_ap_real_turns_preserve_exact_identity_and_temporal_order():
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert [row["prediction_sequence"] for row in evidence["turns"]] == [1, 2, 3]
    assert [row["shadow_identity_floor"] for row in evidence["turns"]] == [0, 1, 2]
    assert [row["past_record_count"] for row in evidence["turns"]] == [0, 0, 1]
    assert [row["previous_outcome"] for row in evidence["turns"]] == [None, "supported", "supported"]
    assert all(row["identity_node_index"] < row["temporal_node_index"] < row["utterance_node_index"] for row in evidence["turns"])
    assert all(row["logic_graph_payload_exact"] for row in evidence["turns"])
    assert all(row["raw_or_private_payload_leak"] is False for row in evidence["turns"])
    assert evidence["raw_runtime_artifacts"]["isolated_chroma_embedding_count"] == 3


def test_p4_ap_acceptance_does_not_hide_remaining_quality_or_ordering_gap():
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert evidence["turns"][1]["visible_reply"] == evidence["turns"][2]["visible_reply"]
    assert "did not test felt-understanding" in evidence["quality_observation_outside_frozen_gate"]
    assert "P4-AH-to-P4-AD" in evidence["remaining_known_failure"]
