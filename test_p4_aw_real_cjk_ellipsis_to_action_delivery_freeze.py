import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs" / "p4_aw_real_cjk_ellipsis_to_action_delivery_v1.json"


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    dataset_path = ROOT / config["dataset"]["path"]
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    return config, dataset, dataset_path


def test_p4_aw_real_contract_and_pair_are_frozen_before_execution():
    config, dataset, dataset_path = _load()

    assert config["status"] == "prospectively_frozen_before_real_execution"
    assert dataset["status"] == "sealed_before_real_execution"
    assert _sha(dataset_path) == config["dataset"]["sha256"]
    assert len(dataset["turns"]) == 2
    assert config["execution"]["port"] == 7887
    assert config["execution"]["private_runtime_required"] is True
    assert config["execution"]["safari_required"] is True
    assert config["execution"]["rerun_or_retry_after_result_allowed"] is False


def test_p4_aw_real_freeze_binds_the_released_offline_implementation():
    config, _dataset, _path = _load()

    assert config["implementation"]["commit"] == "8487644"
    for _name, binding in config["implementation"].items():
        if _name == "commit":
            continue
        path, expected = binding
        assert _sha(ROOT / path) == expected


def test_p4_aw_real_pair_is_new_relative_to_exposed_p4_at_au_av_and_p4_aw_cases():
    _config, dataset, _path = _load()
    frozen_inputs = {row["input"] for row in dataset["turns"]}
    exposed_paths = (
        "datasets/p4_at_real_executed_action_outcome_closure_v1.json",
        "datasets/p4_au_real_source_bound_current_action_delivery_v1.json",
        "datasets/p4_av_real_neutral_operational_role_delivery_v1.json",
        "datasets/p4_aw_cjk_subject_ellipsis_action_authority_v1.json",
    )
    exposed_inputs = set()
    for relative in exposed_paths:
        source = json.loads((ROOT / relative).read_text(encoding="utf-8"))
        rows = source.get("turns") or source.get("cases") or []
        exposed_inputs.update(str(row.get("input") or "") for row in rows)

    assert len(frozen_inputs) == 2
    assert frozen_inputs.isdisjoint(exposed_inputs)


def test_p4_aw_real_gate_requires_the_full_authority_and_delivery_chain():
    config, _dataset, _path = _load()
    gates = config["formal_gates"]

    assert gates["turn_1_p4_aw_authorized_count"] == 1
    assert gates["turn_1_p4_aw_source_role_preserved_unspecified_count"] == 1
    assert gates["turn_1_p4_aw_private_truth_claim_count"] == 0
    assert gates["turn_1_p4_as_executed_count"] == 1
    assert gates["turn_1_p4_ar_authorized_count"] == 1
    assert gates["turn_2_p4_at_closed_supported_count"] == 1
    assert gates["turn_2_p4_au_exact_turn_1_source_count"] == 1
    assert gates["turn_2_p4_av_authorized_count"] == 1
    assert gates["turn_2_m45_delivered_count"] == 1
    assert gates["turn_2_m39_practical_act_count"] == 1
    assert gates["turn_2_generic_promise_or_clarification_count"] == 0
    assert gates["latency_target_met_count"] == 2


def test_p4_aw_real_failure_policy_forbids_retries_and_internal_only_success():
    config, dataset, _path = _load()
    failure = config["failure_policy"]

    assert failure["same_input_rerun_allowed"] is False
    assert failure["post_result_gate_or_dataset_change_allowed"] is False
    assert failure["missing_p4_aw_or_p4_av_node_may_count_as_pass"] is False
    assert failure["timeout_may_count_as_delivery"] is False
    assert failure["generic_promise_may_count_as_delivery"] is False
    assert failure["clarification_may_count_as_delivery"] is False
    assert failure["internal_plan_without_visible_action_may_count_as_delivery"] is False
    assert dataset["visible_reply_policy"]["exact_string_gate"] is False
