import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FREEZE = ROOT / "research" / "p4_g_preference_acknowledgement_implementation_freeze_2026-09-21.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load():
    return json.loads(FREEZE.read_text(encoding="utf-8"))


def test_freeze_binds_parent_gap_contract_validator_and_test():
    freeze = _load()
    assert freeze["status"] == "frozen_before_preference_acknowledgement_implementation"
    assert freeze["parent_checkpoint"]["commit"] == "ca9a814a4017e690637bbc006e2e1efd1ea5b45b"
    release = freeze["parent_checkpoint"]["release"]
    assert _sha256(ROOT / release["path"]) == release["sha256"]
    for binding in freeze["bindings"].values():
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_freeze_preserves_real_prechange_gap_and_zero_new_external_effects():
    evidence = _load()["pre_implementation_evidence"]
    assert evidence["contract_tests_passed"] == 3
    assert evidence["real_p4_f_write_outputs_preserved"] == ["了解しました", "了解しました。"]
    assert evidence["language_guard_rejected_either_output"] is False
    for key in ("new_model_calls", "new_safari_turns", "new_database_writes", "production_memory_accesses"):
        assert evidence[key] == 0


def test_freeze_limits_runtime_change_to_one_post_guard_surface_authority():
    freeze = _load()
    assert freeze["authorized_implementation_files"] == [
        "uruha_explicit_preference_acknowledgement_p4.py",
        "uruha_web_ui_product.py",
        "test_p4_g_explicit_preference_acknowledgement.py",
    ]
    requirements = freeze["implementation_requirements"]
    assert requirements["classify_only_explicit_first_person_preference_write_or_correction"] is True
    assert requirements["replace_only_generic_formal_acknowledgement_allowlist"] is True
    assert requirements["multilingual_input_coverage"] == ["zh", "en", "ja"]
    assert requirements["non_generic_natural_reply_unchanged"] is True
    assert requirements["negative_guards_required"] is True
    assert requirements["model_call_added"] is False
    assert requirements["episode_write_count_changed"] is False
    assert requirements["memory_ranking_changed"] is False
    assert all(freeze["forbidden_changes"].values())
    assert all(value == 0 for value in freeze["pre_commit_external_effect_ceiling"].values())


def test_freeze_requires_implementation_commit_then_new_no_retry_case():
    freeze = _load()
    order = freeze["required_order"]
    assert order.index("commit and push implementation before any new real product turn") < order.index(
        "freeze one separately named unexposed isolated runtime case and gate"
    )
    assert "without rerunning the P4-F tea case" in order[5]
    boundary = freeze["post_implementation_acceptance_boundary"]
    assert boundary["new_real_product_turns_maximum"] == 2
    assert boundary["retry_count"] == 0
    assert boundary["production_memory_access_count"] == 0
    assert boundary["paid_api_call_count"] == 0
