import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FREEZE = ROOT / "research" / "p4_g_multilingual_preference_acknowledgement_freeze_2026-09-21.json"


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
    assert freeze["status"] == "frozen_before_any_real_p4_g_product_turn"
    assert freeze["implementation_checkpoint"]["commit"] == "b257437e189e6108ff3b35432356c3f87734a9e3"
    for binding in freeze["implementation_checkpoint"].values():
        if isinstance(binding, dict):
            assert _sha256(ROOT / binding["path"]) == binding["sha256"]
    for binding in freeze["acceptance_bindings"].values():
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_freeze_records_pre_execution_evidence_without_real_turns():
    evidence = _load()["pre_execution_evidence"]
    assert evidence["focused_implementation_and_gate_tests_passed"] == 24
    assert evidence["adjacent_regression_tests_passed"] == 160
    assert evidence["product_entry_import_install_check_passed"] is True
    assert evidence["real_p4_g_product_turn_count"] == 0
    assert evidence["p4_g_process_start_count"] == 0
    assert evidence["production_memory_access_count"] == 0
    assert evidence["result_known_before_freeze"] is False


def test_freeze_allows_one_process_two_turns_and_zero_retry():
    effects = _load()["authorized_external_effects"]
    assert effects["localhost_product_process_starts"] == 1
    assert effects["safari_product_turns"] == 2
    assert effects["local_ollama_calls_maximum"] == 2
    assert effects["external_network_calls"] == 0
    assert effects["production_memory_accesses"] == 0
    failure = _load()["failure_policy"]
    assert failure["real_turn_retry_allowed"] is False
    assert failure["same_case_rerun_allowed"] is False


def test_freeze_requires_existing_tab_reuse_and_immutable_result():
    order = _load()["execution_order"]
    assert order.index("commit and push this acceptance freeze before any real P4-G turn") < order.index(
        "submit exactly turn 1 once and wait for durable completion"
    )
    assert "without closing any user tab" in order[3]
    assert order[-1] == "run the frozen gate once and preserve pass or fail"
