import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "research" / "p4_h_multilingual_preference_memory_act_release_2026-09-21.json"


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
    assert release["status"] == "released_bounded_preference_memory_act_pass"
    for binding in release["bindings"].values():
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_release_preserves_exact_bounded_pass():
    release = _load()
    passed = release["passed_scope"]
    assert passed["frozen_gate_status"] == "pass"
    assert passed["frozen_gate_failed_count"] == 0
    assert passed["deterministic_plan_route_both_turns"] is True
    assert passed["graph_select_node_both_turns"] is True
    assert passed["local_product_planner_model_calls"] == 0
    assert passed["retry_count"] == 0


def test_release_does_not_promote_surface_pass_to_semantic_pass():
    release = _load()
    remaining = release["observed_but_not_passed_scope"]
    assert remaining["turn_1_english_preference_typed_as_like"] is False
    assert remaining["turn_2_new_chinese_preference_typed_as_like"] is False
    assert remaining["turn_2_old_chinese_preference_typed_as_dislike"] is True
    assert remaining["complete_multilingual_preference_semantics"] is False
    assert remaining["cross_restart_semantic_recall_tested"] is False
    assert remaining["same_case_rerun_or_retuning_performed"] is False


def test_release_limits_p4_i_to_typed_semantics_before_new_real_execution():
    release = _load()
    next_stage = release["next_stage"]
    assert next_stage["id"] == "P4-I"
    assert next_stage["new_real_product_turns_before_separate_contract_freeze_authorized"] == 0
    assert any("do not change" in item for item in next_stage["required_boundary"])
    assert release["resource_accounting"]["local_product_planner_model_calls"] == 0
    assert release["resource_accounting"]["production_memory_access_count"] == 0
