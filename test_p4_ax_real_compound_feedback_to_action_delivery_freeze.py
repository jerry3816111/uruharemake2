import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_ax_real_compound_feedback_to_action_delivery_v1.json"
DATASET = ROOT / "datasets" / "p4_ax_real_compound_feedback_to_action_delivery_v1.json"


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    return contract, dataset


def test_p4_ax_real_pair_is_sealed_and_hash_bound_before_execution():
    contract, dataset = _load()

    assert contract["status"] == "prospectively_frozen_before_real_execution"
    assert dataset["status"] == "sealed_before_real_execution"
    assert contract["dataset"]["sha256"] == _sha(DATASET)
    assert contract["dataset"]["turn_count"] == len(dataset["turns"]) == 2
    assert contract["execution"]["rerun_or_retry_after_result_allowed"] is False


def test_p4_ax_real_pair_is_disjoint_from_exposed_real_and_offline_inputs():
    _contract, dataset = _load()
    inputs = {row["input"] for row in dataset["turns"]}
    prior_paths = [
        ROOT / "datasets" / "p4_ax_compound_feedback_request_split_v1.json",
        ROOT / "datasets" / "p4_aw_real_cjk_ellipsis_to_action_delivery_v1.json",
        ROOT / "datasets" / "p4_av_real_neutral_operational_role_delivery_v1.json",
        ROOT / "datasets" / "p4_au_real_source_bound_current_action_delivery_v1.json",
        ROOT / "datasets" / "p4_at_real_executed_action_outcome_closure_v1.json",
    ]
    serialized = "\n".join(path.read_text(encoding="utf-8") for path in prior_paths)

    assert len(inputs) == 2
    for value in inputs:
        assert value not in serialized


def test_p4_ax_real_gate_requires_full_visible_delivery_not_internal_state_only():
    contract, _dataset = _load()
    gates = contract["formal_gates"]
    failure = contract["failure_policy"]

    assert gates["turn_2_p4_ax_authorized_count"] == 1
    assert gates["turn_2_p4_at_closed_supported_count"] == 1
    assert gates["turn_2_p4_au_prior_source_linked_count"] == 1
    assert gates["turn_2_m45_delivered_count"] == 1
    assert gates["turn_2_m46_verified_count"] == 1
    assert gates["turn_2_m39_practical_act_count"] == 1
    assert gates["turn_2_generic_promise_or_clarification_count"] == 0
    assert failure["timeout_may_count_as_delivery"] is False
    assert failure["internal_plan_without_visible_action_may_count_as_delivery"] is False


def test_p4_ax_real_gate_preserves_graph_source_and_cost_boundaries():
    contract, _dataset = _load()
    gates = contract["formal_gates"]

    assert gates["p4_ax_node_before_p4_at_p4_ag_temporal_utterance_count"] == 1
    assert gates["p4_au_node_before_m50_m53_m46_m45_utterance_count"] == 1
    assert gates["p4_av_node_before_m53_m46_m45_utterance_count"] == 1
    assert gates["assistant_or_private_inference_source_count"] == 0
    assert gates["exact_visible_string_gate_count"] == 0
    assert gates["latency_target_met_count"] == 2
    assert contract["execution"]["model_calls_and_tokens_must_be_recorded"] is True


def test_p4_ax_real_contract_binds_frozen_implementation_hashes():
    contract, _dataset = _load()

    for _name, (relative, expected) in contract["implementation"].items():
        assert _sha(ROOT / relative) == expected
