import json
from pathlib import Path

import p4_t_utterance_frame_shadow_gate as gate
import uruha_utterance_frame_shadow_p4 as p4t


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "p4_t_utterance_frame_shadow_v1.json"
EVIDENCE = ROOT / "analysis" / "p4_t_utterance_frame_shadow_evidence_2026-09-22.json"
RESULT = ROOT / "analysis" / "p4_t_utterance_frame_shadow_result_2026-09-22.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_saved_evidence_matches_reproducible_builder_and_frozen_gate():
    saved = _load(EVIDENCE)
    rebuilt = p4t.build_dataset_evidence_p4_t(DATASET)
    assert rebuilt == saved
    assert gate.evaluate_evidence(gate.load_contract(), saved) == _load(RESULT)


def test_result_is_detection_only_not_visible_repair_claim():
    evidence = _load(EVIDENCE)
    assert evidence["metrics"]["candidate_unchanged_count"] == 24
    assert evidence["metrics"]["holdout_exact_violation_count"] == 12
    assert evidence["metrics"]["plain_control_false_positive_count"] == 0
    assert evidence["metrics"]["new_model_call_count"] == 0
    assert evidence["metrics"]["profile_write_count"] == 0
    assert "does not prove visible repair" in _load(RESULT)["claim_boundary"]
