import json
from pathlib import Path

from p4_aa_real_product_source_proposition_gate import evaluate_evidence, load_contract


ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / "analysis" / "p4_aa_real_product_source_proposition_evidence_2026-09-23.json"
RESULT = ROOT / "analysis" / "p4_aa_real_product_source_proposition_result_2026-09-23.json"


def test_p4_aa_committed_real_product_evidence_preserves_frozen_gate_failure():
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    expected = evaluate_evidence(load_contract(), evidence)
    committed = json.loads(RESULT.read_text(encoding="utf-8"))
    assert expected == committed
    assert committed["status"] == "fail"
    assert committed["failed_gates"] == [
        "turn_1_surface_chain_mismatch",
        "turn_2_surface_chain_mismatch",
        "turn_3_surface_chain_mismatch",
        "turn_4_surface_chain_mismatch",
        "metric_mismatch:exact_surface_chain_count",
    ]


def test_p4_aa_real_turns_have_exact_graph_payloads_and_supported_surfaces():
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert len(evidence["turns"]) == 4
    assert all(row["exact_logic_to_graph_payload_count"] == 4 for row in evidence["turns"])
    assert all(row["surface_chain"][-2:] == ["source_bound_proposition_preservation_p4", "utterance"] for row in evidence["turns"])
    assert all("utterance_frame_coverage_extension_p4" in row["surface_chain"] for row in evidence["turns"])
    assert evidence["metrics"]["exact_surface_chain_count"] == 0
    assert all(row["p4_z_violations_after"] == [] for row in evidence["turns"][:3])
    assert evidence["turns"][3]["p4_z_status"] == "source_pattern_unavailable"
    assert evidence["turns"][3]["p4_z_changed"] is False
    assert evidence["raw_runtime_artifacts"]["matching_turn_episode_count"] == 4
    assert evidence["safari"]["closed_tab_count"] == 0
