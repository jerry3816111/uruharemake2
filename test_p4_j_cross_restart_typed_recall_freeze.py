import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FREEZE = ROOT / "research" / "p4_j_cross_restart_typed_recall_freeze_2026-09-21.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load():
    return json.loads(FREEZE.read_text(encoding="utf-8"))


def test_freeze_binds_design_implementation_acceptance_and_launcher():
    freeze = _load()
    assert freeze["status"] == "frozen_before_any_real_p4_j_product_turn"
    assert _sha256(ROOT / freeze["design_freeze"]["path"]) == freeze["design_freeze"][
        "sha256"
    ]
    checkpoint = freeze["implementation_checkpoint"]
    for binding in checkpoint.values():
        if isinstance(binding, dict):
            payload = subprocess.check_output(
                ["git", "show", f"{checkpoint['commit']}:{binding['path']}"],
                cwd=ROOT,
            )
            assert hashlib.sha256(payload).hexdigest() == binding["sha256"]
    for binding in freeze["acceptance_bindings"].values():
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_frozen_implementation_commit_contains_exact_bound_files():
    freeze = _load()
    commit = freeze["implementation_checkpoint"]["commit"]
    for binding in freeze["implementation_checkpoint"].values():
        if not isinstance(binding, dict):
            continue
        payload = subprocess.check_output(
            ["git", "show", f"{commit}:{binding['path']}"],
            cwd=ROOT,
        )
        assert hashlib.sha256(payload).hexdigest() == binding["sha256"]


def test_freeze_has_no_real_result_and_forbids_retry_or_old_case_reuse():
    freeze = _load()
    evidence = freeze["pre_execution_evidence"]
    assert evidence["real_p4_j_product_turn_count"] == 0
    assert evidence["p4_j_product_process_start_count"] == 0
    assert evidence["result_known_before_freeze"] is False
    policy = freeze["failure_policy"]
    assert policy["real_turn_retry_allowed"] is False
    assert policy["same_case_rerun_allowed"] is False
    assert policy["p4_i_oolong_or_barley_case_rerun_allowed"] is False
    assert policy["p4_f_herbal_or_black_tea_case_rerun_allowed"] is False


def test_only_two_local_processes_two_safari_turns_and_zero_model_calls_are_authorized():
    effects = _load()["authorized_external_effects"]
    assert effects["localhost_product_process_starts"] == 2
    assert effects["process_restart_count"] == 1
    assert effects["safari_product_turns"] == 2
    assert effects["local_product_planner_model_calls_maximum"] == 0
    assert effects["external_network_calls"] == 0
    assert effects["production_memory_accesses"] == 0
    assert effects["closed_user_tabs"] == 0
