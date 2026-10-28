import json
from pathlib import Path

import p4_w_frame_preserving_visible_repair_gate as gate
import uruha_frame_preserving_visible_repair_p4 as p4w


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "p4_w_frame_preserving_visible_repair_v1.json"
EVIDENCE = ROOT / "analysis" / "p4_w_frame_preserving_visible_repair_evidence_2026-09-22.json"
RESULT = ROOT / "analysis" / "p4_w_frame_preserving_visible_repair_result_2026-09-22.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_saved_evidence_matches_reproducible_builder_and_frozen_gate():
    saved = _load(EVIDENCE)
    rebuilt = p4w.build_dataset_evidence_p4_w(DATASET)
    assert rebuilt == saved
    assert gate.evaluate_evidence(gate.load_contract(), saved) == _load(RESULT)


def test_result_is_bounded_repair_not_real_model_or_safari_claim():
    evidence = _load(EVIDENCE)
    result = _load(RESULT)
    assert result["status"] == "pass"
    assert result["failed_gates"] == []
    assert evidence["metrics"]["holdout_exact_reply_count"] == 12
    assert evidence["metrics"]["holdout_zero_unresolved_count"] == 12
    assert evidence["metrics"]["faithful_control_unchanged_count"] == 8
    assert evidence["metrics"]["new_model_call_count"] == 0
    assert "does not establish real-model or Safari behavior" in result["claim_boundary"]
