import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_az_real_previous_turn_ellipsis_to_action_delivery_v1.json"
DATASET = ROOT / "datasets" / "p4_az_real_previous_turn_ellipsis_to_action_delivery_v1.json"


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    return contract, dataset


def test_p4_az_real_pair_is_sealed_hash_bound_and_non_retryable():
    contract, dataset = _load()

    assert contract["status"] == "prospectively_frozen_before_real_execution"
    assert dataset["status"] == "sealed_before_real_execution"
    assert contract["dataset"]["sha256"] == _sha(DATASET)
    assert contract["dataset"]["turn_count"] == len(dataset["turns"]) == 2
    assert contract["execution"]["port"] == 7892
    assert contract["execution"]["private_runtime_required"] is True
    assert contract["execution"]["safari_required"] is True
    assert contract["execution"]["turns_must_run_in_one_session"] is True
    assert contract["execution"]["rerun_or_retry_after_result_allowed"] is False


def test_p4_az_real_pair_is_disjoint_from_exposed_real_and_offline_inputs():
    _contract, dataset = _load()
    inputs = {row["input"] for row in dataset["turns"]}
    prior_paths = (
        "datasets/p4_az_previous_turn_cjk_ellipsis_authority_v1.json",
        "datasets/p4_ax_real_compound_feedback_to_action_delivery_v1.json",
        "datasets/p4_aw_real_cjk_ellipsis_to_action_delivery_v1.json",
        "datasets/p4_av_real_neutral_operational_role_delivery_v1.json",
        "datasets/p4_au_real_source_bound_current_action_delivery_v1.json",
        "datasets/p4_at_real_executed_action_outcome_closure_v1.json",
    )
    serialized = "\n".join((ROOT / path).read_text(encoding="utf-8") for path in prior_paths)

    assert len(inputs) == 2
    for value in inputs:
        assert value not in serialized


def test_p4_az_real_gate_requires_the_full_authority_and_visible_delivery_chain():
    contract, _dataset = _load()
    gates = contract["formal_gates"]
    failure = contract["failure_policy"]

    assert gates["turn_1_p4_aw_authorized_count"] == 1
    assert gates["turn_1_p4_as_executed_count"] == 1
    assert gates["turn_1_exact_m44_receipt_count"] == 1
    assert gates["turn_2_p4_ax_authorized_count"] == 1
    assert gates["turn_2_p4_at_closed_supported_count"] == 1
    assert gates["turn_2_p4_ay_constraint_authorized_count"] == 1
    assert gates["turn_2_p4_ay_genuine_task_ref_count"] == 0
    assert gates["turn_2_p4_ay_prior_role_only_stop_count"] == 1
    assert gates["turn_2_p4_az_authorized_count"] == 1
    assert gates["turn_2_p4_az_source_role_preserved_unspecified_count"] == 1
    assert gates["turn_2_p4_au_prior_source_linked_count"] == 1
    assert gates["turn_2_p4_au_exact_turn_1_source_count"] == 1
    assert gates["turn_2_p4_av_integrity_pass_count"] == 1
    assert gates["turn_2_p4_av_remaining_unsupported_count"] == 0
    assert gates["turn_2_m53_no_unsupported_count"] == 1
    assert gates["turn_2_m45_delivered_count"] == 1
    assert gates["turn_2_m46_verified_count"] == 1
    assert gates["turn_2_m39_practical_act_count"] == 1
    assert gates["turn_2_generic_promise_or_clarification_count"] == 0
    assert failure["timeout_or_json_parse_failure_may_count_as_delivery"] is False
    assert failure["internal_plan_without_visible_action_may_count_as_delivery"] is False


def test_p4_az_real_gate_preserves_graph_source_and_cost_boundaries():
    contract, _dataset = _load()
    gates = contract["formal_gates"]

    assert gates["p4_ay_node_before_p4_az_p4_au_m50_m53_m46_m45_utterance_count"] == 1
    assert gates["p4_az_node_before_p4_au_m50_m53_m46_m45_utterance_count"] == 1
    assert gates["p4_ax_node_before_p4_at_p4_ag_temporal_utterance_count"] == 1
    assert gates["p4_az_new_model_call_count"] == 0
    assert gates["p4_az_factual_memory_write_count"] == 0
    assert gates["p4_az_raw_dialogue_trace_count"] == 0
    assert gates["p4_az_source_role_rewrite_count"] == 0
    assert gates["assistant_or_private_inference_source_count"] == 0
    assert gates["exact_visible_string_gate_count"] == 0
    assert gates["latency_target_met_count"] == 2
    assert contract["execution"]["latency_must_be_recorded"] is True
    assert contract["execution"]["model_calls_and_tokens_must_be_recorded"] is True


def test_p4_az_real_contract_binds_frozen_implementation_hashes():
    contract, _dataset = _load()

    for _name, (relative, expected) in contract["implementation"].items():
        assert _sha(ROOT / relative) == expected
