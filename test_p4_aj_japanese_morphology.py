from pathlib import Path

import p4_aj_japanese_morphology_gate as gate
import uruha_japanese_trigger_morphology_p4 as morphology

ROOT = Path(__file__).resolve().parent


def test_frozen_japanese_inflections_and_controls_pass():
    evidence = morphology.build_dataset_evidence_p4_aj(ROOT / gate.load_contract()["dataset"][0])
    result = gate.evaluate_evidence(gate.load_contract(), evidence)
    assert result["status"] == "pass", result["failed_gates"]


def test_result_is_typed_evidence_not_private_truth():
    trace = morphology.extend_japanese_morphology_p4("考えが止められず、まだ続いている。")
    assert trace["predicates"] == ["cognitive_overactivity"]
    assert trace["private_state_truth_claimed"] is False
    assert trace["visible_reply_changed"] is False
