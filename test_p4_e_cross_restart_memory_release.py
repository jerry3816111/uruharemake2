import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "research" / "p4_e_cross_restart_memory_recall_release_2026-09-20.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_release_binds_freeze_result_and_acceptance():
    release = json.loads(RELEASE.read_text(encoding="utf-8"))
    assert release["status"] == "released_one_bounded_cross_restart_product_recall"
    for binding in release["bindings"].values():
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_release_preserves_scope_cost_limits_and_next_gate():
    release = json.loads(RELEASE.read_text(encoding="utf-8"))
    assert release["passed_scope"]["persisted_episode_id_retrieved"] is True
    assert release["passed_scope"]["speaker_owner_preserved"] is True
    assert release["passed_scope"]["recall_without_general_planner_model_call"] is True
    assert release["actual_result"]["frozen_gate_failed_count"] == 0
    costs = release["resource_accounting"]
    assert costs["real_product_turns"] == 2
    assert costs["retry_count"] == 0
    assert costs["paid_api_call_count"] == 0
    assert costs["production_memory_access_count"] == 0
    assert release["not_passed_or_not_present"]["preference_supersession_or_revocation"] == "not_tested"
    assert release["next_stage"]["id"] == "P4-F"
    assert release["next_stage"]["real_product_turns_before_contract_freeze_authorized"] == 0
