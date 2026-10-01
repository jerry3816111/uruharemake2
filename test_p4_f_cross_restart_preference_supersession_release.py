import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "research" / "p4_f_cross_restart_preference_supersession_release_2026-09-21.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_release_binds_freeze_result_and_acceptance():
    release = json.loads(RELEASE.read_text(encoding="utf-8"))
    assert release["status"] == "released_one_bounded_cross_restart_preference_supersession"
    for binding in release["bindings"].values():
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_release_preserves_scope_cost_surface_gap_and_next_gate():
    release = json.loads(RELEASE.read_text(encoding="utf-8"))
    passed = release["passed_scope"]
    assert passed["two_distinct_durable_episodes_preserved"] is True
    assert passed["current_and_revoked_values_resolved"] is True
    assert passed["higher_scored_old_episode_not_mistaken_for_current"] is True
    assert passed["database_history_not_rewritten"] is True
    assert release["actual_result"]["frozen_gate_failed_count"] == 0

    costs = release["resource_accounting"]
    assert costs["real_product_turns"] == 3
    assert costs["process_starts"] == 2
    assert costs["process_restart_count"] == 1
    assert costs["retry_count"] == 0
    assert costs["paid_api_call_count"] == 0
    assert costs["production_memory_access_count"] == 0

    gap = release["retained_surface_gap"]
    assert gap["status"] == "not_passed"
    assert gap["observed_outputs"] == ["了解しました", "了解しました。"]
    assert release["not_passed_or_not_present"]["research_advantage"] == "not_established"
    assert release["next_stage"]["id"] == "P4-G"
    assert release["next_stage"]["same_p4_f_real_case_may_be_rerun"] is False
    assert release["next_stage"]["new_real_product_turns_before_separate_contract_freeze_authorized"] == 0
