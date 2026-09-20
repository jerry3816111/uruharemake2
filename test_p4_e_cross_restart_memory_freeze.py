import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FREEZE = ROOT / "research" / "p4_e_cross_restart_memory_recall_freeze_2026-09-20.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_freeze_binds_parent_contract_gate_and_test_before_real_turns():
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert freeze["status"] == "frozen_before_any_p4_e_real_product_turn"
    parent = freeze["parent_checkpoint"]["release"]
    assert _sha256(ROOT / parent["path"]) == parent["sha256"]
    for binding in freeze["bindings"].values():
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]
    evidence = freeze["pre_execution_evidence"]
    assert evidence["real_p4_e_product_turn_count"] == 0
    assert evidence["p4_e_process_start_count"] == 0
    assert evidence["result_known_before_freeze"] is False


def test_freeze_forbids_retry_seed_prompt_change_and_external_effects():
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    policy = freeze["failure_policy"]
    assert policy["real_turn_retry_allowed"] is False
    assert policy["prompt_change_allowed"] is False
    assert policy["fact_or_localization_change_allowed"] is False
    assert policy["manual_memory_seed_allowed"] is False
    effects = freeze["authorized_external_effects"]
    assert effects["localhost_product_process_starts"] == 2
    assert effects["safari_product_turns"] == 2
    assert effects["local_ollama_calls_maximum"] == 1
    assert effects["external_network_calls"] == 0
    assert effects["paid_api_calls"] == 0
    assert effects["production_memory_accesses"] == 0
