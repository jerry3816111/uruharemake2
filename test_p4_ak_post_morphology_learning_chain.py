from pathlib import Path

import p4_ak_post_morphology_learning_chain_gate as gate
import uruha_post_morphology_learning_chain_p4 as chain


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "p4_ak_post_morphology_learning_chain_v1.json"


def test_fixed_chain_is_shadow_only_and_unknown_is_not_success():
    trace = chain.run_fixed_chain_p4_ak(
        "My thoughts will not settle after the rehearsal.",
        "The bus stop has a new map.",
        1,
    )
    assert trace["visible_reply_changed"] is False
    assert trace["model_call_added"] is False
    assert trace["fact_write_count"] == 0
    assert trace["resolution"]["outcome"] == "unknown"
    assert trace["resolution"]["unknown_counted_as_success"] is False


def test_prospectively_frozen_post_morphology_chain_preserves_path_gate_failure():
    evidence = chain.build_dataset_evidence_p4_ak(DATASET)
    result = gate.evaluate_evidence(gate.load_contract(), evidence)
    assert result["status"] == "fail"
    assert result["failed_gates"] == [
        "metric_mismatch:japanese_morphology_extension_count"
    ]
    assert evidence["metrics"]["japanese_morphology_extension_count"] == 2
    assert evidence["metrics"]["exact_identity_binding_count"] == 9
    assert evidence["metrics"]["exact_outcome_count"] == 9
