from pathlib import Path

import p4_ah_multilingual_trigger_coverage_gate as gate
import uruha_adaptive_person_model as adaptive
import uruha_multilingual_observable_trigger_p4 as coverage


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "p4_ah_multilingual_trigger_coverage_v1.json"


def test_extension_requires_bounded_composition_and_keeps_private_truth_unknown():
    positive = coverage.extend_observable_trigger_p4("My thoughts cannot settle tonight.")
    object_motion = coverage.extend_observable_trigger_p4("The fan cannot settle on one speed.")
    assert positive["predicates"] == ["cognitive_overactivity"]
    assert positive["private_state_truth_claimed"] is False
    assert positive["coverage_extension"]["complete_sentence_lookup_used"] is False
    assert object_motion["predicates"] == []


def test_extension_does_not_mutate_released_m37_trace():
    base = adaptive.extract_observable_trigger_predicates_m37("My thoughts cannot settle tonight.")
    before = dict(base)
    extended = coverage.extend_observable_trigger_p4("My thoughts cannot settle tonight.", base)
    assert base == before
    assert base["predicates"] == []
    assert extended["predicates"] == ["cognitive_overactivity"]
    assert extended["base_trace_mutated"] is False


def test_frozen_multilingual_coverage_and_controls_pass_fail_closed_gate():
    evidence = coverage.build_dataset_evidence_p4_ah(DATASET)
    result = gate.evaluate_evidence(gate.load_contract(), evidence)
    assert result["status"] == "pass", result["failed_gates"]
    assert result["failed_gates"] == []
