import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent
FREEZE = ROOT / "research" / "p4_k_cross_restart_surface_delivery_freeze_2026-09-21.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_at_commit(commit: str, path: str) -> str:
    payload = subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)
    return hashlib.sha256(payload).hexdigest()


def _load():
    return json.loads(FREEZE.read_text(encoding="utf-8"))


def test_freeze_binds_implementation_checkpoint_acceptance_and_launcher():
    freeze = _load()
    assert freeze["status"] == "frozen_before_any_real_p4_k_product_turn"
    checkpoint = freeze["implementation_checkpoint"]
    for binding in checkpoint.values():
        if isinstance(binding, dict):
            assert _sha256_at_commit(checkpoint["commit"], binding["path"]) == binding["sha256"]
    for binding in freeze["acceptance_bindings"].values():
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_freeze_discloses_semantic_overlap_without_reusing_p4_j_case():
    novelty = _load()["case_novelty_and_boundary"]
    assert novelty["p4_j_real_input_value_reused"] is False
    assert novelty["p4_j_real_query_language_reused"] is False
    assert novelty["exact_source_value_form"] == "紅茶"
    assert novelty["query_language"] == "ja"
    assert novelty["historical_p4_f_semantic_black_tea_overlap_disclosed"] is True
    assert novelty["historical_p4_f_case_reused"] is False
    assert novelty["novel_semantic_generalization_claim_allowed"] is False


def test_freeze_has_no_known_result_and_forbids_retry_or_old_case_reuse():
    freeze = _load()
    evidence = freeze["pre_execution_evidence"]
    assert evidence["real_p4_k_product_turn_count"] == 0
    assert evidence["p4_k_product_process_start_count"] == 0
    assert evidence["result_known_before_freeze"] is False
    policy = freeze["failure_policy"]
    assert policy["real_turn_retry_allowed"] is False
    assert policy["same_case_rerun_allowed"] is False
    assert policy["p4_j_rooibos_case_rerun_allowed"] is False


def test_only_two_local_processes_two_safari_turns_and_zero_model_calls_are_authorized():
    effects = _load()["authorized_external_effects"]
    assert effects["localhost_product_process_starts"] == 2
    assert effects["process_restart_count"] == 1
    assert effects["safari_product_turns"] == 2
    assert effects["local_product_planner_model_calls_maximum"] == 0
    assert effects["external_network_calls"] == 0
    assert effects["production_memory_accesses"] == 0
    assert effects["closed_user_tabs"] == 0
