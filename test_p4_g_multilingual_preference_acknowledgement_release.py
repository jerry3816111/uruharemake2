import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "research" / "p4_g_multilingual_preference_acknowledgement_release_2026-09-21.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load():
    return json.loads(RELEASE.read_text(encoding="utf-8"))


def test_release_binds_freeze_negative_result_and_acceptance():
    release = _load()
    assert release["status"] == "released_negative_multilingual_preference_acknowledgement_result"
    for binding in release["bindings"].values():
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_release_preserves_passed_mechanics_and_failed_visible_product_scope():
    release = _load()
    assert release["passed_scope"]["multilingual_classifier_selected_both_acts"] is True
    assert release["passed_scope"]["two_distinct_durable_episodes"] is True
    assert release["failed_scope"]["frozen_gate_failed_count"] == 10
    assert release["failed_scope"]["write_surface_matches_contract"] is False
    assert release["failed_scope"]["correction_surface_matches_contract"] is False
    assert release["failed_scope"]["turn_2_existing_route"] == "ask_like_me_misclassification"
    assert release["failed_scope"]["same_case_rerun_or_retuning_performed"] is False


def test_release_preserves_cost_and_limits_p4_h():
    release = _load()
    accounting = release["resource_accounting"]
    assert accounting["real_product_turns"] == 2
    assert accounting["local_product_planner_model_calls"] == 1
    assert accounting["retry_count"] == 0
    assert accounting["paid_api_call_count"] == 0
    assert accounting["production_memory_access_count"] == 0
    assert release["causal_diagnosis"]["generic_only_post_guard_repair_is_sufficient"] is False
    assert release["next_stage"]["id"] == "P4-H"
    assert release["next_stage"]["same_p4_g_real_case_may_be_rerun"] is False
    assert release["next_stage"]["new_real_product_turns_before_separate_contract_freeze_authorized"] == 0

