import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs" / "p4_au_real_source_bound_current_action_delivery_v1.json"


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load():
    contract = json.loads(CONFIG.read_text(encoding="utf-8"))
    dataset_path = ROOT / contract["dataset"]["path"]
    assert _sha(dataset_path) == contract["dataset"]["sha256"]
    return contract, json.loads(dataset_path.read_text(encoding="utf-8"))


def test_p4_au_real_case_is_frozen_after_offline_pass_and_before_execution():
    contract, dataset = _load()

    assert contract["status"] == "prospectively_frozen_before_real_execution"
    assert dataset["status"] == "prospectively_frozen_before_real_execution"
    assert contract["implementation"]["commit"] == "97eebc6"
    assert len(dataset["turns"]) == 2
    assert contract["execution"]["rerun_or_retry_after_result_allowed"] is False


def test_p4_au_real_case_is_new_and_does_not_reuse_exposed_inputs():
    _contract, dataset = _load()
    historical_paths = [
        ROOT / "datasets" / "p4_at_real_executed_action_outcome_closure_v1.json",
        ROOT / "datasets" / "p4_au_source_bound_current_action_delivery_v1.json",
    ]
    historical = "\n".join(path.read_text(encoding="utf-8") for path in historical_paths)

    for row in dataset["turns"]:
        assert row["input"] not in historical


def test_p4_au_real_case_freezes_prior_source_and_visible_action_as_separate_gates():
    contract, dataset = _load()
    gates = contract["formal_gates"]

    assert dataset["source_contract"]["turn_2_prior_source_must_equal_turn_1_user_source"] is True
    assert gates["turn_2_p4_au_prior_source_linked_count"] == 1
    assert gates["turn_2_p4_au_exact_turn_1_source_count"] == 1
    assert gates["turn_2_m45_delivered_count"] == 1
    assert gates["turn_2_m46_verified_count"] == 1
    assert gates["turn_2_m39_practical_act_count"] == 1
    assert gates["turn_2_generic_promise_or_clarification_count"] == 0


def test_p4_au_real_case_records_words_cost_and_latency_without_weakening_delivery():
    contract, dataset = _load()

    assert dataset["surface_contract"]["exact_visible_string_is_gate"] is False
    assert dataset["surface_contract"]["exact_visible_string_must_be_recorded"] is True
    assert contract["formal_gates"]["exact_visible_string_gate_count"] == 0
    assert contract["execution"]["latency_must_be_recorded"] is True
    assert contract["execution"]["model_calls_and_tokens_must_be_recorded"] is True
    assert contract["failure_policy"]["timeout_may_count_as_delivery"] is False
    assert contract["failure_policy"]["generic_promise_may_count_as_delivery"] is False


def test_p4_au_real_case_preserves_frozen_implementation_hashes():
    contract, _dataset = _load()

    for key in ("module", "product_entry", "launcher", "offline_evidence"):
        path, expected = contract["implementation"][key]
        assert _sha(ROOT / path) == expected


def test_p4_au_real_case_requires_private_runtime_safari_and_no_fallback_source():
    contract, _dataset = _load()
    failure = contract["failure_policy"]

    assert contract["execution"]["private_runtime_required"] is True
    assert contract["execution"]["safari_required"] is True
    assert failure["missing_prior_source_may_use_assistant_or_inferred_fallback"] is False
    assert failure["failed_result_may_be_hidden_by_offline_pass"] is False
