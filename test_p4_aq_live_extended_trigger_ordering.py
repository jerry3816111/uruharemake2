from copy import deepcopy
from pathlib import Path

import p4_aq_live_extended_trigger_ordering_gate as gate
import uruha_desired_response_ambiguity_p4 as ambiguity
import uruha_desired_response_outcome_binding_p4 as outcome_binding
import uruha_live_extended_trigger_ordering_p4 as ordering
import uruha_multilingual_observable_trigger_p4 as trigger
import uruha_runtime_temporal_graph_delivery_p4 as temporal


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets/p4_aq_live_extended_trigger_ordering_v1.json"


def test_offline_evidence_passes_frozen_ordering_gates():
    contract = gate.load_contract()
    evidence = ordering.build_dataset_evidence_p4_aq(DATASET)
    result = gate.evaluate_offline_evidence(contract, evidence)
    assert evidence["dataset_sha256"] == contract["dataset"]["sha256"]
    assert evidence["metrics"] == contract["offline_gates"]
    assert result["status"] == "pass"
    assert result["failed_gates"] == []


def test_positive_reorders_fixed_trace_before_all_downstream_nodes():
    frozen = gate.load_dataset(gate.load_contract())["fresh_positive_cases"][0]
    result, temporal_before, _, _ = ordering._synthetic_predecessor_result(frozen, 1)
    reply_before = result["reply"]
    rebuilt = ordering.rebuild_late_extended_trigger_chain_p4(
        result,
        temporal_before,
    )
    assert rebuilt["applied"] is True
    assert rebuilt["trace"]["status"] == "repaired_extended_trigger_downstream_order"
    assert rebuilt["result"]["reply"] == reply_before
    labels = [row["label"] for row in rebuilt["result"]["runtime_trace"]["blackboard"]]
    assert labels.index(trigger.LABEL) < labels.index(ambiguity.LABEL)
    assert labels.index(ambiguity.LABEL) < labels.index(outcome_binding.LABEL)
    assert labels.index(outcome_binding.LABEL) < labels.index(temporal.LABEL)
    assert labels.index(temporal.LABEL) < labels.index(ordering.LABEL)
    assert labels.index(ordering.LABEL) < labels.index("utterance")
    assert rebuilt["pending_binding"]["candidate_count"] == 6
    assert rebuilt["temporal_payload"]["future"]["status"] == "committed_outcome_locked"


def test_control_is_strict_noop_except_raw_free_audit_node():
    frozen = gate.load_dataset(gate.load_contract())["fresh_control_cases"][0]
    result, temporal_before, _, _ = ordering._synthetic_predecessor_result(frozen, 2)
    before = deepcopy(result)
    rebuilt = ordering.rebuild_late_extended_trigger_chain_p4(
        result,
        temporal_before,
    )
    assert rebuilt["applied"] is False
    assert rebuilt["trace"]["status"] == "not_applicable"
    assert rebuilt["result"]["reply"] == before["reply"]
    for label in (ambiguity.LABEL, outcome_binding.LABEL, trigger.LABEL, temporal.LABEL):
        assert rebuilt["result"]["runtime_trace"][label] == before["runtime_trace"][label]
    assert frozen["input"] not in ordering._canonical(rebuilt["trace"])


def test_repair_preserves_previous_resolution_and_does_not_mutate_inputs():
    frozen = gate.load_dataset(gate.load_contract())["fresh_positive_cases"][1]
    result, temporal_before, _, _ = ordering._synthetic_predecessor_result(frozen, 3)
    result_before = deepcopy(result)
    temporal_snapshot = deepcopy(temporal_before)
    previous = result["runtime_trace"][outcome_binding.LABEL]["previous_resolution"]
    rebuilt = ordering.rebuild_late_extended_trigger_chain_p4(result, temporal_before)
    assert result == result_before
    assert temporal_before == temporal_snapshot
    assert rebuilt["ag_trace"]["previous_resolution"] == previous
    assert rebuilt["trace"]["previous_resolution_preserved"] is True
    assert rebuilt["trace"]["source_state_mutated"] is False
    assert rebuilt["trace"]["source_temporal_state_mutated"] is False
