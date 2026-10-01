import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FREEZE = ROOT / "research" / "p4_n_real_source_bound_japanese_delivery_freeze_2026-09-22.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _freeze():
    return json.loads(FREEZE.read_text(encoding="utf-8"))


def test_freeze_binds_offline_release_implementation_and_acceptance_files():
    freeze = _freeze()
    assert freeze["status"] == "frozen_before_any_real_p4_n_real_product_turn"
    bindings = [freeze["implementation_checkpoint"]["offline_release"]]
    bindings.extend(
        freeze["implementation_checkpoint"][name]
        for name in ("adapter", "product_entry")
    )
    bindings.extend(freeze["acceptance_bindings"].values())
    for binding in bindings:
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_freeze_records_zero_execution_and_novel_value_before_real_turn():
    freeze = _freeze()
    novelty = freeze["case_novelty_and_boundary"]
    assert novelty["selected_value"] == "そば茶"
    assert novelty["repository_occurrences_before_acceptance_files"] == 0
    assert novelty["offline_extraction_probe"]["current_value"] == "そば茶"
    assert novelty["offline_extraction_probe"]["bounded_identity_value"] == "そば茶"
    before = freeze["pre_execution_evidence"]
    assert before["real_p4_n_real_product_turn_count"] == 0
    assert before["p4_n_real_product_process_start_count"] == 0
    assert before["result_known_before_freeze"] is False


def test_freeze_authorizes_exactly_two_no_retry_local_turns_and_no_external_effects():
    allowed = _freeze()["authorized_external_effects"]
    assert allowed["localhost_product_process_starts"] == 2
    assert allowed["safari_product_turns"] == 2
    assert allowed["local_product_planner_model_calls_maximum"] == 0
    assert allowed["external_network_calls"] == 0
    assert allowed["paid_api_calls"] == 0
    assert allowed["external_deployments"] == 0
    assert allowed["production_memory_accesses"] == 0
    assert allowed["closed_user_tabs"] == 0
    policy = _freeze()["failure_policy"]
    assert policy["real_turn_retry_allowed"] is False
    assert policy["same_case_rerun_allowed"] is False
