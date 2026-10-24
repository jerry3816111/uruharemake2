from pathlib import Path

import p4_ai_fresh_ambiguity_learning_chain_gate as gate
import uruha_ambiguity_learning_chain_p4 as chain

ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "p4_ai_fresh_ambiguity_learning_chain_v1.json"


def test_fixed_chain_does_not_store_raw_turns_or_change_visible_behavior():
    trace = chain.run_fixed_chain_p4_ai(
        "My thoughts cannot settle tonight.",
        "The train was early.",
        1,
    )
    assert trace["visible_reply_changed"] is False
    assert trace["model_call_added"] is False
    assert trace["fact_write_count"] == 0
    assert trace["resolution"]["outcome"] == "unknown"
    assert trace["resolution"]["unknown_counted_as_success"] is False


def test_new_frozen_multiturn_chain_preserves_typed_path_failure():
    evidence = chain.build_dataset_evidence_p4_ai(DATASET)
    result = gate.evaluate_evidence(gate.load_contract(), evidence)
    assert result["status"] == "fail"
    assert result["failed_gates"] == [
        "ai_contradict_ja:typed_trigger_false",
        "metric_mismatch:typed_trigger_count",
    ]
    assert evidence["metrics"]["typed_trigger_count"] == 8
    assert evidence["metrics"]["exact_identity_binding_count"] == 9
    assert evidence["metrics"]["exact_outcome_count"] == 9
