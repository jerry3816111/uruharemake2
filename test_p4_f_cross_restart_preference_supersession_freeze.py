import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FREEZE = ROOT / "research" / "p4_f_cross_restart_preference_supersession_freeze_2026-09-21.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load():
    return json.loads(FREEZE.read_text(encoding="utf-8"))


def test_freeze_binds_committed_implementation_and_acceptance_gate():
    freeze = _load()
    assert freeze["status"] == "frozen_before_any_real_p4_f_product_turn"
    assert freeze["implementation_checkpoint"]["commit"] == "c89f62d0f400b984056c2059a0811db16302eb75"
    for section in ("implementation_checkpoint", "acceptance_bindings"):
        for name, binding in freeze[section].items():
            if name == "commit":
                continue
            assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_freeze_records_zero_real_p4_f_effects_before_execution():
    evidence = _load()["pre_execution_evidence"]
    assert evidence["focused_implementation_and_gate_tests_passed"] == 41
    assert evidence["adjacent_regression_tests_passed"] == 113
    assert evidence["real_p4_f_product_turn_count"] == 0
    assert evidence["p4_f_process_start_count"] == 0
    assert evidence["production_memory_access_count"] == 0
    assert evidence["post_turn_memory_seed_count"] == 0
    assert evidence["result_known_before_freeze"] is False


def test_freeze_allows_exactly_three_turns_one_restart_and_no_retry():
    freeze = _load()
    effects = freeze["authorized_external_effects"]
    assert effects["localhost_product_process_starts"] == 2
    assert effects["safari_product_turns"] == 3
    assert effects["local_ollama_calls_maximum"] == 2
    assert effects["external_network_calls"] == 0
    assert effects["paid_api_calls"] == 0
    assert effects["production_memory_accesses"] == 0
    assert freeze["failure_policy"]["real_turn_retry_allowed"] is False
    assert freeze["failure_policy"]["same_case_rerun_allowed"] is False


def test_freeze_orders_commit_before_real_turn_and_preserves_terminal_result():
    freeze = _load()
    order = freeze["execution_order"]
    assert order[0] == "commit and push this acceptance freeze before any real P4-F turn"
    assert order[-1] == "run the frozen gate once and preserve pass or fail"
    assert "first P4-F result remains immutable" in freeze["failure_policy"]["repair_after_terminal_result"]
