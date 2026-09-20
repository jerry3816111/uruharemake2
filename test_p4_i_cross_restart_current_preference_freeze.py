import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent
FREEZE = ROOT / "research" / "p4_i_cross_restart_current_preference_freeze_2026-09-21.json"


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


def test_freeze_binds_committed_implementation_and_acceptance_artifacts():
    freeze = _load()
    assert freeze["status"] == "frozen_before_any_real_p4_i_product_turn"
    commit = freeze["implementation_checkpoint"]["commit"]
    for name, binding in freeze["implementation_checkpoint"].items():
        if name == "commit":
            continue
        assert _sha256_at_commit(commit, binding["path"]) == binding["sha256"]
    for binding in freeze["acceptance_bindings"].values():
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_freeze_records_offline_success_but_no_real_result():
    evidence = _load()["pre_execution_evidence"]
    assert evidence["p4_i_focused_tests_passed"] == 12
    assert evidence["affected_regression_tests_passed"] == 122
    assert evidence["gate_tests_passed"] == 10
    assert evidence["product_entry_import_install_check_passed"] is True
    assert evidence["real_p4_i_product_turn_count"] == 0
    assert evidence["p4_i_process_start_count"] == 0
    assert evidence["result_known_before_freeze"] is False


def test_freeze_allows_two_processes_two_turns_and_no_retry():
    freeze = _load()
    effects = freeze["authorized_external_effects"]
    assert effects["localhost_product_process_starts"] == 2
    assert effects["process_restart_count"] == 1
    assert effects["safari_product_turns"] == 2
    assert effects["local_product_planner_model_calls_maximum"] == 0
    assert effects["production_memory_accesses"] == 0
    assert freeze["failure_policy"]["real_turn_retry_allowed"] is False
    assert freeze["failure_policy"]["same_case_rerun_allowed"] is False
    assert freeze["failure_policy"]["p4_h_sparkling_water_or_hot_cocoa_case_rerun_allowed"] is False
