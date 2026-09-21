import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FREEZE = ROOT / "research" / "p4_p_cross_language_correction_lifecycle_freeze_2026-09-22.json"


def _load():
    return json.loads(FREEZE.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_freeze_binds_contract_gate_probe_and_preexecution_tests():
    freeze = _load()
    assert freeze["status"] == "frozen_before_offline_execution"
    for binding in freeze["bindings"].values():
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_values_were_absent_at_checkpoint_and_old_cases_are_not_reused():
    novelty = _load()["novelty"]
    assert novelty["git_grep_checkpoint_old_value_file_count"] == 0
    assert novelty["git_grep_checkpoint_new_value_file_count"] == 0
    assert novelty["does_not_reuse_p4_m_p4_n_real_p4_o_or_p4_o_real_values"] is True
    assert novelty["old_value"] == "菊花茶"
    assert novelty["new_value"] == "クロモジ茶"


def test_execution_is_single_offline_no_retry_and_no_product_change():
    freeze = _load()
    execution = freeze["execution_authorization"]
    design = freeze["design"]
    policy = freeze["result_policy"]
    assert execution["exact_case_execution_count"] == 1
    assert execution["retry_count"] == 0
    assert execution["model_call_count"] == 0
    assert execution["safari_product_turn_count"] == 0
    assert design["product_implementation_authorized_before_observed_failure"] is False
    assert policy["same_case_rerun_allowed"] is False
    assert policy["broad_claim_allowed"] is False
