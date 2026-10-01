import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "research" / "p4_i_cross_restart_current_preference_release_2026-09-21.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load():
    return json.loads(RELEASE.read_text(encoding="utf-8"))


def test_release_binds_freeze_result_and_acceptance():
    release = _load()
    assert release["status"] == "released_bounded_cross_restart_typed_state_pass"
    for binding in release["bindings"].values():
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_release_preserves_exact_cross_restart_typed_state_pass():
    passed = _load()["passed_scope"]
    assert passed["frozen_gate_status"] == "pass"
    assert passed["actual_product_process_starts"] == 2
    assert passed["different_pid_and_product_session"] is True
    assert passed["same_isolated_runtime_root_and_memory_db"] is True
    assert passed["old_positive_preserved_as_historical"] is True
    assert passed["explicit_old_negative_active"] is True
    assert passed["local_product_planner_model_calls"] == 0
    assert passed["retry_count"] == 0


def test_release_does_not_promote_typed_storage_to_answer_authority():
    remaining = _load()["observed_but_not_passed_scope"]
    assert remaining["typed_profile_shadow_answer_use_authorized"] is False
    assert remaining["typed_profile_shadow_affects_working_memory"] is False
    assert remaining["conversational_recall_from_typed_state_tested"] is False
    assert remaining["long_dialogue_reliability"] is False
    assert remaining["human_felt_understanding"] is False
    assert remaining["strong_llm_advantage"] is False


def test_release_limits_p4_j_to_frozen_read_only_active_scope_recall():
    release = _load()
    next_stage = release["next_stage"]
    assert next_stage["id"] == "P4-J"
    assert next_stage["new_real_product_turns_before_separate_contract_freeze_authorized"] == 0
    assert any("active P4-I" in item for item in next_stage["required_boundary"])
    assert any("fail closed" in item for item in next_stage["required_boundary"])
    assert release["resource_accounting"]["production_memory_access_count"] == 0
