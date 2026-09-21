import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FREEZE = ROOT / "research" / "p4_o_real_persisted_reference_time_delivery_freeze_2026-09-22.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _freeze():
    return json.loads(FREEZE.read_text(encoding="utf-8"))


def test_freeze_binds_release_implementation_launcher_and_acceptance():
    freeze = _freeze()
    assert freeze["status"] == "frozen_before_any_real_p4_o_real_product_turn"
    bindings = list(freeze["implementation_checkpoint"].values())[1:]
    bindings.extend(freeze["acceptance_bindings"].values())
    for binding in bindings:
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_freeze_records_new_value_and_zero_execution_before_real_turn():
    freeze = _freeze()
    novelty = freeze["case_novelty_and_boundary"]
    assert novelty["selected_value"] == "たんぽぽ茶"
    assert novelty["repository_occurrences_before_acceptance_files"] == 0
    assert novelty["offline_extraction_probe"]["scope_after_canonicalization"] == "drink"
    assert novelty["offline_extraction_probe"]["bounded_identity_value"] == "たんぽぽ茶"
    before = freeze["pre_execution_evidence"]
    assert before["isolated_product_entry_server_started_for_this_case"] is False
    assert before["real_p4_o_real_product_turn_count"] == 0
    assert before["p4_o_real_product_process_start_count"] == 0
    assert before["result_known_before_freeze"] is False


def test_freeze_authorizes_exactly_two_no_retry_local_turns_and_no_external_effects():
    freeze = _freeze()
    allowed = freeze["authorized_external_effects"]
    assert allowed["localhost_product_process_starts"] == 2
    assert allowed["safari_product_turns"] == 2
    assert allowed["local_product_planner_model_calls_maximum"] == 0
    assert allowed["external_network_calls"] == 0
    assert allowed["paid_api_calls"] == 0
    assert allowed["external_deployments"] == 0
    assert allowed["production_memory_accesses"] == 0
    assert allowed["closed_user_tabs"] == 0
    assert freeze["failure_policy"]["real_turn_retry_allowed"] is False
    assert freeze["failure_policy"]["same_case_rerun_allowed"] is False
