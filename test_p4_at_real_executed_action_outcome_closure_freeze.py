import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs" / "p4_at_real_executed_action_outcome_closure_v1.json"


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load():
    contract = json.loads(CONFIG.read_text(encoding="utf-8"))
    dataset_path = ROOT / contract["dataset"]["path"]
    assert _sha(dataset_path) == contract["dataset"]["sha256"]
    return contract, json.loads(dataset_path.read_text(encoding="utf-8"))


def test_p4_at_real_case_is_frozen_after_offline_pass_and_before_execution():
    contract, dataset = _load()

    assert contract["status"] == "prospectively_frozen_before_real_execution"
    assert dataset["status"] == "prospectively_frozen_before_real_execution"
    assert contract["implementation"]["commit"] == "a1600e2"
    assert len(dataset["turns"]) == 2
    assert contract["execution"]["rerun_or_retry_after_result_allowed"] is False


def test_p4_at_real_case_scores_action_act_and_records_but_does_not_gate_exact_words():
    contract, dataset = _load()

    assert dataset["surface_contract"]["action_act_must_match"] is True
    assert dataset["surface_contract"]["exact_visible_string_is_gate"] is False
    assert dataset["surface_contract"]["exact_visible_string_must_be_recorded"] is True
    assert contract["formal_gates"]["exact_visible_string_gate_count"] == 0


def test_p4_at_real_case_requires_full_identity_feedback_and_temporal_chain():
    contract, dataset = _load()
    gates = contract["formal_gates"]

    assert gates["turn_1_exact_m44_receipt_count"] == 1
    assert gates["turn_1_exact_p4_ag_binding_count"] == 1
    assert gates["turn_2_exact_prediction_identity_count"] == 1
    assert gates["turn_2_m44_supported_linked_count"] == 1
    assert gates["turn_2_p4_ag_supported_count"] == 1
    assert gates["turn_2_current_solve_policy_count"] == 1
    assert gates["turn_2_m39_practical_act_count"] == 1
    assert gates["turn_2_same_turn_outcome_backdated_count"] == 0
    assert dataset["temporal_contract"]["turn_2_outcome_observed_now_not_backdated"] is True


def test_p4_at_real_case_uses_new_inputs_and_preserves_predecessor_hashes():
    contract, dataset = _load()
    historical_paths = [
        ROOT / "datasets" / "p4_at_executed_action_outcome_closure_v1.json",
        ROOT / "datasets" / "p4_as_real_selected_action_surface_execution_v1.json",
    ]
    historical = "\n".join(path.read_text(encoding="utf-8") for path in historical_paths)
    for row in dataset["turns"]:
        assert row["input"] not in historical
    for key in ("module", "product_entry", "launcher", "offline_evidence"):
        path, expected_sha = contract["implementation"][key]
        assert _sha(ROOT / path) == expected_sha


def test_p4_at_real_case_keeps_private_runtime_and_no_text_fallback_boundaries():
    contract, _dataset = _load()
    policy = contract["failure_policy"]

    assert contract["execution"]["private_runtime_required"] is True
    assert contract["execution"]["safari_required"] is True
    assert policy["same_input_rerun_allowed"] is False
    assert policy["missing_exact_receipt_may_fallback_to_text_only"] is False
    assert policy["unknown_may_count_as_success"] is False
