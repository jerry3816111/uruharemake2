import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FREEZE = ROOT / "research" / "p4_q_real_safari_correction_lifecycle_freeze_2026-09-22.json"


def _load():
    return json.loads(FREEZE.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_freeze_binds_offline_result_product_release_launcher_contract_and_gate():
    freeze = _load()
    assert freeze["status"] == "frozen_before_real_execution"
    for binding in freeze["bindings"].values():
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_values_are_new_and_finite_map_rescue_is_not_preinstalled():
    novelty = _load()["novelty"]
    assert novelty["git_grep_checkpoint_old_value_file_count"] == 0
    assert novelty["git_grep_checkpoint_new_value_file_count"] == 0
    assert novelty["new_value_absent_from_finite_localization_map"] is True
    assert novelty["does_not_reuse_p4_p_p4_q_or_earlier_product_values"] is True


def test_exact_three_turn_two_process_zero_retry_shape_is_frozen():
    execution = _load()["execution"]
    assert execution["listener"] == "127.0.0.1:7868"
    assert execution["process_starts"] == 2
    assert execution["process_restart_count"] == 1
    assert execution["real_product_turns"] == 3
    assert execution["retry_count"] == 0
    assert execution["model_call_count"] == 0
    assert execution["closed_user_tab_count"] == 0
    assert "--reuse-runtime" in execution["process_2_command_template"]


def test_failure_policy_forbids_same_case_rescue():
    policy = _load()["failure_policy"]
    assert policy["same_case_rerun_allowed"] is False
    assert policy["input_value_expected_surface_or_gate_change_allowed"] is False
    assert policy["manual_memory_seed_allowed"] is False
    assert policy["implementation_change_after_result_allowed"] is False
