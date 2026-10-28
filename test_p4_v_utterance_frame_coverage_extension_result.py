import json
from pathlib import Path

import p4_v_utterance_frame_coverage_extension_gate as gate
import uruha_utterance_frame_shadow_extension_p4 as p4v


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "p4_v_utterance_frame_coverage_extension_v1.json"
EVIDENCE = ROOT / "analysis" / "p4_v_utterance_frame_coverage_extension_evidence_2026-09-22.json"
RESULT = ROOT / "analysis" / "p4_v_utterance_frame_coverage_extension_result_2026-09-22.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_saved_evidence_matches_reproducible_builder_and_frozen_gate():
    saved = _load(EVIDENCE)
    rebuilt = p4v.build_dataset_evidence_p4_v(DATASET)
    assert rebuilt == saved
    assert gate.evaluate_evidence(gate.load_contract(), saved) == _load(RESULT)


def test_result_is_shadow_coverage_not_visible_repair_or_open_domain_claim():
    evidence = _load(EVIDENCE)
    result = _load(RESULT)
    assert result["status"] == "pass"
    assert result["failed_gates"] == []
    assert evidence["metrics"]["holdout_exact_violation_count"] == 9
    assert evidence["metrics"]["faithful_control_false_positive_count"] == 0
    assert evidence["metrics"]["candidate_unchanged_count"] == 25
    assert evidence["metrics"]["new_model_call_count"] == 0
    assert "does not prove visible repair" in result["claim_boundary"]
