import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FREEZE = ROOT / "research" / "p4_q_correction_lifecycle_protocol_repair_freeze_2026-09-22.json"


def _load():
    return json.loads(FREEZE.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_freeze_binds_p4_p_failure_and_all_p4_q_preexecution_files():
    freeze = _load()
    assert freeze["status"] == "frozen_before_offline_execution"
    for binding in freeze["bindings"].values():
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_single_change_is_elapsed_protocol_time_not_product_mechanics():
    change = _load()["causal_change"]
    assert "already elapsed 06:30/06:31" in change["single_change"]
    assert change["unchanged_product_code"] is True
    assert change["unchanged_answer_absence_lineage_hash_identity_and_no_retry_gates"] is True
    assert change["product_implementation_authorized"] is False


def test_new_values_and_single_no_retry_execution_are_frozen():
    freeze = _load()
    novelty = freeze["novelty"]
    execution = freeze["execution_authorization"]
    policy = freeze["result_policy"]
    assert novelty["git_grep_checkpoint_old_value_file_count"] == 0
    assert novelty["git_grep_checkpoint_new_value_file_count"] == 0
    assert novelty["does_not_reuse_p4_p_or_earlier_values"] is True
    assert execution["exact_case_execution_count"] == 1
    assert execution["retry_count"] == 0
    assert execution["model_call_count"] == 0
    assert execution["safari_product_turn_count"] == 0
    assert policy["same_case_rerun_allowed"] is False
    assert policy["p4_p_case_rerun_allowed"] is False
