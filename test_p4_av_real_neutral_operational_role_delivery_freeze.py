import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs" / "p4_av_real_neutral_operational_role_delivery_v1.json"
DATASET = ROOT / "datasets" / "p4_av_real_neutral_operational_role_delivery_v1.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_p4_av_real_case_is_frozen_after_offline_pass_and_before_execution():
    config = _load(CONFIG)
    dataset = _load(DATASET)

    assert config["status"] == "prospectively_frozen_before_real_execution"
    assert dataset["status"] == "sealed_before_real_execution"
    assert config["dataset"]["sha256"] == _sha(DATASET)
    assert config["implementation"]["commit"] == "83ea808"
    assert config["execution"]["rerun_or_retry_after_result_allowed"] is False


def test_p4_av_real_inputs_are_new_across_existing_p4_datasets():
    dataset = _load(DATASET)
    inputs = [row["input"] for row in dataset["turns"]]

    for path in (ROOT / "datasets").glob("p4_*.json"):
        if path == DATASET:
            continue
        text = path.read_text(encoding="utf-8")
        for value in inputs:
            assert value not in text, path


def test_p4_av_real_gate_requires_authorization_review_and_visible_delivery():
    config = _load(CONFIG)
    gates = config["formal_gates"]

    assert gates["turn_2_p4_au_exact_turn_1_source_count"] == 1
    assert gates["turn_2_p4_av_authorized_count"] == 1
    assert gates["turn_2_p4_av_operational_role_count_minimum"] == 1
    assert gates["turn_2_p4_av_remaining_unsupported_count"] == 0
    assert gates["turn_2_m53_authorized_count"] == 1
    assert gates["turn_2_m46_verified_count"] == 1
    assert gates["turn_2_m45_delivered_count"] == 1
    assert gates["turn_2_m39_practical_act_count"] == 1
    assert gates["turn_2_generic_promise_or_clarification_count"] == 0


def test_p4_av_real_gate_freezes_causal_order_and_no_side_effects():
    gates = _load(CONFIG)["formal_gates"]

    assert gates["p4_av_node_before_m53_m46_m45_utterance_count"] == 1
    assert gates["p4_av_plan_mutation_count"] == 0
    assert gates["p4_av_new_model_call_count"] == 0
    assert gates["p4_av_factual_memory_write_count"] == 0
    assert gates["p4_av_raw_label_trace_count"] == 0
    assert gates["p4_av_m46_review_bypass_count"] == 0
    assert gates["p4_av_m45_or_m39_gate_weakening_count"] == 0
    assert gates["assistant_or_private_inference_source_count"] == 0


def test_p4_av_real_visible_gate_is_action_level_not_exact_wording():
    dataset = _load(DATASET)
    config = _load(CONFIG)

    assert dataset["visible_reply_policy"]["exact_string_gate"] is False
    assert dataset["visible_reply_policy"]["action_must_be_visible"] is True
    assert config["formal_gates"]["exact_visible_string_gate_count"] == 0
    assert config["failure_policy"]["internal_plan_without_visible_action_may_count_as_delivery"] is False


def test_p4_av_real_case_preserves_frozen_implementation_hashes():
    config = _load(CONFIG)

    for path_string, expected in (
        config["implementation"]["module"],
        config["implementation"]["product_entry"],
        config["implementation"]["launcher"],
        config["implementation"]["offline_evidence"],
    ):
        assert _sha(ROOT / path_string) == expected


def test_p4_av_real_case_requires_private_runtime_safari_and_no_rerun():
    config = _load(CONFIG)
    failure = config["failure_policy"]

    assert config["execution"]["port"] == 7885
    assert config["execution"]["private_runtime_required"] is True
    assert config["execution"]["safari_required"] is True
    assert failure["same_input_rerun_allowed"] is False
    assert failure["failed_result_may_be_hidden_by_offline_pass"] is False
    assert "does not establish advice usefulness" in config["claim_boundary"]
