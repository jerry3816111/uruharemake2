import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "research" / "p4_j_cross_restart_typed_recall_release_2026-09-21.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load():
    return json.loads(RELEASE.read_text(encoding="utf-8"))


def test_release_binds_frozen_terminal_failure_evidence():
    release = _load()
    assert release["status"] == "released_terminal_cross_restart_typed_recall_fail"
    for binding in release["bindings"].values():
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_release_preserves_failed_surface_and_missing_graph_without_retry():
    failure = _load()["preserved_failure"]
    assert failure["frozen_gate_status"] == "fail"
    assert failure["failed_gate_count"] == 7
    assert failure["typed_record_resolved_into_plan"] is True
    assert failure["final_visible_surface_matched_planned_core"] is False
    assert failure["final_visible_surface_used_episode_timestamp"] is True
    assert failure["p4_j_graph_node_present"] is False
    assert failure["same_case_rerun_performed"] is False
    assert failure["retry_count"] == 0


def test_next_stage_is_one_propagation_fix_not_retuning_or_case_reuse():
    stage = _load()["next_stage"]
    assert stage["id"] == "P4-K"
    assert stage["real_product_turns_before_separate_new_acceptance_freeze_authorized"] == 0
    assert any("memory_data" in item for item in stage["allowed_implementation_change"])
    assert any("do not edit or rerun" in item for item in stage["forbidden_change"])
    assert any("do not change query classification" in item for item in stage["forbidden_change"])


def test_release_does_not_promote_failed_recall_to_research_claim():
    missing = _load()["not_established"]
    assert missing["product_typed_current_preference_recall"] is True
    assert missing["long_dialogue_reliability"] is True
    assert missing["human_felt_understanding"] is True
    assert missing["strong_llm_advantage"] is True
    assert missing["human_equation"] is True
