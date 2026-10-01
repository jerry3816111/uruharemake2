import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FREEZE = ROOT / "research" / "p4_f_explicit_preference_supersession_freeze_2026-09-21.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load():
    return json.loads(FREEZE.read_text(encoding="utf-8"))


def test_freeze_binds_parent_gap_contract_and_test_before_implementation():
    freeze = _load()
    assert freeze["status"] == "frozen_before_preference_supersession_implementation"
    assert freeze["parent_checkpoint"]["commit"] == "dab3cfa"
    release = freeze["parent_checkpoint"]["release"]
    assert _sha256(ROOT / release["path"]) == release["sha256"]
    for binding in freeze["bindings"].values():
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_freeze_records_the_prechange_failure_without_external_effects():
    evidence = _load()["pre_implementation_evidence"]
    assert evidence["focused_tests_passed"] == 25
    assert evidence["current_adapter_result"] == "ambiguous_multiple_user_preferences"
    assert evidence["correction_applied"] is False
    assert evidence["historical_revocation_marked"] is False
    for key in ("fixture_model_calls", "fixture_network_calls", "fixture_safari_turns", "fixture_database_writes"):
        assert evidence[key] == 0


def test_freeze_limits_implementation_to_one_bounded_selected_memory_mechanism():
    freeze = _load()
    assert freeze["single_changed_variable"] == "bounded_explicit_preference_supersession_in_speaker_qualified_selected_memory"
    assert freeze["authorized_implementation_files"] == [
        "uruha_speaker_qualified_fact_p3.py",
        "test_speaker_qualified_fact_p3.py",
        "test_p4_f_explicit_preference_supersession.py",
    ]
    requirements = freeze["implementation_requirements"]
    assert requirements["selected_evidence_only"] is True
    assert requirements["same_selected_item_contains_old_negation_and_new_current_value"] is True
    assert requirements["first_person_user_only"] is True
    assert requirements["same_preference_category_required"] is True
    assert requirements["historical_episode_remains_immutable"] is True
    assert requirements["current_and_revoked_values_have_digests"] is True
    assert requirements["raw_dialogue_in_trace"] is False
    assert requirements["fact_memory_write_count"] == 0
    assert requirements["unsupported_or_conflicting_corrections_fail_closed"] is True
    assert requirements["safety_surface_remains_authoritative"] is True
    assert all(freeze["forbidden_changes"].values())
    assert all(value == 0 for value in freeze["pre_commit_external_effect_ceiling"].values())


def test_freeze_requires_commit_before_one_no_retry_product_acceptance():
    freeze = _load()
    order = freeze["required_order"]
    assert order.index("commit and push the implementation before any real P4-F product turn") < order.index(
        "freeze exact three-turn Safari inputs and acceptance gate"
    )
    boundary = freeze["post_implementation_acceptance_boundary"]
    assert boundary["real_product_turns"] == 3
    assert boundary["actual_process_restarts"] == 1
    assert boundary["retry_count"] == 0
    assert boundary["production_memory_access_count"] == 0
    assert boundary["paid_api_call_count"] == 0
