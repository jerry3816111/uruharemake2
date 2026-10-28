import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "research" / "p4_m_cross_language_correction_delivery_release_2026-09-22.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load():
    return json.loads(RELEASE.read_text(encoding="utf-8"))


def test_release_binds_freeze_terminal_result_and_acceptance():
    release = _load()
    assert release["status"] == "released_terminal_cross_language_correction_delivery_failure"
    for binding in release["bindings"].values():
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_release_preserves_lineage_success_and_surface_failure_separately():
    established = _load()["established"]
    assert established["frozen_gate_status"] == "fail"
    assert established["new_value_unique_active_after_restart"] is True
    assert established["old_value_unique_historical_after_restart"] is True
    assert established["explicit_negative_preserved_after_restart"] is True
    assert established["exact_expected_japanese_value_surface"] is False
    failure = _load()["failure"]
    assert failure["memory_loss"] is False
    assert failure["historical_value_leak"] is False


def test_next_stage_repairs_one_general_boundary_without_reusing_exposed_value():
    stage = _load()["next_stage"]
    assert stage["id"] == "P4-N"
    assert stage["single_changed_variable"] == (
        "source_provenance_bounded_japanese_identity_localization"
    )
    assert stage["real_product_turns_before_separate_new_acceptance_freeze_authorized"] == 0
    assert any("do not add 柚子茶" in item for item in stage["forbidden_change"])
    assert any("provenance" in item for item in stage["success_requirements"])


def test_release_does_not_promote_failure_localization_to_general_claim():
    missing = _load()["not_established"]
    assert missing["successful_cross_language_correction_delivery"] is True
    assert missing["strong_llm_advantage"] is True
    assert missing["human_equation"] is True
